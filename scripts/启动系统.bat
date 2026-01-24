@echo off
chcp 65001 >nul
echo.
echo ========================================
echo   聚羧酸减水剂研发管理系统
echo ========================================
echo.

REM 检查并定位 Python 环境
set "PYTHON_CMD=python"
%PYTHON_CMD% --version >nul 2>&1
if errorlevel 1 (
    if exist "%LOCALAPPDATA%\Python\bin\python.exe" (
        set "PYTHON_CMD=%LOCALAPPDATA%\Python\bin\python.exe"
    ) else if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
        set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    ) else if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
        set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    ) else if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" (
        set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    ) else (
        echo 错误: 未检测到 Python 环境，请先安装 Python 3.8+
        echo 访问 https://www.python.org/downloads/ 下载并安装
        echo [提示] 安装时请务必勾选 "Add Python to PATH"
        pause
        exit /b 1
    )
)

echo [环境] 使用 Python: %PYTHON_CMD%

REM --- [优化] 智能跳过依赖安装 ---
if exist ".env_installed" (
    echo [系统] 检测到依赖已安装，跳过检查...
) else (
    echo [系统] 正在首次安装依赖环境 (仅首次启动或清理后执行)...
    if exist requirements.txt (
        %PYTHON_CMD% -m pip install -r requirements.txt
    ) else if exist ..\requirements.txt (
        %PYTHON_CMD% -m pip install -r ..\requirements.txt
    ) else (
        echo [警告] 未找到 requirements.txt，将安装基础依赖...
        %PYTHON_CMD% -m pip install streamlit pandas plotly
    )
    REM 创建标记文件
    echo done > .env_installed
)

echo.
echo 启动应用中 (已启用远程访问模式)...
echo 应用将在浏览器中自动打开...
echo 如果未自动打开，请访问: http://localhost:8501
echo ========================================
echo.

REM 切换到上级目录并启动互联网模式
cd ..
%PYTHON_CMD% scripts/run_internet_mode.py

pause