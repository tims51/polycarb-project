@echo off
chcp 65001 >nul
echo.
echo ========================================
echo   聚羧酸减水剂研发管理系统 (远程模式)
echo ========================================
echo.

REM 检查Python环境
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未检测到Python，请先安装Python 3.7+
    pause
    exit
)

echo 启动应用中 (已启用远程访问模式)...
echo.

cd ..
python scripts/run_internet_mode.py

pause
