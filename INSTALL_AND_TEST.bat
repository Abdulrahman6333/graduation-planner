@echo off
setlocal
cd /d "%~dp0"
title Graduation Planner - Install and Test

echo ============================================
echo Rebuilding the Python environment
echo ============================================

py -3.12 --version >nul 2>&1
if errorlevel 1 (
    echo Python 3.12 was not found.
    echo Install Python 3.12 64-bit, then run this file again.
    pause
    exit /b 1
)

if exist ".venv" rmdir /s /q ".venv"

py -3.12 -m venv .venv
if errorlevel 1 goto :error

call .venv\Scripts\activate

python -m pip install --upgrade pip setuptools wheel
if errorlevel 1 goto :error

python -m pip install -r requirements_desktop.txt
if errorlevel 1 goto :error

echo.
echo Verifying PyMuPDF...
python -c "import pymupdf; print('PyMuPDF OK:', pymupdf.__doc__[:20])"
if errorlevel 1 goto :error

echo.
echo Starting Graduation Planner...
python desktop_launcher.py
exit /b 0

:error
echo.
echo Installation failed.
echo Copy the last red/error lines and send them.
pause
exit /b 1
