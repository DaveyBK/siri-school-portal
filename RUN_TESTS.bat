@echo off
REM Hardware Scanner Test Script
REM Run this from Windows to test the scanner integration

echo ============================================================
echo HARDWARE SCANNER TEST SUITE
echo ============================================================
echo.

REM Change to the script directory
cd /d "%~dp0"

echo Running scanner tests...
echo.

python test_scanner.py

echo.
echo ============================================================
echo Test complete! Check output above for results.
echo ============================================================
echo.
pause
