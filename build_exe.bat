@echo off
setlocal EnableDelayedExpansion

:: -------------------------------------------------------
:: Siri English Inventory GUI - Enhanced EXE Builder
:: -------------------------------------------------------
title Building InventoryGUI.exe
color 0A
echo.
echo ================================================
echo   Siri English Inventory GUI - EXE Builder
echo ================================================
echo.

:: -------------------------------------------------------
:: 1. Detect Python
:: -------------------------------------------------------
echo [1/7] Checking Python...

py --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is NOT installed or not found!
    echo Please install Python from: https://www.python.org/downloads/
    echo.
    pause
    exit /b
)

for /f "tokens=*" %%v in ('py --version') do set py_ver=%%v
echo %py_ver% detected.
echo.

:: -------------------------------------------------------
:: 2. Read version from Python file
:: -------------------------------------------------------
echo [2/7] Reading app version...

if exist app.py (
    set main_file=app.py
) else if exist inventory_gui.py (
    set main_file=inventory_gui.py
) else (
    echo [ERROR] Cannot find main Python file!
    pause
    exit /b
)

for /f "delims=" %%a in ('findstr /B "APP_VERSION" %main_file%') do set ver_line=%%a
set version=%ver_line:APP_VERSION = "%=
set version=%version:"=%

if "%version%"=="" (
    set version=1.0.0
    echo Version not found in file, using default: %version%
) else (
    echo Detected version: %version%
)
echo.

:: -------------------------------------------------------
:: 3. Clean old build files
:: -------------------------------------------------------
echo [3/7] Cleaning old build files...

if exist dist (
    echo Removing dist folder...
    rmdir /s /q dist
)
if exist build (
    echo Removing build folder...
    rmdir /s /q build
)
if exist *.spec (
    echo Removing old spec files...
    del /q *.spec
)
echo Clean complete.
echo.

:: -------------------------------------------------------
:: 4. Check PyInstaller
:: -------------------------------------------------------
echo [4/7] Checking PyInstaller...

py -m pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo PyInstaller not found. Installing...
    py -m pip install pyinstaller
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install PyInstaller!
        pause
        exit /b
    )
)

where pyinstaller >nul 2>&1
if %errorlevel%==0 (
    echo PyInstaller found in PATH.
    set buildcmd=pyinstaller
) else (
    echo Using Python module method.
    set buildcmd=py -m PyInstaller
)
echo.

:: -------------------------------------------------------
:: 5. Build EXE
:: -------------------------------------------------------
echo [5/7] Building EXE... please wait.
echo This may take 10-60 seconds depending on system speed.
echo.

:: Check if icon exists
set icon_param=
if exist siri_english_clean_circle.ico (
    set icon_param=--icon=siri_english_clean_circle.ico
    echo Using icon: siri_english_clean_circle.ico
)

:: Check if version file exists
set version_param=
if exist version_info.txt (
    set version_param=--version-file=version_info.txt
    echo Using version info file
)

:: Build command
%buildcmd% --onefile --noconsole ^
    --name "School Portal" ^
    %icon_param% ^
    %version_param% ^
    %main_file%

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Build failed!
    echo Please scroll up for details.
    echo.
    pause
    exit /b
)

:: -------------------------------------------------------
:: 6. Create portable package (optional)
:: -------------------------------------------------------
echo.
echo [6/7] Creating portable package...

if not exist "dist\InventoryPortable" mkdir "dist\InventoryPortable"

:: Copy EXE
copy "dist\School Portal.exe" "dist\InventoryPortable\" >nul

:: Copy data folders if they exist
if exist data (
    echo Copying data folder...
    xcopy /E /I /Q data "dist\InventoryPortable\data" >nul
)
if exist inventory (
    echo Copying inventory folder...
    xcopy /E /I /Q inventory "dist\InventoryPortable\inventory" >nul
)
if exist exports (
    echo Copying exports folder...
    xcopy /E /I /Q exports "dist\InventoryPortable\exports" >nul
)

:: Create README
echo Creating README...
(
echo ================================================
echo   Siri English Inventory GUI v%version%
echo ================================================
echo.
echo To run this application:
echo 1. Double-click InventoryGUI.exe
echo 2. Wait for the application to load
echo.
echo System Requirements:
echo - Windows 7 or higher
echo - No Python installation required
echo.
echo First Run:
echo - Windows may show a security warning
echo - Click "More info" then "Run anyway"
echo.
echo Data Storage:
echo - All data is stored in the local folders
echo - Keep this folder intact for data persistence
echo.
echo Support: contact@sirienglish.com
echo ================================================
) > "dist\InventoryPortable\README.txt"

:: -------------------------------------------------------
:: 7. Create Auto-Start Registry Entry (Optional)
:: -------------------------------------------------------
echo.
echo [7/7] Creating auto-start option...
echo.
echo Creating registry entry for Windows auto-start...

set exe_path=!cd!\dist\InventoryGUI.exe
set reg_key=HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run

:: Create registry file for auto-start
(
echo Windows Registry Editor Version 5.00
echo.
echo [HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run]
echo "School Portal"="!exe_path!"
) > setup_autostart.reg

echo Created: setup_autostart.reg
echo.
echo To enable auto-start with Windows login:
echo   1. Double-click setup_autostart.reg
echo   2. Click "Yes" when prompted
echo.
echo To disable auto-start later:
echo   1. Open Registry Editor (regedit)
echo   2. Go to: HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run
echo   3. Delete the "School Portal" entry
echo.

:: -------------------------------------------------------
:: 8. Report success
:: -------------------------------------------------------
echo.
echo ================================================
echo   BUILD COMPLETE!
echo ================================================
echo.
echo Version built: %version%
echo Main file used: %main_file%
echo.
echo Files created:
echo   [1] Standalone EXE:
echo       dist\School Portal.exe
echo.
echo   [2] Portable Package:
echo       dist\InventoryPortable\
echo       (includes EXE + data folders + README)
echo.
echo   [3] Auto-Start Registry Entry:
echo       setup_autostart.reg
echo.
echo ================================================
echo.
echo To distribute:
echo   Option 1: Share just the EXE file
echo   Option 2: Zip the InventoryPortable folder
echo   Option 3: Include setup_autostart.reg for auto-start setup
echo.
echo To test: Run dist\School Portal.exe
echo.
pause
exit /b