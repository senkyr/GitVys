#!/usr/bin/env python3

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.main_window import MainWindow


def main():
    try:
        app = MainWindow()
        app.run()
    except KeyboardInterrupt:
        print("\nAplikace ukončena uživatelem.")
    except Exception as e:
        print(f"Neočekávaná chyba: {e}")


if __name__ == "__main__":
    main()
