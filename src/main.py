#!/usr/bin/env python3

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.main_window import MainWindow
from utils.logging_config import setup_logging


def main():
    # Inicializovat logging pouze v dev módu nebo s DEBUG env var
    # V produkční .exe se log soubor nevytváří (neznečišťuje systém uživatele)
    if getattr(sys, 'frozen', False):
        # Frozen .exe - logovat jen když GITVIS_DEBUG=1
        enable_logging = os.environ.get('GITVIS_DEBUG') == '1'
    else:
        # Dev mód (Python script) - vždy logovat
        enable_logging = True

    if enable_logging:
        setup_logging()

    try:
        app = MainWindow()
        app.run()
    except KeyboardInterrupt:
        print("\nAplikace ukončena uživatelem.")
    except Exception as e:
        print(f"Neočekávaná chyba: {e}")


if __name__ == "__main__":
    main()
