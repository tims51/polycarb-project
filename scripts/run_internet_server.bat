@echo off
setlocal

:loop
echo.
echo ========================================================
echo [Watchdog] Starting Internet Server...
echo ========================================================
echo.

python run_internet_mode.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [Watchdog] Server crashed with exit code %ERRORLEVEL%.
    echo [Watchdog] Restarting in 5 seconds...
    echo Press Ctrl+C to stop.
    timeout /t 5 >nul
    goto loop
)

echo.
echo [Watchdog] Server exited normally.
pause
endlocal
