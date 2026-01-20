Set WshShell = CreateObject("WScript.Shell")

' 启动后台服务器（隐藏窗口）
WshShell.Run "cmd /c ""C:\Users\徐梓馨\polycarb_project\run_mobile_server_nopause.bat""", 0, False

' 等待几秒，给服务器启动时间（可以根据机器速度调整）
WScript.Sleep 5000

' 打开浏览器访问系统（默认本机 8501 端口）
WshShell.Run "http://localhost:8501"

