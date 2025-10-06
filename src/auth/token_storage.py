"""
Ukládání a načítání GitHub access tokenu.
"""

import os
import stat
from pathlib import Path
from utils.logging_config import get_logger

logger = get_logger(__name__)


class TokenStorage:
    """Spravuje ukládání GitHub tokenu do lokálního souboru."""

    def __init__(self):
        # Určit cestu k config složce podle OS
        if os.name == 'nt':  # Windows
            config_dir = Path(os.environ.get('USERPROFILE', '~')) / '.gitvys'
        else:  # Linux/Mac
            config_dir = Path.home() / '.gitvys'

        self.config_dir = config_dir
        self.token_file = config_dir / 'github_token'

    def save_token(self, token: str) -> bool:
        """
        Uloží GitHub token do souboru.

        Args:
            token: GitHub access token

        Returns:
            True pokud se podařilo uložit, False při chybě
        """
        try:
            # Vytvořit config složku pokud neexistuje
            self.config_dir.mkdir(parents=True, exist_ok=True)

            # Uložit token do souboru
            self.token_file.write_text(token, encoding='utf-8')

            # Nastavit permissions na 600 (read/write jen pro vlastníka)
            # Na Windows toto může selhat, ale není to kritické
            try:
                os.chmod(self.token_file, stat.S_IRUSR | stat.S_IWUSR)
            except Exception as e:
                logger.debug(f"Could not set file permissions (Windows?): {e}")

            logger.info(f"GitHub token saved to {self.token_file}")
            return True

        except Exception as e:
            logger.warning(f"Failed to save GitHub token: {e}")
            return False

    def load_token(self) -> str:
        """
        Načte GitHub token ze souboru.

        Returns:
            Token string nebo None pokud token neexistuje/nelze načíst
        """
        try:
            if not self.token_file.exists():
                logger.debug("No GitHub token found")
                return None

            token = self.token_file.read_text(encoding='utf-8').strip()

            if not token:
                logger.debug("GitHub token file is empty")
                return None

            logger.info("GitHub token loaded successfully")
            return token

        except Exception as e:
            logger.warning(f"Failed to load GitHub token: {e}")
            return None

    def delete_token(self) -> bool:
        """
        Smaže uložený GitHub token.

        Returns:
            True pokud se podařilo smazat nebo token neexistoval, False při chybě
        """
        try:
            if self.token_file.exists():
                self.token_file.unlink()
                logger.info("GitHub token deleted")
            return True

        except Exception as e:
            logger.warning(f"Failed to delete GitHub token: {e}")
            return False

    def token_exists(self) -> bool:
        """
        Zkontroluje, zda existuje uložený token.

        Returns:
            True pokud token existuje, False jinak
        """
        return self.token_file.exists() and self.token_file.stat().st_size > 0
