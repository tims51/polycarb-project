@echo off
setlocal

:loop
echo.
echo ========================================================
echo [Watchdog] Starting Mobile Server...
echo ========================================================
echo.
echo 注意: 
echo 1. 请确保您的手机和电脑连接在同一个 Wi-Fi 网络下
echo 2. 如果是第一次运行，Windows 防火墙可能会弹出提示，请务必允许"专用网络"访问
echo.

streamlit run src/main.py --server.address 0.0.0.0

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
