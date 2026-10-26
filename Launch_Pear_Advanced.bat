@echo off
setlocal EnableDelayedExpansion

:: =====================================================
::  Siri English - Pear v2 Advanced Launcher
::  Control panel for running, logging, and backups
:: =====================================================

title Pear v2 - Advanced Launcher
color 0A
echo.
echo  ==================================================
echo      Siri English - Pear v2  (School Portal)
echo              Advanced Launcher - Python 3.13
echo  ==================================================
echo.

:: -----------------------------------------------------
:: 0. Set project directory to the folder of this .bat
:: -----------------------------------------------------
set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"
echo  [*] Project directory: %PROJECT_DIR%
echo.

:: -----------------------------------------------------
:: 1. Detect Python
:: -----------------------------------------------------
set "PYTHON_CMD="

if exist "C:\Python313\python.exe" (
    set "PYTHON_CMD=C:\Python313\python.exe"
    echo  [OK] Found Python 3.13 at: C:\Python313\python.exe
) else (
    echo  [!] C:\Python313\python.exe not found.
    echo      Falling back to 'python' on PATH...
    where python >nul 2>&1
    if errorlevel 1 (
        echo.
        echo  [ERROR] No Python interpreter found.
        echo          Install Python 3.13 to C:\Python313
        echo          or add 'python' to your PATH.
        echo.
        pause
        exit /b 1
    ) else (
        set "PYTHON_CMD=python"
        echo  [OK] Using 'python' from PATH.
    )
)

echo.

:: -----------------------------------------------------
:: Paths for DB, backups, and logs
:: -----------------------------------------------------
set "DATA_DIR=%PROJECT_DIR%data"
set "DB_PATH=%DATA_DIR%\inventory.db"
set "BACKUP_DIR=%PROJECT_DIR%backups"
set "LOG_DIR=%PROJECT_DIR%logs"

if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

:: -----------------------------------------------------
:: Main menu loop
:: -----------------------------------------------------
:MENU
echo.
echo  ===================== MAIN MENU ====================
echo   [1] Run Pear v2 (normal)
echo   [2] Run Pear v2 (DEV mode - log to file)
echo   [3] Open logs folder
echo   [4] Backup database
echo   [5] Open project folder
echo   [6] Run Pear v2 (classic look - theme and DPI off)
echo   [0] Exit
echo  ==================================================
echo.

set "CHOICE="
set /p CHOICE="  Select option: "

if "%CHOICE%"=="1" goto RUN_NORMAL
if "%CHOICE%"=="2" goto RUN_DEV
if "%CHOICE%"=="3" goto OPEN_LOGS
if "%CHOICE%"=="4" goto BACKUP_DB
if "%CHOICE%"=="5" goto OPEN_PROJECT
if "%CHOICE%"=="6" goto RUN_CLASSIC
if "%CHOICE%"=="0" goto EXIT_LAUNCHER

echo.
echo  [!] Invalid choice. Please choose 0-6.
echo.
goto MENU

:: -----------------------------------------------------
:: 1) Run Pear v2 normally
:: -----------------------------------------------------
:RUN_NORMAL
echo.
echo  --------------------------------------------------
echo   RUNNING: Pear v2 (normal mode)
echo  --------------------------------------------------
echo.

set "PORTAL_THEME="

if not exist "app.py" (
    echo  [ERROR] app.py not found in:
    echo          %PROJECT_DIR%
    echo.
    echo  Make sure this launcher is in the same folder
    echo  as app.py.
    echo.
    pause
    goto MENU
)

"%PYTHON_CMD%" app.py
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if "%EXIT_CODE%"=="0" (
    echo  [OK] Pear v2 closed normally.
) else (
    echo  [ERROR] Pear v2 exited with code %EXIT_CODE%.
)
echo.
pause
goto MENU

:: -----------------------------------------------------
:: 2) Run Pear v2 in DEV mode (log to file)
:: -----------------------------------------------------
:RUN_DEV
echo.
echo  --------------------------------------------------
echo   RUNNING: Pear v2 (DEV mode - logging enabled)
echo  --------------------------------------------------
echo.

set "PORTAL_THEME="

if not exist "app.py" (
    echo  [ERROR] app.py not found in:
    echo          %PROJECT_DIR%
    echo.
    pause
    goto MENU
)

:: Build a timestamp for the log filename
set "STAMP=%DATE:~6,4%-%DATE:~3,2%-%DATE:~0,2%_%TIME:~0,2%-%TIME:~3,2%-%TIME:~6,2%"
set "STAMP=%STAMP: =0%"
set "LOG_FILE=%LOG_DIR%\pear_dev_%STAMP%.log"

echo  [*] Logging to: %LOG_FILE%
echo.

"%PYTHON_CMD%" app.py >>"%LOG_FILE%" 2>&1
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if "%EXIT_CODE%"=="0" (
    echo  [OK] Pear v2 closed normally.
) else (
    echo  [ERROR] Pear v2 exited with code %EXIT_CODE%.
    echo         See log: %LOG_FILE%
)
echo.
pause
goto MENU

:: -----------------------------------------------------
:: 3) Open logs folder
:: -----------------------------------------------------
:OPEN_LOGS
echo.
echo  [*] Opening logs folder:
echo      %LOG_DIR%
echo.
start "" "%LOG_DIR%"
goto MENU

:: -----------------------------------------------------
:: 4) Backup database
:: -----------------------------------------------------
:BACKUP_DB
echo.
echo  --------------------------------------------------
echo   DATABASE BACKUP
echo  --------------------------------------------------
echo.

if not exist "%DB_PATH%" (
    echo  [ERROR] Database not found at:
    echo          %DB_PATH%
    echo.
    pause
    goto MENU
)

set "STAMP=%DATE:~6,4%-%DATE:~3,2%-%DATE:~0,2%_%TIME:~0,2%-%TIME:~3,2%-%TIME:~6,2%"
set "STAMP=%STAMP: =0%"
set "BACKUP_FILE=%BACKUP_DIR%\inventory_%STAMP%.db"

copy "%DB_PATH%" "%BACKUP_FILE%" >nul
if errorlevel 1 (
    echo  [ERROR] Backup failed.
) else (
    echo  [OK] Backup created:
    echo      %BACKUP_FILE%
)
echo.
pause
goto MENU

:: -----------------------------------------------------
:: 5) Open project folder
:: -----------------------------------------------------
:OPEN_PROJECT
echo.
echo  [*] Opening project folder:
echo      %PROJECT_DIR%
echo.
start "" "%PROJECT_DIR%"
goto MENU

:: -----------------------------------------------------
:: 6) Run Pear v2 with the pre-2026-09-19 appearance
:: -----------------------------------------------------
:RUN_CLASSIC
echo.
echo  --------------------------------------------------
echo   RUNNING: Pear v2 (classic look)
echo  --------------------------------------------------
echo.
echo  [*] PORTAL_THEME=classic
echo      House theme off, DPI awareness off. Same app,
echo      same data, same behaviour - appearance only.
echo.

if not exist "app.py" (
    echo  [ERROR] app.py not found in:
    echo          %PROJECT_DIR%
    echo.
    pause
    goto MENU
)

set "PORTAL_THEME=classic"
"%PYTHON_CMD%" app.py
set "EXIT_CODE=%ERRORLEVEL%"
set "PORTAL_THEME="

echo.
if "%EXIT_CODE%"=="0" (
    echo  [OK] Pear v2 closed normally.
) else (
    echo  [ERROR] Pear v2 exited with code %EXIT_CODE%.
)
echo.
pause
goto MENU

:: -----------------------------------------------------
:: Exit launcher
:: -----------------------------------------------------
:EXIT_LAUNCHER
echo.
echo  Exiting Pear v2 Advanced Launcher.
echo.
endlocal
exit /b 0
