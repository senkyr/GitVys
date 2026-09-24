"""
Ukládání a načítání GitHub access tokenu.

Token dává přístup ke všem repozitářům uživatele (scope ``repo``), proto se
neukládá jako čitelný text:

- **Windows:** token je zašifrovaný přes DPAPI (``CryptProtectData``) a vázaný
  na účet přihlášeného uživatele. Jiný uživatel ani kopie souboru na jiný
  počítač ho nerozšifruje.
- **Linux/macOS:** DPAPI neexistuje; soubor se vytváří rovnou s právy 0600
  (jen vlastník), aby nevznikla chvíle, kdy je čitelný pro ostatní.

Starší verze ukládaly token jako prostý text. Takový soubor se při načtení
přečte a na Windows hned přepíše do zašifrované podoby.
"""

import base64
import os
import tempfile
from pathlib import Path
from typing import Optional

from utils.logging_config import get_logger

logger = get_logger(__name__)

# Prefix souboru se šifrovaným tokenem (DPAPI). Cokoli jiného je starý plaintext.
_DPAPI_PREFIX = "dpapi:v1:"


class TokenProtectionError(Exception):
    """Token nejde zašifrovat nebo rozšifrovat."""


def _dpapi_available() -> bool:
    return os.name == 'nt'


def _dpapi_call(data: bytes, protect: bool) -> bytes:
    """Zašifruje/rozšifruje data přes Windows DPAPI (bez externích závislostí)."""
    import ctypes
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD),
                    ("pbData", ctypes.POINTER(ctypes.c_char))]

    crypt32 = ctypes.WinDLL('crypt32', use_last_error=True)
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p

    func = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
    func.argtypes = [ctypes.POINTER(DATA_BLOB), ctypes.c_void_p, ctypes.POINTER(DATA_BLOB),
                     ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(DATA_BLOB)]
    func.restype = wintypes.BOOL

    buffer = ctypes.create_string_buffer(data, len(data))
    blob_in = DATA_BLOB(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)))
    blob_out = DATA_BLOB()
    CRYPTPROTECT_UI_FORBIDDEN = 0x01

    if not func(ctypes.byref(blob_in), None, None, None, None,
                CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(blob_out)):
        raise TokenProtectionError(f"DPAPI selhalo (chyba {ctypes.get_last_error()})")
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        kernel32.LocalFree(ctypes.cast(blob_out.pbData, ctypes.c_void_p))


class TokenStorage:
    """Spravuje uložení GitHub tokenu v ``~/.gitvys/github_token``."""

    def __init__(self):
        # Určit cestu k config složce podle OS
        if os.name == 'nt':  # Windows
            config_dir = Path(os.environ.get('USERPROFILE', '~')) / '.gitvys'
        else:  # Linux/Mac
            config_dir = Path.home() / '.gitvys'

        self.config_dir = config_dir
        self.token_file = config_dir / 'github_token'

    # --- serializace -----------------------------------------------------

    @staticmethod
    def _encode(token: str) -> str:
        """Převede token na obsah souboru (na Windows zašifrovaný)."""
        if not token or not _dpapi_available():
            return token
        blob = _dpapi_call(token.encode('utf-8'), protect=True)
        return _DPAPI_PREFIX + base64.b64encode(blob).decode('ascii')

    @staticmethod
    def _decode(content: str) -> str:
        """Převede obsah souboru na token. Plaintext (starý formát) vrací beze změny."""
        if content.startswith(_DPAPI_PREFIX):
            if not _dpapi_available():
                raise TokenProtectionError("Token je zašifrovaný DPAPI, které tu není k dispozici")
            blob = base64.b64decode(content[len(_DPAPI_PREFIX):])
            return _dpapi_call(blob, protect=False).decode('utf-8')
        return content

    def _write_private(self, content: str) -> None:
        """Atomicky zapíše soubor tak, aby nikdy nebyl čitelný pro ostatní uživatele."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=str(self.config_dir), prefix='.github_token.')
        # mkstemp vytváří soubor s právy 0600 už při vzniku
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(content)
            os.replace(tmp_path, self.token_file)
        except BaseException:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    # --- veřejné API -----------------------------------------------------

    def save_token(self, token: str) -> bool:
        """
        Uloží GitHub token do souboru (na Windows zašifrovaný přes DPAPI).

        Args:
            token: GitHub access token

        Returns:
            True pokud se podařilo uložit, False při chybě
        """
        try:
            self._write_private(self._encode(token))
            logger.info(f"GitHub token saved to {self.token_file}")
            return True
        except Exception as e:
            logger.warning(f"Failed to save GitHub token: {e}")
            return False

    def load_token(self) -> Optional[str]:
        """
        Načte GitHub token ze souboru.

        Returns:
            Token nebo None, pokud token neexistuje nebo nejde načíst
        """
        try:
            if not self.token_file.exists():
                logger.debug("No GitHub token found")
                return None

            content = self.token_file.read_text(encoding='utf-8').strip()
            if not content:
                logger.debug("GitHub token file is empty")
                return None

            token = self._decode(content).strip()
            if not token:
                return None

            # Starý plaintext formát → přepsat zašifrovaně
            if not content.startswith(_DPAPI_PREFIX) and _dpapi_available():
                if self.save_token(token):
                    logger.info("Plaintext GitHub token migrated to DPAPI storage")

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
