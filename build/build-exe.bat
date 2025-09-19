@echo off
echo GitVisualizer Build Script
echo ========================
echo.

REM Přepnout do root složky projektu
cd /d "%~dp0\.."

REM Spustit build script
python build\build.py

echo.
echo Build dokončen! Výsledek je v dist\ složce.
pause