
import subprocess
import time
import re
import os
import sys
import threading
import signal
from pathlib import Path

# Add src to python path to import config
sys.path.append(str(Path(__file__).parent.parent / "src"))
try:
    from config import URL_FILE_PATH
except ImportError:
    URL_FILE_PATH = "public_url.txt"

def start_streamlit():
    """Start Streamlit server in the background."""
    print("🚀 Starting Streamlit server...")
    # Use Popen to run in background
    process = subprocess.Popen(
        ["streamlit", "run", "src/main.py", "--server.headless", "true"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=Path(__file__).parent.parent # Run from project root
    )
    return process

def start_cloudflared():
    """Start Cloudflare Tunnel."""
    print("🌐 Starting Cloudflare Tunnel...")
    # cloudflared tunnel --url http://localhost:8501
    try:
        process = subprocess.Popen(
            ["cloudflared", "tunnel", "--url", "http://localhost:8501"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return process
    except FileNotFoundError:
        print("❌ Error: 'cloudflared' not found. Please install Cloudflare Tunnel.")
        print("Download: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/")
        sys.exit(1)

def extract_url_from_logs(process, stop_event):
    """Monitor Cloudflare logs to extract the public URL."""
    url_pattern = r"https://[a-zA-Z0-9-]+\.trycloudflare\.com"
    
    print("⏳ Waiting for public URL...")
    
    # Cloudflared outputs to stderr usually
    while not stop_event.is_set():
        line = process.stderr.readline()
        if not line and process.poll() is not None:
            break
            
        if line:
            # print(f"DEBUG: {line.strip()}") # Uncomment for debugging
            match = re.search(url_pattern, line)
            if match:
                public_url = match.group(0)
                print(f"\n✅ Public URL generated: {public_url}")
                print(f"📋 Share this URL with your team to access the app.")
                
                # Save to file
                try:
                    with open(URL_FILE_PATH, "w") as f:
                        f.write(public_url)
                    print(f"💾 URL saved to {URL_FILE_PATH}")
                except Exception as e:
                    print(f"⚠️ Failed to save URL to file: {e}")
                
                # Keep monitoring for stability, but we found the URL
                # return public_url 
                # Don't return, keep reading to prevent buffer fill
                
def monitor_tunnel(tunnel_process, stop_event):
    """Monitor tunnel process health and restart if needed."""
    while not stop_event.is_set():
        if tunnel_process.poll() is not None:
            print("\n⚠️ Cloudflare Tunnel process died! Restarting...")
            tunnel_process = start_cloudflared()
            # Start a new log reader for the new process
            t = threading.Thread(target=extract_url_from_logs, args=(tunnel_process, stop_event))
            t.daemon = True
            t.start()
        time.sleep(5)

def main():
    stop_event = threading.Event()
    
    # 1. Start Streamlit
    streamlit_process = start_streamlit()
    
    # Wait a bit for Streamlit to initialize
    time.sleep(2)
    
    # 2. Start Cloudflare Tunnel
    tunnel_process = start_cloudflared()
    
    # 3. Start Log Monitor Thread
    log_thread = threading.Thread(target=extract_url_from_logs, args=(tunnel_process, stop_event))
    log_thread.daemon = True
    log_thread.start()
    
    # 4. Start Health Monitor Thread
    monitor_thread = threading.Thread(target=monitor_tunnel, args=(tunnel_process, stop_event))
    monitor_thread.daemon = True
    monitor_thread.start()
    
    print("\n⌨️  Press Ctrl+C to stop the server.")
    
    try:
        # Keep main thread alive
        while True:
            # Check if Streamlit is still running
            if streamlit_process.poll() is not None:
                print("\n⚠️ Streamlit server crashed! Restarting...")
                streamlit_process = start_streamlit()
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping servers...")
        stop_event.set()
        
        # Cleanup
        streamlit_process.terminate()
        tunnel_process.terminate()
        
        # Clean up URL file
        if os.path.exists(URL_FILE_PATH):
            os.remove(URL_FILE_PATH)
            print("🧹 Cleaned up URL file.")
            
        print("👋 Goodbye!")
        sys.exit(0)

if __name__ == "__main__":
    main()
