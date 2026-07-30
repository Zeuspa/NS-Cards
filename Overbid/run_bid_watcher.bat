@echo off
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo [error] python not found on PATH. Install from https://www.python.org/downloads/
    pause
    exit /b 1
)

python -u ns_bid_watcher.py %*

echo.
echo Finished. Press any key to close.
pause >nul
