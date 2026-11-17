"""
Translation management for multi-language support.
"""
import os
import json
from typing import Dict
from utils.logging_config import get_logger

logger = get_logger(__name__)


# Translation dictionaries
TRANSLATIONS = {
    'cs': {
        # Main window
        'app_title': 'Git Visualizer v1.6.0',
        'fetch_remote': 'Načíst remote',
        'fetch_branches': 'Načíst větve',
        'close_repo': 'Zavřít repo',
        'refresh': 'Obnovit',
        'ready': 'Připraven',
        'loading_repo': 'Načítám repozitář...',
        'cloning': 'Klonuji {}...',
        'cloning_with_auth': 'Klonuji s autentizací...',
        'loading_cloned': 'Načítám naklonovaný repozitář...',
        'loading_remote_branches': 'Načítám remote větve...',
        'loading': 'Načítám...',
        'loaded_commits': 'Načteno {} commitů',
        'loaded_commits_remote': 'Načteno {} commitů (včetně remote)',
        'error': 'Chyba',
        'failed_load_repo': 'Nepodařilo se načíst Git repozitář',
        'no_commits': 'Repozitář neobsahuje žádné commity',
        'error_loading_repo': 'Chyba při načítání repozitáře: {}',
        'error_loading_remote': 'Chyba při načítání remote větví: {}',
        'error_cloning': 'Chyba klonování:\n{}',
        'auth_expired': 'Autentizace vypršela nebo byla zrušena',
        'auth_failed': 'Autentizace se nezdařila',
        'auth_https_only': 'Přihlášení přes GitHub je možné jen pro HTTPS adresy na github.com',
        'logout_github': 'Odhlásit GitHub',
        'logout_title': 'Odhlášení z GitHubu',
        'logout_done': 'Odhlášeno. Přihlášení ke GitHubu už na tomto počítači není uložené,\nsoukromý repozitář si vyžádá nové.',
        'logout_failed': 'Odhlášení se nezdařilo: uložené přihlášení se nepodařilo smazat.\nSmažte ručně soubor:\n{}',
        'logout_cancelled_clone': 'Klonování bylo zrušeno, protože jste se odhlásili z GitHubu.',

        # Statistics plurals
        'author_1': 'autor',
        'author_2_4': 'autoři',
        'author_5': 'autorů',
        'branch_1': 'větev',
        'branch_2_4': 'větve',
        'branch_5': 'větví',
        'commit_1': 'commit',
        'commit_2_4': 'commity',
        'commit_5': 'commitů',
        'tag_1': 'tag',
        'tag_2_4': 'tagy',
        'tag_5': 'tagů',
        'tags_format': '{}+{} tagů',  # local+remote format

        # Drag & drop
        'drag_drop_text': 'Přetáhni sem složku nebo URL repozitáře',
        'open_folder': 'Otevřít složku',
        'open_url': 'Otevřít URL',
        'select_folder': 'Vyber složku Git repozitáře',
        'enter_url_title': 'Otevřít online repozitář',
        'enter_url_text': 'Zadej URL Git repozitáře:\n(např. https://github.com/user/repo.git)',
        'paste_tooltip': 'Vložit ze schránky',
        'ok': 'OK',
        'cancel': 'Zrušit',
        'invalid_url': 'Zadaná URL není platná Git URL',
        'invalid_folder': 'Vybraná cesta není platná složka',
        'not_git_repo': 'Vybraná složka neobsahuje Git repozitář',

        # Auth dialog
        'auth_title': 'Autorizace GitHub účtu',
        'auth_instruction': 'Pro přístup k soukromým repozitářům\nautorizujte aplikaci na GitHubu.',
        'auth_steps': '1. Klikněte na tlačítko níže\n2. Zadejte tento kód:',
        'copy_code': '📋 Kopírovat',
        'open_github': '🌐 Otevřít GitHub v prohlížeči',
        'auth_preparing': 'Připravuji autentizaci...',
        'auth_requesting': 'Žádám GitHub o kód...',
        'auth_waiting': 'Čekám na autorizaci...',
        'auth_success': '✓ Autorizace úspěšná!',
        'auth_error_title': 'Chyba autentizace',
        'auth_error_code': 'Nepodařilo se získat autorizační kód.',
        'auth_error_timeout': 'Autorizace vypršela. Zkuste to znovu.',
        'auth_error_cancelled': 'Autorizace byla zamítnuta.',
        'auth_error_general': 'Chyba při autentizaci.',
        'code_copied': 'Kód zkopírován do schránky!',
        'browser_opened': 'Prohlížeč otevřen. Pokračujte na GitHubu...',
        'open_manually': 'Otevřete ručně: {}',

        # Graph drawer / table headers
        'header_branch': 'Větev / Commit / Tag',
        'header_message': 'Zpráva / Popis',
        'header_author': 'Autor',
        'header_date': 'Datum',

        # Language switcher
        'language': 'Jazyk:',
        'czech': 'Čeština',
        'english': 'English',
    },
    'en': {
        # Main window
        'app_title': 'Git Visualizer v1.6.0',
        'fetch_remote': 'Fetch remote',
        'fetch_branches': 'Fetch branches',
        'close_repo': 'Close repo',
        'refresh': 'Refresh',
        'ready': 'Ready',
        'loading_repo': 'Loading repository...',
        'cloning': 'Cloning {}...',
        'cloning_with_auth': 'Cloning with authentication...',
        'loading_cloned': 'Loading cloned repository...',
        'loading_remote_branches': 'Loading remote branches...',
        'loading': 'Loading...',
        'loaded_commits': 'Loaded {} commits',
        'loaded_commits_remote': 'Loaded {} commits (including remote)',
        'error': 'Error',
        'failed_load_repo': 'Failed to load Git repository',
        'no_commits': 'Repository contains no commits',
        'error_loading_repo': 'Error loading repository: {}',
        'error_loading_remote': 'Error loading remote branches: {}',
        'error_cloning': 'Cloning error:\n{}',
        'auth_expired': 'Authentication expired or was cancelled',
        'auth_failed': 'Authentication failed',
        'auth_https_only': 'GitHub sign-in only works with HTTPS URLs on github.com',
        'logout_github': 'Sign out GitHub',
        'logout_title': 'GitHub sign-out',
        'logout_done': 'Signed out. The GitHub sign-in is no longer stored on this computer;\na private repository will ask for a new one.',
        'logout_failed': 'Sign-out failed: the stored sign-in could not be deleted.\nDelete this file manually:\n{}',
        'logout_cancelled_clone': 'Cloning was cancelled because you signed out of GitHub.',

        # Statistics plurals (English doesn't need complex plurals)
        'author_1': 'author',
        'author_2_4': 'authors',
        'author_5': 'authors',
        'branch_1': 'branch',
        'branch_2_4': 'branches',
        'branch_5': 'branches',
        'commit_1': 'commit',
        'commit_2_4': 'commits',
        'commit_5': 'commits',
        'tag_1': 'tag',
        'tag_2_4': 'tags',
        'tag_5': 'tags',
        'tags_format': '{}+{} tags',

        # Drag & drop
        'drag_drop_text': 'Drag & drop a folder or repository URL here',
        'open_folder': 'Open folder',
        'open_url': 'Open URL',
        'select_folder': 'Select Git repository folder',
        'enter_url_title': 'Open online repository',
        'enter_url_text': 'Enter Git repository URL:\n(e.g. https://github.com/user/repo.git)',
        'paste_tooltip': 'Paste from clipboard',
        'ok': 'OK',
        'cancel': 'Cancel',
        'invalid_url': 'The entered URL is not a valid Git URL',
        'invalid_folder': 'The selected path is not a valid folder',
        'not_git_repo': 'The selected folder does not contain a Git repository',

        # Auth dialog
        'auth_title': 'GitHub Account Authorization',
        'auth_instruction': 'To access private repositories,\nauthorize the application on GitHub.',
        'auth_steps': '1. Click the button below\n2. Enter this code:',
        'copy_code': '📋 Copy',
        'open_github': '🌐 Open GitHub in browser',
        'auth_preparing': 'Preparing authentication...',
        'auth_requesting': 'Requesting code from GitHub...',
        'auth_waiting': 'Waiting for authorization...',
        'auth_success': '✓ Authorization successful!',
        'auth_error_title': 'Authentication error',
        'auth_error_code': 'Failed to obtain authorization code.',
        'auth_error_timeout': 'Authorization expired. Please try again.',
        'auth_error_cancelled': 'Authorization was denied.',
        'auth_error_general': 'Error during authentication.',
        'code_copied': 'Code copied to clipboard!',
        'browser_opened': 'Browser opened. Continue on GitHub...',
        'open_manually': 'Open manually: {}',

        # Graph drawer / table headers
        'header_branch': 'Branch / Commit / Tag',
        'header_message': 'Message / Description',
        'header_author': 'Author',
        'header_date': 'Date',

        # Language switcher
        'language': 'Language:',
        'czech': 'Čeština',
        'english': 'English',
    }
}


class TranslationManager:
    """Singleton for managing application translations."""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._current_language = 'cs'  # Default to Czech
            self._callbacks = []  # Callbacks to notify when language changes
            self._load_language_preference()
            TranslationManager._initialized = True

    def _get_settings_dir(self) -> str:
        """Get the settings directory path."""
        home = os.path.expanduser('~')
        settings_dir = os.path.join(home, '.gitvys')
        os.makedirs(settings_dir, exist_ok=True)
        return settings_dir

    def _get_settings_file(self) -> str:
        """Get the settings file path."""
        return os.path.join(self._get_settings_dir(), 'settings.json')

    def _load_language_preference(self):
        """Load language preference from settings file."""
        try:
            settings_file = self._get_settings_file()
            if os.path.exists(settings_file):
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    self._current_language = settings.get('language', 'cs')
                    logger.info(f"Loaded language preference: {self._current_language}")
        except Exception as e:
            logger.warning(f"Failed to load language preference: {e}")
            self._current_language = 'cs'

    def _save_language_preference(self):
        """Save language preference to settings file."""
        try:
            settings_file = self._get_settings_file()

            # Load existing settings if any
            settings = {}
            if os.path.exists(settings_file):
                try:
                    with open(settings_file, 'r', encoding='utf-8') as f:
                        settings = json.load(f)
                except Exception:
                    pass

            # Update language
            settings['language'] = self._current_language

            # Save
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved language preference: {self._current_language}")
        except Exception as e:
            logger.warning(f"Failed to save language preference: {e}")

    def get(self, key: str, *args) -> str:
        """
        Get translated string for the given key.

        Args:
            key: Translation key
            *args: Format arguments for the string

        Returns:
            Translated string with format arguments applied
        """
        try:
            translations = TRANSLATIONS.get(self._current_language, TRANSLATIONS['cs'])
            text = translations.get(key, key)

            # Apply format arguments if provided
            if args:
                return text.format(*args)
            return text
        except Exception as e:
            logger.warning(f"Translation error for key '{key}': {e}")
            return key

    def get_current_language(self) -> str:
        """Get current language code."""
        return self._current_language

    def set_language(self, language: str):
        """
        Set current language.

        Args:
            language: Language code ('cs' or 'en')
        """
        if language not in TRANSLATIONS:
            logger.warning(f"Unsupported language: {language}")
            return

        self._current_language = language
        self._save_language_preference()

        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(language)
            except Exception as e:
                logger.warning(f"Language change callback error: {e}")

    def register_callback(self, callback):
        """Register a callback to be called when language changes."""
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def unregister_callback(self, callback):
        """Unregister a language change callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def get_plural(self, count: int, key_base: str) -> str:
        """
        Get plural form for a count.

        Args:
            count: Number to determine plural form
            key_base: Base key (e.g. 'author', 'branch')

        Returns:
            Translated plural form
        """
        if self._current_language == 'cs':
            # Czech has 3 plural forms
            if count == 1:
                key = f'{key_base}_1'
            elif count in [2, 3, 4]:
                key = f'{key_base}_2_4'
            else:
                key = f'{key_base}_5'
        else:
            # English has 2 forms
            if count == 1:
                key = f'{key_base}_1'
            else:
                key = f'{key_base}_5'

        return self.get(key)


# Global instance
_translation_manager = TranslationManager()


def get_translation_manager() -> TranslationManager:
    """Get the global TranslationManager instance."""
    return _translation_manager


def t(key: str, *args) -> str:
    """Shorthand for getting a translation."""
    return _translation_manager.get(key, *args)
