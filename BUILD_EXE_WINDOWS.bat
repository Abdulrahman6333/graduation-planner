@echo off
setlocal
cd /d "%~dp0"
title Graduation Planner EXE Builder

echo ============================================
echo Graduation Planner EXE Builder
echo ============================================

py -3.12 --version >nul 2>&1
if errorlevel 1 (
    echo Python 3.12 was not found.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Environment not found. Run INSTALL_AND_TEST.bat first.
    pause
    exit /b 1
)

call .venv\Scripts\activate

python -c "import pymupdf; print('PyMuPDF ready')"
if errorlevel 1 (
    echo PyMuPDF is missing. Run INSTALL_AND_TEST.bat first.
    pause
    exit /b 1
)

if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "GraduationPlanner.spec" del /q "GraduationPlanner.spec"

pyinstaller --noconfirm --clean --onedir --windowed ^
  --name GraduationPlanner ^
  --collect-all streamlit ^
  --collect-all pymupdf ^
  --collect-all openpyxl ^
  --collect-all reportlab ^
  --collect-all arabic_reshaper ^
  --collect-all bidi ^
  --hidden-import pymupdf ^
  --hidden-import fitz ^
  --hidden-import streamlit.web.cli ^
  --hidden-import arabic_reshaper ^
  --hidden-import bidi.algorithm ^
  --add-data "app.py;." ^
  desktop_launcher.py

if errorlevel 1 goto :error

echo.
echo Build completed:
echo dist\GraduationPlanner\GraduationPlanner.exe
echo Keep the whole GraduationPlanner folder.
pause
exit /b 0

:error
echo.
echo BUILD FAILED.
echo Copy the last error lines and send them.
pause
exit /b 1
