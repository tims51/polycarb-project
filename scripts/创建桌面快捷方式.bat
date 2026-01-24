@echo off
chcp 65001 >nul
echo.
echo ========================================
echo   创建桌面快捷方式
echo ========================================
echo.

REM 获取当前目录
set "CURRENT_DIR=%~dp0"
set "BAT_FILE=%CURRENT_DIR%启动系统.bat"

REM 创建快捷方式 (使用PowerShell直接指向批处理文件)
echo [系统] 正在创建桌面快捷方式...
powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\Desktop\聚羧酸研发系统.lnk'); $Shortcut.TargetPath = '%BAT_FILE%'; $Shortcut.WorkingDirectory = '%CURRENT_DIR%'; $Shortcut.WindowStyle = 1; $Shortcut.Save()"

echo.
echo ✓ 快捷方式创建成功！
echo.
echo 桌面图标: 聚羧酸研发系统.lnk
echo.
echo 使用说明:
echo 1. 双击桌面图标启动系统
echo 2. 系统将在浏览器中打开 (http://localhost:8501)
echo 3. 关闭浏览器窗口后，可在终端按 Ctrl+C 退出
echo ========================================
echo.
pause