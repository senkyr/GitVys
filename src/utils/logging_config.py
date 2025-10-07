"""
Centralizované nastavení logování pro GitVisualizer
"""
import logging
import sys
import os
from pathlib import Path


def get_log_file_path() -> Path:
    """
    Určí cestu k log souboru podle OS.

    Returns:
        Path k log souboru v ~/.gitvys/ složce
    """
    # Určit cestu k config složce podle OS
    if os.name == 'nt':  # Windows
        config_dir = Path(os.environ.get('USERPROFILE', '~')) / '.gitvys'
    else:  # Linux/Mac
        config_dir = Path.home() / '.gitvys'

    # Vytvořit složku pokud neexistuje
    try:
        config_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        # Pokud nelze vytvořit složku, použít current directory jako fallback
        return Path('gitvisualizer.log')

    return config_dir / 'gitvisualizer.log'


def setup_logging(log_file: str = None, level: int = logging.WARNING):
    """
    Nastaví logování pro celou aplikaci.

    Args:
        log_file: Cesta k log souboru (pokud None, použije se ~/.gitvys/gitvisualizer.log)
        level: Úroveň logování (logging.DEBUG, INFO, WARNING, ERROR)
    """
    # Vytvoř logger
    logger = logging.getLogger('gitvisualizer')
    logger.setLevel(level)

    # Pokud už má handlery, neskladuj je znovu
    if logger.handlers:
        return logger

    # Určit cestu k log souboru
    if log_file is None:
        log_file_path = get_log_file_path()
    else:
        log_file_path = Path(log_file)

    # Format pro log zprávy
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # File handler - zapisuje do souboru
    try:
        file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        # Pokud nelze vytvořit soubor, pouze varování na stderr
        print(f"Warning: Nelze vytvořit log soubor {log_file_path}: {e}", file=sys.stderr)

    # Console handler - pouze pro ERROR a výše (nezahlcovat konzoli)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.ERROR)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Získá logger pro daný modul.

    Args:
        name: Název modulu (např. __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(f'gitvisualizer.{name}')
