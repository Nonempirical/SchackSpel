@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

set "DEBUG_MODE=0"
if /I "%~1"=="--debug" set "DEBUG_MODE=1"
if /I "%~1"=="-d" set "DEBUG_MODE=1"

if "%DEBUG_MODE%"=="1" (
    echo [DEBUG] Debug mode enabled.
    echo [DEBUG] Working directory: %CD%
)

where python >nul 2>nul
if errorlevel 1 (
    echo Python hittades inte i PATH.
    echo Installera Python och prova igen.
    pause
    exit /b 1
)

if "%DEBUG_MODE%"=="1" (
    python --version
    echo [DEBUG] STOCKFISH_PATH=%STOCKFISH_PATH%
)

REM Du kan satta en fast sokvag har:
REM set "STOCKFISH_PATH=C:\path\to\stockfish.exe"

set "AUTO_DETECTED=0"
if "%STOCKFISH_PATH%"=="" (
    if exist "%~dp0stockfish.exe" (
        set "STOCKFISH_PATH=%~dp0stockfish.exe"
        set "AUTO_DETECTED=1"
    )
)

if "%STOCKFISH_PATH%"=="" (
    for /f "delims=" %%I in ('dir /b /s "%~dp0stockfish*.exe" 2^>nul') do (
        set "STOCKFISH_PATH=%%I"
        set "AUTO_DETECTED=1"
        goto :stockfish_ready
    )
)

if "%STOCKFISH_PATH%"=="" (
    for /f "delims=" %%I in ('where stockfish.exe 2^>nul') do (
        set "STOCKFISH_PATH=%%I"
        set "AUTO_DETECTED=1"
        goto :stockfish_ready
    )
)

:stockfish_ready
if "%STOCKFISH_PATH%"=="" (
    echo STOCKFISH_PATH ar inte satt.
    if exist "%~dp0stockfish\src\main.cpp" (
        echo.
        echo Obs: Jag hittade en "stockfish"-kallkodsmapp men ingen .exe-motor.
        echo Du behover en kompilerad binar, t.ex. stockfish-windows-... .exe
    )
    echo.
    echo Snabb fix:
    echo 1^) Lagg en Stockfish .exe i projektmappen ^(eller i en undermapp^), eller
    echo 2^) Satt variabeln manuellt:
    echo Exempel:
    echo   set "STOCKFISH_PATH=C:\path\to\stockfish.exe"
    echo Sat variabeln och kor sedan start.bat igen.
    pause
    exit /b 1
)

if "%AUTO_DETECTED%"=="1" (
    echo Hittade Stockfish automatiskt: %STOCKFISH_PATH%
)
if "%DEBUG_MODE%"=="1" (
    echo [DEBUG] Resolved STOCKFISH_PATH=%STOCKFISH_PATH%
)

if "%DEBUG_MODE%"=="1" (
    echo [DEBUG] Running: python -X dev -u main.py
    python -X dev -u main.py
) else (
    python main.py
)

set "exit_code=%errorlevel%"
echo Program exited with code %exit_code%.
if "%DEBUG_MODE%"=="1" (
    pause
) else (
    if not "%exit_code%"=="0" pause
)
exit /b %exit_code%
