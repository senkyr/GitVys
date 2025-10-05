#!/usr/bin/env python3
"""
Build script pro vytvoření GitVisualizer.exe pomocí PyInstaller
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def main():
    print("GitVisualizer Build Script")
    print("=" * 40)

    # Kontrola, že jsme ve správné složce (root projektu)
    if not os.path.exists("src/main.py"):
        print("CHYBA: src/main.py nenalezen. Spust script z root slozky projektu.")
        sys.exit(1)

    # Kontrola tkinter
    try:
        import tkinter
        print("OK: tkinter dostupny")
    except ImportError:
        print("CHYBA: tkinter neni dostupny. Nainstaluj Python s tkinter support.")
        sys.exit(1)

    # Kontrola PyInstaller verze
    try:
        result = subprocess.run(["pyinstaller", "--version"], capture_output=True, check=True, text=True)
        version = result.stdout.strip()
        print(f"OK: PyInstaller {version} nalezen")

        # Zkontrolovat že máme alespoň verzi 6.x pro správný tkinter support
        major_version = int(version.split('.')[0])
        if major_version < 6:
            print(f"Aktualizuji PyInstaller z verze {version} na nejnovejsi...")
            subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pyinstaller"], check=True)
            print("OK: PyInstaller aktualizovan")

    except (subprocess.CalledProcessError, FileNotFoundError):
        print("PyInstaller nenalezen. Instaluji nejnovejsi verzi...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
        print("OK: PyInstaller nainstalan")

    # Vyčištění předchozích buildů
    print("\nMazani predchozich buildu...")

    # Pokus o smazání s chytrou error handling
    def safe_remove(path, is_file=False):
        try:
            if is_file:
                os.remove(path)
            else:
                shutil.rmtree(path)
            return True
        except (PermissionError, FileNotFoundError):
            return False

    if os.path.exists("dist"):
        if not safe_remove("dist"):
            print("VAROVANI: Nelze smazat dist/ - mozna je .exe spusteny. Pokracuji...")

    if os.path.exists("build/temp"):
        safe_remove("build/temp")

    if os.path.exists("GitVisualizer.spec"):
        safe_remove("GitVisualizer.spec", is_file=True)

    # PyInstaller parametry
    pyinstaller_args = [
        "pyinstaller",
        "--onefile",                    # Jeden .exe soubor
        "--windowed",                   # Bez console okna
        "--name=GitVisualizer",         # Název výsledného .exe
        "--icon=build/icon.ico",        # Ikona pro .exe (Tk feather logo)
        "--distpath=dist",              # Výstupní složka
        "--workpath=build/temp",        # Dočasná složka
        "--clean",                      # Vyčistit cache
        "--noconfirm",                  # Přepsat bez dotazu

        # Skryté importy pro kompletní funkcionalitu
        "--hidden-import=tkinter",
        "--hidden-import=tkinter.ttk",
        "--hidden-import=tkinter.messagebox",
        "--hidden-import=tkinter.filedialog",
        "--hidden-import=tkinter.constants",
        "--hidden-import=tkinter.font",
        "--hidden-import=tkinter.scrolledtext",
        "--hidden-import=tkinter.simpledialog",
        "--hidden-import=_tkinter",
        "--hidden-import=tkinterdnd2",
        "--hidden-import=git",
        "--hidden-import=gitdb",
        "--hidden-import=PIL",
        "--hidden-import=PIL.Image",
        "--hidden-import=PIL.ImageTk",

        # Exclude nepotřebné moduly pro menší velikost
        "--exclude-module=matplotlib",
        "--exclude-module=numpy",
        "--exclude-module=scipy",
        "--exclude-module=pandas",
        "--exclude-module=jupyter",
        "--exclude-module=IPython",
        "--exclude-module=pytest",
        "--exclude-module=sphinx",

        "src/main.py"                   # Vstupní soubor
    ]

    print("\nSpoustim PyInstaller...")
    print("Parametry:", " ".join(pyinstaller_args[1:]))

    try:
        result = subprocess.run(pyinstaller_args, check=True, capture_output=False)
        print("\nOK: Build uspesny!")

        # Kontrola výsledku
        exe_path = Path("dist/GitVisualizer.exe")
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"Vysledny soubor: {exe_path}")
            print(f"Velikost: {size_mb:.1f} MB")

            # Jednoduchý test spuštění
            print("\nTestovani .exe souboru...")
            try:
                # Spustit a okamžitě ukončit (jen test že se spustí)
                proc = subprocess.Popen([str(exe_path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                # Počkat chvilku a ukončit
                import time
                time.sleep(2)
                proc.terminate()
                proc.wait(timeout=5)
                print("OK: .exe soubor se spousta spravne")
            except Exception as e:
                print(f"VAROVANI: Test spusteni selhal: {e}")

        else:
            print("CHYBA: .exe soubor nebyl vytvoren")
            sys.exit(1)

    except subprocess.CalledProcessError as e:
        print(f"CHYBA: Build selhal: {e}")
        sys.exit(1)

    print("\nBuild dokoncen!")

    # Cleanup build/temp
    print("Mazani docasnych build souboru...")
    if os.path.exists("build/temp"):
        if safe_remove("build/temp"):
            print("OK: build/temp/ smazan")
        else:
            print("VAROVANI: Nelze smazat build/temp/ - smazte rucne")

    print(f"\nSpustitelny soubor: dist\\GitVisualizer.exe")
    print("Pro vytvoreni dalsiho buildu spust: build\\build-exe.bat")

if __name__ == "__main__":
    main()
