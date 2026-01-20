
import os
import sys
import streamlit as st
from utils.mobile_helper import generate_qr_code

def render_internet_access_sidebar():
    """
    渲染互联网访问侧边栏
    """
    # 1. 尝试从环境变量获取
    env_enabled = os.environ.get("ENABLE_INTERNET_ACCESS") == "true"
    
    # 2. 尝试从根目录文件获取 (作为后备方案)
    # 定位到项目根目录: app/utils/../../.public_url
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    url_file_path = os.path.join(root_dir, ".public_url")
    
    file_url = None
    if os.path.exists(url_file_path):
        try:
            with open(url_file_path, "r") as f:
                file_url = f.read().strip()
        except:
            pass

    # 如果既没有环境变量启用，也没有 URL 文件，则不显示侧边栏
    if not env_enabled and not file_url:
        return

    with st.sidebar:
        st.markdown("---")
        st.subheader("🌐 互联网远程访问")
        
        # 优先使用文件中的 URL (最新)，其次是环境变量
        url = file_url if file_url else os.environ.get("PUBLIC_ACCESS_URL")
        
        if url:
            st.success("✅ 远程连接已就绪")
            
            # 二维码
            qr_img = generate_qr_code(url)
            st.image(qr_img, caption="扫码远程访问", use_container_width=True)
            
            st.code(url, language="text")
            st.caption("此链接可在任何有互联网的地方访问。")
            st.caption("注意：这是临时链接，重启后会变化。")
            
        else:
            st.info("⌛ 正在等待连接信息...")
            st.caption("请查看启动窗口的输出。")
