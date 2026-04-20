@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo Python hittades inte i PATH.
    echo Installera Python och prova igen.
    exit /b 1
)

echo Installerar beroenden fran requirements.txt...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo Installationen misslyckades.
    exit /b 1
)

echo Klart! Starta programmet med start.bat
exit /b 0
