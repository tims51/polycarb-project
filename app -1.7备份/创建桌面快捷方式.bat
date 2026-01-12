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

REM 创建快捷方式
echo Set oWS = WScript.CreateObject("WScript.Shell") > "%TEMP%\create_shortcut.vbs"
echo sLinkFile = "%USERPROFILE%\Desktop\聚羧酸研发系统.lnk" >> "%TEMP%\create_shortcut.vbs"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%TEMP%\create_shortcut.vbs"
echo oLink.TargetPath = "cmd.exe" >> "%TEMP%\create_shortcut.vbs"
echo oLink.Arguments = "/c ""%BAT_FILE%""" >> "%TEMP%\create_shortcut.vbs"
echo oLink.Description = "聚羧酸减水剂研发管理系统" >> "%TEMP%\create_shortcut.vbs"
echo oLink.WorkingDirectory = "%CURRENT_DIR%" >> "%TEMP%\create_shortcut.vbs"
echo oLink.WindowStyle = 4 >> "%TEMP%\create_shortcut.vbs"  REM 最小化窗口启动
echo oLink.Save >> "%TEMP%\create_shortcut.vbs"

cscript //nologo "%TEMP%\create_shortcut.vbs"
del "%TEMP%\create_shortcut.vbs"

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