"""Repository manager component for loading and managing Git repositories."""

import threading
import os
import tempfile
import glob
import shutil
import stat
from repo.repository import GitRepository
from visualization.layout import GraphLayout
from gui.auth_dialog import GitHubAuthDialog
from auth.token_storage import TokenStorage
from utils.logging_config import get_logger
from utils.translations import t

logger = get_logger(__name__)


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

        # Repository state
        self.git_repo = None
        self.is_remote_loaded = False  # Sledování stavu remote načtení
        self.is_cloned_repo = False  # True pokud repo bylo načteno z URL (klonováno)
        self.temp_clones = []  # Seznam temp složek ke smazání při zavření
        self.current_temp_clone = None  # Cesta k aktuálně otevřenému temp klonu
        self.display_name = None  # Reálný název repozitáře (pro klonované repo)
        self.token_storage = TokenStorage()  # GitHub token storage

        # Vyčistit staré temp složky z předchozích sessions
        self._cleanup_old_temp_clones()

        # Register cleanup handler
        import atexit
        atexit.register(self._cleanup_temp_clones)

    def on_repository_selected(self, repo_path: str):
        """
        Entry point for loading repository - detects URL vs local path.

        Args:
            repo_path: Local filesystem path or Git URL
        """
        # Detekce URL vs lokální cesta
        if self._is_git_url(repo_path):
            # Online repozitář - klonovat
            self.clone_repository(repo_path)
        else:
            # Lokální složka - načíst přímo

            # Zavřít GitPython repo před mazáním temp složky
            if self.git_repo and hasattr(self.git_repo, 'repo') and self.git_repo.repo:
                try:
                    self.git_repo.repo.close()
                except Exception as e:
                    logger.warning(f"Failed to close GitPython repo: {e}")
                    pass

            # Pokud byl předtím otevřený klonovaný repo → smazat temp
            if self.is_cloned_repo and self.current_temp_clone:
                self._cleanup_single_clone(self.current_temp_clone)
                self.current_temp_clone = None

            self.is_cloned_repo = False  # Lokální repo, ne klonované
            self.display_name = None  # Resetovat display name pro lokální repo
            self.parent.update_status(t('loading_repo'))
            tm = self.parent.theme_manager
            self.parent.progress.config(value=50, color=tm.get_color('progress_color_success'))
            self.parent.progress.start()

            thread = threading.Thread(
                target=self.load_repository,
                args=(repo_path,),
                daemon=True
            )
            thread.start()

    def _is_git_url(self, text: str) -> bool:
        """
        Detekuje zda je text Git URL.

        Args:
            text: String to check

        Returns:
            bool: True if text is a Git URL
        """
        text = text.lower().strip()
        if text.startswith(('http://', 'https://', 'git@')):
            return True
        git_hosts = ['github.com', 'gitlab.com', 'bitbucket.org', 'gitea.']
        return any(host in text for host in git_hosts)

    def clone_repository(self, url: str):
        """
        Klonuje online repozitář do temp složky.

        Args:
            url: Git repository URL
        """
        # Smazat VŠECHNY staré temp klony (nejen current)
        # Řeší race conditions a failed clones
        if self.temp_clones:
            for old_clone in self.temp_clones[:]:  # Kopie listu pro bezpečnou iteraci
                self._cleanup_single_clone(old_clone)
        self.current_temp_clone = None

        # Vytvořit temp složku
        temp_dir = tempfile.mkdtemp(prefix='gitvys_clone_')
        self.temp_clones.append(temp_dir)

        # Extrahovat název repo z URL pro zobrazení
        repo_name = url.rstrip('/').split('/')[-1].replace('.git', '')
        self.display_name = repo_name  # Uložit reálný název pro pozdější zobrazení

        self.parent.update_status(t('cloning', repo_name))
        tm = self.parent.theme_manager
        self.parent.progress.config(color=tm.get_color('progress_color_success'))
        self.parent.progress.start()

        thread = threading.Thread(
            target=self._clone_worker,
            args=(url, temp_dir),
            daemon=True
        )
        thread.start()

    def _clone_worker(self, url: str, path: str):
        """
        Worker thread pro klonování repozitáře.

        Args:
            url: Git repository URL
            path: Local path to clone to
        """
        try:
            from git import Repo
            from git.exc import GitCommandError

            # Pokusit se klonovat bez autentizace
            try:
                Repo.clone_from(url, path)
                # Úspěch - načíst jako běžný repo
                self.root.after(0, self._on_clone_complete, path)
                return

            except GitCommandError as clone_error:
                # Zkontrolovat, zda je to chyba autentizace
                error_message = str(clone_error).lower()
                is_auth_error = any(keyword in error_message for keyword in [
                    'authentication', 'forbidden', '403', '401',
                    'could not read', 'repository not found'
                ])

                if not is_auth_error:
                    # Jiná chyba než autentizace - propagovat
                    raise

                # Chyba autentizace - zkusit s tokenem
                logger.info("Authentication required for cloning, attempting with token...")

                # Načíst uložený token
                token = self.token_storage.load_token()

                # Pokud token neexistuje, zobrazit auth dialog
                if not token:
                    logger.info("No saved token found, showing auth dialog...")
                    token = self.root.after(0, self._show_auth_dialog_sync)

                    # Počkat na výsledek z auth dialogu (v main threadu)
                    import time
                    timeout = 300  # 5 minut
                    start_time = time.time()
                    while not hasattr(self, '_auth_dialog_result') and time.time() - start_time < timeout:
                        time.sleep(0.1)

                    if hasattr(self, '_auth_dialog_result'):
                        token = self._auth_dialog_result
                        delattr(self, '_auth_dialog_result')
                    else:
                        raise Exception(t('auth_expired'))

                if not token:
                    raise Exception(t('auth_failed'))

                # Uložit token pro příští použití
                self.token_storage.save_token(token)

                # Vytvořit autentizovanou URL
                # Formát: https://{token}@github.com/user/repo.git
                if url.startswith('https://'):
                    auth_url = url.replace('https://', f'https://{token}@')
                elif url.startswith('http://'):
                    auth_url = url.replace('http://', f'http://{token}@')
                else:
                    # SSH URL nebo jiný formát - nemůžeme použít token
                    raise Exception(t('auth_https_only'))

                # Retry klonování s autentizovanou URL
                logger.info("Retrying clone with authentication...")
                self.root.after(0, self.parent.update_status, t('cloning_with_auth'))
                Repo.clone_from(auth_url, path)

                # Úspěch
                self.root.after(0, self._on_clone_complete, path)

        except Exception as e:
            # Smazat temp složku při chybě klonování
            self.root.after(0, self._cleanup_single_clone, path)
            self.root.after(0, self.parent.show_error, t('error_cloning', str(e)))
            self.root.after(0, self.parent.progress.stop)

    def _show_auth_dialog_sync(self):
        """Zobrazí auth dialog v main threadu a uloží výsledek."""
        dialog = GitHubAuthDialog(self.root)
        token = dialog.show()
        self._auth_dialog_result = token
        return token

    def _on_clone_complete(self, path: str):
        """
        Callback po úspěšném klonování.

        Args:
            path: Path to cloned repository
        """
        self.is_cloned_repo = True  # Označit že repo bylo klonováno z URL
        self.current_temp_clone = path  # Uložit cestu k aktuálnímu temp klonu
        self.parent.update_status(t('loading_cloned'))

        thread = threading.Thread(
            target=self.load_repository,
            args=(path,),
            daemon=True
        )
        thread.start()

    def _cleanup_old_temp_clones(self):
        """Při startu smaže všechny temp složky z předchozích sessions."""
        def handle_remove_readonly(func, path, exc):
            """Error handler pro Windows readonly files."""
            if func in (os.unlink, os.rmdir):
                # Změnit readonly flag a zkusit znovu
                os.chmod(path, stat.S_IWRITE)
                func(path)
            else:
                raise

        try:
            temp_dir = tempfile.gettempdir()
            pattern = os.path.join(temp_dir, 'gitvys_clone_*')

            for old_temp in glob.glob(pattern):
                try:
                    if os.path.exists(old_temp) and os.path.isdir(old_temp):
                        shutil.rmtree(old_temp, onerror=handle_remove_readonly)
                except Exception as e:
                    logger.warning(f"Failed to cleanup orphaned temp clone {old_temp}: {e}")
                    pass  # Ignorovat chyby u jednotlivých složek
        except Exception as e:
            logger.warning(f"Failed to cleanup temp clones: {e}")
            pass  # Ignorovat chyby celého cleaningu

    def _cleanup_single_clone(self, path: str):
        """
        Smaže jeden konkrétní temp klon.

        Args:
            path: Path to temp clone to delete
        """
        def handle_remove_readonly(func, path, exc):
            """Error handler pro Windows readonly files."""
            if func in (os.unlink, os.rmdir):
                # Změnit readonly flag a zkusit znovu
                os.chmod(path, stat.S_IWRITE)
                func(path)
            else:
                raise

        try:
            if os.path.exists(path):
                shutil.rmtree(path, onerror=handle_remove_readonly)
                # Odebrat z listu JEN pokud mazání skutečně uspělo
                if not os.path.exists(path) and path in self.temp_clones:
                    self.temp_clones.remove(path)
        except Exception as e:
            # Logovat ale nepadnout
            print(f"Warning: Nepodařilo se smazat temp klon: {e}")

    def _cleanup_temp_clones(self):
        """Smaže dočasné klonované repozitáře při zavření (fallback)."""
        # Zavřít GitPython repo pokud je stále otevřený
        if hasattr(self, 'git_repo') and self.git_repo:
            if hasattr(self.git_repo, 'repo') and self.git_repo.repo:
                try:
                    self.git_repo.repo.close()
                except Exception as e:
                    logger.warning(f"Failed to close GitPython repo during cleanup: {e}")
                    pass

        def handle_remove_readonly(func, path, exc):
            """Error handler pro Windows readonly files."""
            if func in (os.unlink, os.rmdir):
                # Změnit readonly flag a zkusit znovu
                os.chmod(path, stat.S_IWRITE)
                func(path)
            else:
                raise

        for temp_dir in self.temp_clones:
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir, onerror=handle_remove_readonly)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp clone {temp_dir}: {e}")
                pass  # Ignorovat chyby při cleanup

    def load_repository(self, repo_path: str):
        """
        Načte Git repozitář z dané cesty.

        Args:
            repo_path: Path to Git repository
        """
        try:
            self.git_repo = GitRepository(repo_path)

            if not self.git_repo.load_repository():
                self.root.after(0, self.parent.show_error, t('failed_load_repo'))
                return

            commits = self.git_repo.parse_commits()

            if not commits:
                self.root.after(0, self.parent.show_error, t('no_commits'))
                return

            merge_branches = self.git_repo.get_merge_branches()
            layout = GraphLayout(commits, merge_branches=merge_branches)
            positioned_commits = layout.calculate_positions()

            self.root.after(0, self.parent.show_graph, positioned_commits)

        except Exception as e:
            self.root.after(0, self.parent.show_error, t('error_loading_repo', str(e)))

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
            tm = self.parent.theme_manager
            self.parent.progress.config(color=tm.get_color('progress_color_success'))
            self.parent.progress.start()

            thread = threading.Thread(
                target=self.refresh_local_repository,
                daemon=True
            )
            thread.start()

    def refresh_local_repository(self):
        """Obnoví lokální repozitář data."""
        try:
            commits = self.git_repo.parse_commits()

            if not commits:
                self.root.after(0, self.parent.show_error, t('no_commits'))
                return

            merge_branches = self.git_repo.get_merge_branches()
            layout = GraphLayout(commits, merge_branches=merge_branches)
            positioned_commits = layout.calculate_positions()

            self.root.after(0, self.parent.show_graph, positioned_commits)

        except Exception as e:
            self.root.after(0, self.parent.show_error, t('error_loading_repo', str(e)))

    def fetch_remote_data(self):
        """Načte remote větve pro aktuální repozitář."""
        if not self.git_repo:
            return

        self.parent.fetch_button.config(text=t('loading'), state="disabled")
        self.parent.update_status(t('loading_remote_branches'))
        tm = self.parent.theme_manager
        self.parent.progress.config(color=tm.get_color('progress_color_success'))
        self.parent.progress.start()

        thread = threading.Thread(
            target=self.load_remote_repository,
            daemon=True
        )
        thread.start()

    def load_remote_repository(self):
        """Načte remote repozitář data."""
        try:
            commits = self.git_repo.parse_commits_with_remote()

            if not commits:
                self.root.after(0, self.parent.show_error, t('no_commits'))
                return

            merge_branches = self.git_repo.get_merge_branches()
            layout = GraphLayout(commits, merge_branches=merge_branches)
            positioned_commits = layout.calculate_positions()

            self.root.after(0, self.parent.update_graph_with_remote, positioned_commits)

        except Exception as e:
            self.root.after(0, self.parent.show_error, t('error_loading_remote', str(e)))

    def close_repository(self):
        """Zavře aktuální repozitář a vyčistí temp soubory."""
        # Zavřít GitPython repo aby uvolnil file handles
        if self.git_repo and hasattr(self.git_repo, 'repo') and self.git_repo.repo:
            try:
                self.git_repo.repo.close()
            except Exception as e:
                logger.warning(f"Failed to close GitPython repo: {e}")
                pass
        self.git_repo = None

        # Pokud je otevřený klonovaný repo → smazat temp klon
        if self.is_cloned_repo and self.current_temp_clone:
            self._cleanup_single_clone(self.current_temp_clone)
            self.current_temp_clone = None

        # Reset stavu
        self.is_remote_loaded = False
        self.is_cloned_repo = False
        self.display_name = None
