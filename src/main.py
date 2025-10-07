#!/usr/bin/env python3

import sys
import os
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.main_window import MainWindow
from utils.logging_config import setup_logging


def check_git_installed():
    """
    Zkontroluje, zda je Git nainstalovaný a dostupný v PATH.

    Returns:
        True pokud je Git dostupný, False jinak
    """
    try:
        # Zkusit spustit 'git --version'
        result = subprocess.run(
            ['git', '--version'],
            capture_output=True,
            check=True,
            timeout=5
        )
        return True
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False


def show_git_missing_dialog():
    """Zobrazí dialog s informací o chybějícím Gitu."""
    try:
        import tkinter as tk
        from tkinter import messagebox

        # Vytvořit dočasné root okno (skryté)
        root = tk.Tk()
        root.withdraw()

        # Zobrazit error dialog
        messagebox.showerror(
            "Git není nainstalován",
            "Pro běh Git Visualizer je potřeba nainstalovat Git.\n\n"
            "Stáhněte Git z:\nhttps://git-scm.com/downloads\n\n"
            "Po instalaci Gitu restartujte aplikaci."
        )

        root.destroy()
    except Exception:
        # Fallback pokud tkinter selže
        print("CHYBA: Git není nainstalován.")
        print("Stáhněte Git z: https://git-scm.com/downloads")
        print("Po instalaci restartujte aplikaci.")


def main():
    # Zkontrolovat, zda je Git nainstalovaný
    if not check_git_installed():
        show_git_missing_dialog()
        sys.exit(1)

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
