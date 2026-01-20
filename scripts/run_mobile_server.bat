
@echo off
echo ========================================================
echo 正在启动聚羧酸研发管理系统 (手机访问模式)
echo ========================================================
echo.
echo 注意: 
echo 1. 请确保您的手机和电脑连接在同一个 Wi-Fi 网络下
echo 2. 如果是第一次运行，Windows 防火墙可能会弹出提示，请务必允许"专用网络"访问
echo.
echo 正在启动服务器...
echo.

streamlit run app/main.py --server.address 0.0.0.0

pause
