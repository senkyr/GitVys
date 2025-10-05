@echo off
echo GitVisualizer Build Script
echo ========================
echo.

REM Prepnout do root slozky projektu
cd /d "%~dp0\.."

REM Spustit build script
python build\build.py

echo.
echo Build dokoncen! Vysledek je v dist\ slozce.
pause