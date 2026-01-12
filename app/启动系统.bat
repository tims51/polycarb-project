@echo off
chcp 65001 >nul
echo.
echo ========================================
echo   聚羧酸减水剂研发管理系统
echo ========================================
echo.

REM 检查Python环境
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未检测到Python，请先安装Python 3.7+
    echo 访问 https://www.python.org/downloads/
    pause
    exit
)

REM 检查并安装依赖
echo 正在检查依赖包...
if exist requirements.txt (
    pip install -r requirements.txt
) else (
    echo 正在安装必需包...
    pip install streamlit pandas plotly
)

echo.
echo 启动应用中 (已启用远程访问模式)...
echo 应用将在浏览器中自动打开...
echo 如果未自动打开，请访问: http://localhost:8501
echo ========================================
echo.

REM 切换到上级目录并启动互联网模式
cd ..
python run_internet_mode.py

pause