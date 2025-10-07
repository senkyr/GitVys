@echo off
echo GitVisualizer Build Script
echo ========================
echo.

REM Prepnout do root slozky projektu
cd /d "%~dp0\.."

REM Kontrola Pythonu
echo Kontroluji dostupnost Pythonu...
python --version >nul 2>&1
if errorlevel 1 (
    echo CHYBA: Python neni dostupny v PATH!
    echo Nainstalujte Python z https://python.org
    pause
    exit /b 1
)
echo OK: Python nalezen
echo.

REM Instalace zakladnich zavislosti
echo Instaluji zavislosti z requirements.txt...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo CHYBA: Instalace zavislosti selhala!
    pause
    exit /b 1
)
echo OK: Zavislosti nainstalovany
echo.

REM Instalace PyInstaller (build zavislost)
echo Instaluji PyInstaller...
python -m pip install pyinstaller
if errorlevel 1 (
    echo CHYBA: Instalace PyInstalleru selhala!
    pause
    exit /b 1
)
echo OK: PyInstaller nainstalan
echo.

REM Spustit build script
echo Spoustim build proces...
python build\build.py

echo.
echo Build dokoncen! Vysledek je v dist\ slozce.
pause