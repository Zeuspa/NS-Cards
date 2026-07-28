@echo off
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo [error] python not found on PATH. Install from https://www.python.org/downloads/
    pause
    exit /b 1
)

python -u ns_card_ping_watcher.py %* --show-ratelimit --watch

echo.
echo Finished. Press any key to close.
pause >nul
