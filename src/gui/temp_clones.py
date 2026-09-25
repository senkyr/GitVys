"""Dočasné složky pro klony z URL, oddělené pro každou běžící instanci aplikace.

Struktura v systémovém temp::

    gitvys_instance_XXXX/
        instance.lock     # PID + zámek držený po celou dobu běhu instance
        clone_YYYY/       # jednotlivé klony

Úklid při startu smaže jen složky instancí, jejichž zámek už nikdo nedrží
(proces skončil nebo spadl). Zámek uvolní operační systém i při pádu, takže
na rozdíl od samotného PID nevadí ani recyklace PID jiným procesem. Dřív se
při startu mazaly všechny ``gitvys_clone_*`` - včetně klonu, se kterým
právě pracovala jiná spuštěná instance.
"""

import os
import shutil
import stat
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional

from utils.logging_config import get_logger

logger = get_logger(__name__)

INSTANCE_PREFIX = 'gitvys_instance_'
LOCK_NAME = 'instance.lock'
LEGACY_CLONE_PREFIX = 'gitvys_clone_'  # Klony starších verzí (přímo v temp, bez zámku)

# Složka instance bez zámku může patřit instanci, která ho právě zakládá
UNLOCKED_GRACE_SECONDS = 60 * 60
# Klon staré verze mohla vytvořit stále běžící stará instance - mazat jen staré
LEGACY_MAX_AGE_SECONDS = 24 * 60 * 60


def _remove_readonly(func, path, _exc):
    """Error handler pro rmtree: Git na Windows zakládá read-only objekty."""
    if func in (os.unlink, os.rmdir, os.remove):
        os.chmod(path, stat.S_IWRITE)
        func(path)
    else:
        raise


def rmtree_force(path) -> None:
    """Smaže strom včetně read-only souborů (onexc od Pythonu 3.12, dřív onerror)."""
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=_remove_readonly)
    else:
        shutil.rmtree(path, onerror=_remove_readonly)


def _try_lock(file_obj) -> bool:
    """Neblokující exkluzivní zámek na otevřeném souboru; True = získán."""
    try:
        file_obj.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(file_obj.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(file_obj.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        return False


def _unlock(file_obj) -> None:
    try:
        file_obj.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(file_obj.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(file_obj.fileno(), fcntl.LOCK_UN)
    except OSError:
        pass


def _age_seconds(path: Path) -> float:
    try:
        return time.time() - path.stat().st_mtime
    except OSError:
        return 0.0


def is_instance_dir_orphaned(instance_dir: Path) -> bool:
    """True, pokud složku instance nedrží žádný běžící proces."""
    lock_path = instance_dir / LOCK_NAME
    if not lock_path.exists():
        # Bez zámku: buď ho instance právě zakládá, nebo zbytek po pádu při startu
        return _age_seconds(instance_dir) > UNLOCKED_GRACE_SECONDS
    try:
        with open(lock_path, 'a+') as lock_file:
            if _try_lock(lock_file):
                _unlock(lock_file)
                return True
            return False
    except OSError:
        # Soubor nejde ani otevřít - bezpečnější ho nechat být
        return False


class TempCloneArea:
    """Složka dočasných klonů jedné instance aplikace."""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir or tempfile.gettempdir())
        self.instance_dir = Path(tempfile.mkdtemp(prefix=INSTANCE_PREFIX, dir=str(self.base_dir)))
        self._lock_file = open(self.instance_dir / LOCK_NAME, 'a+')
        if not _try_lock(self._lock_file):
            logger.warning(f"Could not lock temp clone area {self.instance_dir}")
        self._lock_file.seek(0)
        self._lock_file.truncate()
        self._lock_file.write(str(os.getpid()))
        self._lock_file.flush()

    def new_clone_dir(self) -> str:
        """Vytvoří prázdnou složku pro nový klon."""
        return tempfile.mkdtemp(prefix='clone_', dir=str(self.instance_dir))

    def cleanup_orphans(self) -> int:
        """Smaže složky instancí, které už neběží, a staré klony předchozích verzí.

        Returns:
            Počet smazaných složek
        """
        removed = 0
        try:
            candidates = list(self.base_dir.iterdir())
        except OSError as e:
            logger.warning(f"Failed to list temp directory {self.base_dir}: {e}")
            return 0

        for path in candidates:
            try:
                if not path.is_dir() or path == self.instance_dir:
                    continue
                if path.name.startswith(INSTANCE_PREFIX):
                    orphaned = is_instance_dir_orphaned(path)
                elif path.name.startswith(LEGACY_CLONE_PREFIX):
                    orphaned = _age_seconds(path) > LEGACY_MAX_AGE_SECONDS
                else:
                    continue
                if orphaned:
                    rmtree_force(path)
                    removed += 1
            except Exception as e:
                logger.warning(f"Failed to cleanup orphaned temp clone {path}: {e}")
        return removed

    def close(self) -> None:
        """Uvolní zámek a smaže složku instance (volá se při ukončení)."""
        if self._lock_file is not None:
            _unlock(self._lock_file)
            try:
                self._lock_file.close()
            except OSError:
                pass
            self._lock_file = None
        try:
            if self.instance_dir.exists():
                rmtree_force(self.instance_dir)
        except Exception as e:
            logger.warning(f"Failed to remove temp clone area {self.instance_dir}: {e}")
