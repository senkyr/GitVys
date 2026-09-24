"""Repository manager component for loading and managing Git repositories.

Vlákna: načítání, klonování i refresh běží v daemon vláknech, výsledky se do
hlavního (tkinter) vlákna předávají přes ``root.after``. Každá operace dostane
číslo generace; výsledek operace, kterou mezitím předběhla novější (jiný
repozitář, zavření, refresh), se zahodí. Bez toho by pomalé načítání starého
repozitáře mohlo přepsat graf nového.
"""

import atexit
import glob
import os
import shutil
import stat
import sys
import tempfile
import threading

from repo.repository import GitRepository
from visualization.layout import GraphLayout
from gui.auth_dialog import GitHubAuthDialog
from auth.token_storage import TokenStorage
from auth.git_credentials import (
    build_git_auth_env, can_use_github_token, is_trusted_git_url,
    looks_like_url, parse_git_url_host, redact_secrets,
)
from utils.logging_config import get_logger
from utils.translations import t

logger = get_logger(__name__)

# Jak dlouho klonovací vlákno čeká na dokončení OAuth dialogu (device code platí 15 min)
AUTH_DIALOG_TIMEOUT = 20 * 60

# Klíčová slova v chybě `git clone`, která znamenají chybějící/špatné přihlášení
AUTH_ERROR_KEYWORDS = (
    'authentication', 'forbidden', '403', '401',
    'could not read', 'repository not found', 'terminal prompts disabled',
)


def _remove_readonly(func, path, _exc):
    """Error handler pro rmtree: Git na Windows zakládá read-only objekty."""
    if func in (os.unlink, os.rmdir, os.remove):
        os.chmod(path, stat.S_IWRITE)
        func(path)
    else:
        raise


def _rmtree_force(path: str) -> None:
    """Smaže strom včetně read-only souborů (onexc od Pythonu 3.12, dřív onerror)."""
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=_remove_readonly)
    else:
        shutil.rmtree(path, onerror=_remove_readonly)


class RepositoryManager:
    """Component for managing Git repository operations including cloning, loading, and refreshing."""

    def __init__(self, parent_window):
        """
        Initialize RepositoryManager.

        Args:
            parent_window: MainWindow instance
        """
        self.parent = parent_window
        self.root = parent_window.root

        # Repository state (mění se jen v hlavním vlákně)
        self.git_repo = None
        self.is_remote_loaded = False  # Sledování stavu remote načtení
        self.is_cloned_repo = False  # True pokud repo bylo načteno z URL (klonováno)
        self.temp_clones = []  # Seznam temp složek ke smazání při zavření
        self.current_temp_clone = None  # Cesta k aktuálně otevřenému temp klonu
        self.display_name = None  # Reálný název repozitáře (pro klonované repo)
        self.token_storage = TokenStorage()  # GitHub token storage
        self._generation = 0  # Číslo poslední spuštěné operace (viz docstring modulu)

        # Vyčistit staré temp složky z předchozích sessions
        self._cleanup_old_temp_clones()

        # Register cleanup handler
        atexit.register(self._cleanup_temp_clones)

    # ------------------------------------------------------------------
    # Předávání výsledků z vláken
    # ------------------------------------------------------------------

    def _next_generation(self) -> int:
        self._generation += 1
        return self._generation

    def _post(self, generation, callback, *args):
        """Naplánuje callback do hlavního vlákna, pokud je operace stále aktuální."""
        def run():
            if generation == self._generation:
                callback(*args)
            else:
                logger.debug(f"Dropping stale result of operation {generation}")
        self._post_always(run)

    def _post_always(self, callback, *args):
        """Naplánuje callback do hlavního vlákna bez ohledu na generaci."""
        try:
            self.root.after(0, callback, *args)
        except RuntimeError:
            # Hlavní smyčka už neběží (aplikace se zavírá)
            logger.debug("Main loop is not running, callback dropped")

    def _start_progress(self, value=None):
        tm = self.parent.theme_manager
        if value is None:
            self.parent.progress.config(color=tm.get_color('progress_color_success'))
        else:
            self.parent.progress.config(value=value, color=tm.get_color('progress_color_success'))
        self.parent.progress.start()

    # ------------------------------------------------------------------
    # Výběr repozitáře
    # ------------------------------------------------------------------

    def on_repository_selected(self, repo_path: str):
        """
        Entry point for loading repository - detects URL vs local path.

        Validuje vstup i tady (ne jen v DragDropFrame): na graf lze přetáhnout
        libovolný text a ten jde rovnou sem.

        Args:
            repo_path: Local filesystem path or Git URL
        """
        text = (repo_path or '').strip()

        if self._is_git_url(text):
            if not is_trusted_git_url(text):
                logger.warning("Rejected untrusted Git URL")
                self.parent.show_error(t('invalid_url'))
                return
            self.clone_repository(text)
            return

        if not os.path.isdir(text):
            self.parent.show_error(t('invalid_folder'))
            return

        # Lokální složka - zavřít předchozí repo a případně smazat jeho temp klon
        self._close_current_repo()
        if self.is_cloned_repo and self.current_temp_clone:
            self._cleanup_single_clone(self.current_temp_clone)
            self.current_temp_clone = None

        self.is_cloned_repo = False  # Lokální repo, ne klonované
        self.is_remote_loaded = False
        self.display_name = None  # Resetovat display name pro lokální repo
        self.parent.update_status(t('loading_repo'))
        self._start_progress(value=50)

        generation = self._next_generation()
        thread = threading.Thread(
            target=self.load_repository,
            args=(text, generation),
            daemon=True
        )
        thread.start()

    def _is_git_url(self, text: str) -> bool:
        """
        Detekuje, zda je text URL (a ne lokální cesta).

        Zda je URL povolená, rozhoduje až ``is_trusted_git_url``.

        Args:
            text: String to check

        Returns:
            bool: True if text looks like a Git URL
        """
        return looks_like_url(text)

    # ------------------------------------------------------------------
    # Klonování
    # ------------------------------------------------------------------

    def clone_repository(self, url: str):
        """
        Klonuje online repozitář do temp složky.

        Args:
            url: Git repository URL
        """
        # Zavřít předchozí repo a smazat VŠECHNY staré temp klony (nejen current)
        self._close_current_repo()
        if self.temp_clones:
            for old_clone in self.temp_clones[:]:  # Kopie listu pro bezpečnou iteraci
                self._cleanup_single_clone(old_clone)
        self.current_temp_clone = None

        # Vytvořit temp složku
        temp_dir = tempfile.mkdtemp(prefix='gitvys_clone_')
        self.temp_clones.append(temp_dir)

        # Extrahovat název repo z URL pro zobrazení
        repo_name = url.rstrip('/').split('/')[-1].split(':')[-1]
        if repo_name.endswith('.git'):
            repo_name = repo_name[:-4]
        self.display_name = repo_name  # Uložit reálný název pro pozdější zobrazení

        self.parent.update_status(t('cloning', repo_name))
        self._start_progress()

        generation = self._next_generation()
        thread = threading.Thread(
            target=self._clone_worker,
            args=(url, temp_dir, generation),
            daemon=True
        )
        thread.start()

    @staticmethod
    def _is_auth_error(error: Exception) -> bool:
        message = str(error).lower()
        return any(keyword in message for keyword in AUTH_ERROR_KEYWORDS)

    @staticmethod
    def _clone(url: str, path: str, token: str = None):
        """Spustí `git clone`; token jde do Gitu jen přes proměnné prostředí."""
        from git import Repo
        env = build_git_auth_env(token) if token else {'GIT_TERMINAL_PROMPT': '0'}
        Repo.clone_from(url, path, env=env)

    def _clone_worker(self, url: str, path: str, generation: int = None):
        """
        Worker thread pro klonování repozitáře.

        Postup: klon bez přihlášení → při chybě autentizace uložený token →
        je-li uložený token neplatný (odvolaný), smaže se a otevře se OAuth
        dialog. Token se ukládá až po úspěšném klonu a posílá se jen na
        https://github.com.

        Args:
            url: Git repository URL
            path: Local path to clone to
            generation: Číslo operace (None = aktuální)
        """
        if generation is None:
            generation = self._generation

        try:
            from git.exc import GitCommandError

            try:
                self._clone(url, path)
                self._post(generation, self._on_clone_complete, path)
                return
            except GitCommandError as clone_error:
                if not self._is_auth_error(clone_error):
                    raise

                if not can_use_github_token(url):
                    _, host = parse_git_url_host(url)
                    if host == 'github.com':
                        # SSH nebo http:// na GitHub - token tam poslat nejde / nesmí
                        raise Exception(t('auth_https_only'))
                    raise

            logger.info("Authentication required for cloning, attempting with token...")

            token = self.token_storage.load_token()
            token_from_storage = token is not None
            if not token:
                logger.info("No saved token found, showing auth dialog...")
                token = self._request_token_from_user()
                if not token:
                    raise Exception(t('auth_expired'))

            self._post(generation, self.parent.update_status, t('cloning_with_auth'))
            try:
                self._clone(url, path, token)
            except GitCommandError as auth_clone_error:
                if not (token_from_storage and self._is_auth_error(auth_clone_error)):
                    raise
                # Uložený token neplatí (odvolaný, vypršel) → smazat a požádat o nový
                logger.info("Saved token was rejected, requesting a new one")
                self.token_storage.delete_token()
                token_from_storage = False
                token = self._request_token_from_user()
                if not token:
                    raise Exception(t('auth_expired'))
                self._clone(url, path, token)

            if not token_from_storage:
                self.token_storage.save_token(token)

            self._post(generation, self._on_clone_complete, path)

        except Exception as e:
            message = redact_secrets(str(e))
            logger.warning(f"Cloning failed: {message}")
            # Temp složku smazat vždy, chybu ukázat jen u aktuální operace
            self._post_always(self._cleanup_single_clone, path)
            self._post(generation, self.parent.show_error, t('error_cloning', message))

    def _request_token_from_user(self):
        """Z pracovního vlákna otevře OAuth dialog v hlavním vlákně a počká na výsledek."""
        done = threading.Event()
        result = {}

        def show():
            try:
                result['token'] = self._show_auth_dialog_sync()
            except Exception as e:
                logger.warning(f"Auth dialog failed: {e}")
            finally:
                done.set()

        self._post_always(show)
        if not done.wait(AUTH_DIALOG_TIMEOUT):
            logger.warning("Auth dialog did not finish in time")
            return None
        return result.get('token')

    def _show_auth_dialog_sync(self):
        """Zobrazí auth dialog (volat jen v hlavním vlákně) a vrátí token nebo None."""
        dialog = GitHubAuthDialog(self.root)
        return dialog.show()

    def _on_clone_complete(self, path: str):
        """
        Callback po úspěšném klonování (hlavní vlákno).

        Args:
            path: Path to cloned repository
        """
        self.is_cloned_repo = True  # Označit že repo bylo klonováno z URL
        self.is_remote_loaded = False
        self.current_temp_clone = path  # Uložit cestu k aktuálnímu temp klonu
        self.parent.update_status(t('loading_cloned'))

        thread = threading.Thread(
            target=self.load_repository,
            args=(path, self._generation),
            daemon=True
        )
        thread.start()

    # ------------------------------------------------------------------
    # Úklid
    # ------------------------------------------------------------------

    def _close_current_repo(self):
        """Uvolní file handles GitPythonu (nutné před mazáním klonu na Windows)."""
        if self.git_repo is not None:
            self._close_git_repo(self.git_repo)
        self.git_repo = None

    @staticmethod
    def _close_git_repo(git_repo):
        repo = getattr(git_repo, 'repo', None)
        if repo:
            try:
                repo.close()
            except Exception as e:
                logger.warning(f"Failed to close GitPython repo: {e}")

    def _cleanup_old_temp_clones(self):
        """Při startu smaže všechny temp složky z předchozích sessions."""
        try:
            pattern = os.path.join(tempfile.gettempdir(), 'gitvys_clone_*')
            for old_temp in glob.glob(pattern):
                try:
                    if os.path.isdir(old_temp):
                        _rmtree_force(old_temp)
                except Exception as e:
                    logger.warning(f"Failed to cleanup orphaned temp clone {old_temp}: {e}")
        except Exception as e:
            logger.warning(f"Failed to cleanup temp clones: {e}")

    def _cleanup_single_clone(self, path: str):
        """
        Smaže jeden konkrétní temp klon.

        Args:
            path: Path to temp clone to delete
        """
        try:
            if os.path.exists(path):
                _rmtree_force(path)
            # Odebrat z listu JEN pokud mazání skutečně uspělo
            if not os.path.exists(path) and path in self.temp_clones:
                self.temp_clones.remove(path)
        except Exception as e:
            logger.warning(f"Failed to delete temp clone {path}: {e}")

    def _cleanup_temp_clones(self):
        """Smaže dočasné klonované repozitáře při zavření (fallback)."""
        if getattr(self, 'git_repo', None):
            self._close_git_repo(self.git_repo)

        for temp_dir in list(self.temp_clones):
            try:
                if os.path.exists(temp_dir):
                    _rmtree_force(temp_dir)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp clone {temp_dir}: {e}")

    # ------------------------------------------------------------------
    # Načítání
    # ------------------------------------------------------------------

    @staticmethod
    def _build_layout(git_repo, commits):
        layout = GraphLayout(commits, merge_branches=git_repo.get_merge_branches())
        return layout.calculate_positions()

    def load_repository(self, repo_path: str, generation: int = None):
        """
        Načte Git repozitář z dané cesty (pracovní vlákno).

        Args:
            repo_path: Path to Git repository
            generation: Číslo operace (None = aktuální)
        """
        if generation is None:
            generation = self._generation

        git_repo = None
        try:
            git_repo = GitRepository(repo_path)

            if not git_repo.load_repository():
                self._post(generation, self.parent.show_error, t('failed_load_repo'))
                return

            commits = git_repo.parse_commits()

            if not commits:
                self._close_git_repo(git_repo)
                self._post(generation, self.parent.show_error, t('no_commits'))
                return

            positioned_commits = self._build_layout(git_repo, commits)
            self._post(generation, self._on_repository_loaded, git_repo, positioned_commits)

        except Exception as e:
            if git_repo is not None:
                self._close_git_repo(git_repo)
            self._post(generation, self.parent.show_error,
                       t('error_loading_repo', redact_secrets(str(e))))

    def _on_repository_loaded(self, git_repo, commits):
        """Hlavní vlákno: převezme nově načtený repozitář a zobrazí graf."""
        if self.git_repo is not None and self.git_repo is not git_repo:
            self._close_git_repo(self.git_repo)
        self.git_repo = git_repo
        self.parent.show_graph(commits)

    def refresh_repository(self):
        """Obnoví repozitář podle aktuálního stavu (lokální vs remote)."""
        if not self.git_repo:
            return

        if self.is_remote_loaded:
            # Obnovit s remote daty
            self.fetch_remote_data()
        else:
            # Obnovit jen lokálně
            self.parent.update_status(t('loading_repo'))
            self._start_progress()

            generation = self._next_generation()
            thread = threading.Thread(
                target=self.refresh_local_repository,
                args=(self.git_repo, generation),
                daemon=True
            )
            thread.start()

    def refresh_local_repository(self, git_repo=None, generation: int = None):
        """Obnoví data lokálního repozitáře (pracovní vlákno)."""
        git_repo = git_repo or self.git_repo
        if generation is None:
            generation = self._generation
        try:
            commits = git_repo.parse_commits()

            if not commits:
                self._post(generation, self.parent.show_error, t('no_commits'))
                return

            positioned_commits = self._build_layout(git_repo, commits)
            self._post(generation, self.parent.show_graph, positioned_commits)

        except Exception as e:
            self._post(generation, self.parent.show_error,
                       t('error_loading_repo', redact_secrets(str(e))))

    def fetch_remote_data(self):
        """Načte remote větve pro aktuální repozitář (z lokálních remote-tracking refů, bez síťového fetch)."""
        if not self.git_repo:
            return

        self.parent.fetch_button.config(text=t('loading'), state="disabled")
        self.parent.update_status(t('loading_remote_branches'))
        self._start_progress()

        generation = self._next_generation()
        thread = threading.Thread(
            target=self.load_remote_repository,
            args=(self.git_repo, generation),
            daemon=True
        )
        thread.start()

    def load_remote_repository(self, git_repo=None, generation: int = None):
        """Načte data včetně remote větví (pracovní vlákno)."""
        git_repo = git_repo or self.git_repo
        if generation is None:
            generation = self._generation
        try:
            commits = git_repo.parse_commits_with_remote()

            if not commits:
                self._post(generation, self.parent.show_error, t('no_commits'))
                return

            positioned_commits = self._build_layout(git_repo, commits)
            self._post(generation, self.parent.update_graph_with_remote, positioned_commits)

        except Exception as e:
            self._post(generation, self.parent.show_error,
                       t('error_loading_remote', redact_secrets(str(e))))

    def close_repository(self):
        """Zavře aktuální repozitář a vyčistí temp soubory."""
        # Zneplatnit případné běžící operace - jejich výsledek se už nezobrazí
        self._next_generation()

        # Zavřít GitPython repo aby uvolnil file handles
        self._close_current_repo()

        # Pokud je otevřený klonovaný repo → smazat temp klon
        if self.is_cloned_repo and self.current_temp_clone:
            self._cleanup_single_clone(self.current_temp_clone)
            self.current_temp_clone = None

        # Reset stavu
        self.is_remote_loaded = False
        self.is_cloned_repo = False
        self.display_name = None
