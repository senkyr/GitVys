"""
Centralizované nastavení logování pro GitVisualizer
"""
import logging
import sys
from pathlib import Path


def setup_logging(log_file: str = 'gitvisualizer.log', level: int = logging.WARNING):
    """
    Nastaví logování pro celou aplikaci.

    Args:
        log_file: Název log souboru
        level: Úroveň logování (logging.DEBUG, INFO, WARNING, ERROR)
    """
    # Vytvoř logger
    logger = logging.getLogger('gitvisualizer')
    logger.setLevel(level)

    # Pokud už má handlery, neskladuj je znovu
    if logger.handlers:
        return logger

    # Format pro log zprávy
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # File handler - zapisuje do souboru
    try:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        # Pokud nelze vytvořit soubor, pouze varování na stderr
        print(f"Warning: Nelze vytvořit log soubor {log_file}: {e}", file=sys.stderr)

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
