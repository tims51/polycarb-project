
import os
import subprocess
import sys
import time
import threading
import re
import webbrowser
import urllib.request
import shutil

# 定义存储公共 URL 的临时文件路径
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
URL_FILE = os.path.join(ROOT_DIR, ".public_url")
CLOUDFLARED_PATH = os.path.join(ROOT_DIR, "cloudflared.exe")

def cleanup_url_file():
    """清理 URL 文件"""
    if os.path.exists(URL_FILE):
        try:
            os.remove(URL_FILE)
        except:
            pass

def download_cloudflared():
    """
    下载 Cloudflared (如果不存在)
    """
    if os.path.exists(CLOUDFLARED_PATH):
        return True
        
    print("正在初始化网络组件 (Cloudflared)...")
    print("首次运行需要下载必要组件 (约 15MB)，请稍候...")
    
    # 尝试下载 32 位版本 (兼容性更好)
    url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-386.exe"
    try:
        # 使用 urllib 下载，伪装 User-Agent
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        )
        with urllib.request.urlopen(req) as response, open(CLOUDFLARED_PATH, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
            
        print("组件下载完成，正在验证...")
        
        # 验证文件是否可执行
        try:
            subprocess.run([CLOUDFLARED_PATH, "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print("组件验证通过！")
            return True
        except Exception as e:
            print(f"❌ 组件验证失败: {e}")
            print("下载的文件可能已损坏或不兼容。")
            if os.path.exists(CLOUDFLARED_PATH):
                os.remove(CLOUDFLARED_PATH)
            return False
            
    except Exception as e:
        print(f"\n❌ 组件下载失败: {e}")
        print("请检查网络连接。")
        return False

def read_stream(stream, callback):
    """读取流并回调"""
    while True:
        line = stream.readline()
        if not line:
            break
        callback(line)

def start_cloudflared_tunnel():
    """
    启动 Cloudflared Quick Tunnel
    """
    if not download_cloudflared():
        return None, None
        
    print("正在连接 Cloudflare 全球加速网络...")
    
    # 启动 cloudflared
    cmd = [CLOUDFLARED_PATH, "tunnel", "--url", "http://localhost:8501"]
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    )
    
    url_found_event = threading.Event()
    found_url = [None]
    
    def output_handler(line):
        # Cloudflared 输出通常在 stderr，但我们合并了流
        # print(f"[Cloudflare] {line.strip()}") # 调试用
        
        # 查找 trycloudflare.com URL
        if ".trycloudflare.com" in line:
            match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
            if match:
                url = match.group(0)
                if not found_url[0]:
                    found_url[0] = url
                    url_found_event.set()
                    
                    # 写入文件供 Streamlit 读取
                    try:
                        with open(URL_FILE, "w") as f:
                            f.write(url)
                    except Exception as e:
                        print(f"写入 URL 文件失败: {e}")

    # 启动后台线程读取输出
    t = threading.Thread(target=read_stream, args=(process.stdout, output_handler), daemon=True)
    t.start()
    
    # 等待 URL 生成 (Cloudflared 可能需要一点时间)
    print("等待分配全球加速地址...")
    if url_found_event.wait(timeout=30):
        return process, found_url[0]
    else:
        process.terminate()
        return None, None

def open_browser_delayed(url):
    """延迟打开浏览器"""
    time.sleep(3)
    try:
        webbrowser.open(url)
    except:
        pass

def main():
    print("========================================================")
    print("      聚羧酸研发管理系统 - 互联网极速访问模式      ")
    print("========================================================")
    print("🚀 正在切换至 Cloudflare 全球加速线路...")
    print("无需账号，无需配置，穿透力更强。")
    print("")
    
    # 清理旧文件
    cleanup_url_file()
    
    # 启动隧道
    tunnel_process, public_url = start_cloudflared_tunnel()
    
    if public_url:
        print(f"\n✅ 连接成功！")
        print(f"🌍 公网访问地址: {public_url}")
        print("--------------------------------------------------------")
        
        # 设置环境变量
        os.environ["ENABLE_INTERNET_ACCESS"] = "true"
        os.environ["PUBLIC_ACCESS_URL"] = public_url
        
        print("\n正在启动系统界面...")
        print("提示：如果浏览器提示 0.0.0.0 无法访问，请使用 http://127.0.0.1:8501")
        
        # 自动打开正确的本地地址
        threading.Thread(target=open_browser_delayed, args=("http://127.0.0.1:8501",), daemon=True).start()
        
        # 启动 Streamlit
        cmd = [sys.executable, "-m", "streamlit", "run", "app/main.py", "--server.address", "0.0.0.0", "--server.headless", "true"]
        
        try:
            # 运行 Streamlit (阻塞)
            subprocess.run(cmd)
        except KeyboardInterrupt:
            print("\n正在关闭...")
        finally:
            # 清理
            cleanup_url_file()
            if tunnel_process:
                tunnel_process.terminate()
                
    else:
        print("\n❌ 连接 Cloudflare 失败。")
        print("可能的原因：")
        print("1. 网络连接不稳定")
        print("2. Cloudflared 组件下载失败")
        print("\n建议：")
        print("- 请确保您的电脑可以访问互联网")
        print("- 检查是否有杀毒软件拦截了 cloudflared.exe")
        input("\n按回车键退出...")

if __name__ == "__main__":
    main()
