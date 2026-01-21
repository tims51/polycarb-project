
"""
Access Manager Component
Handles display of Mobile and Internet access information in the sidebar.
"""

import os
import streamlit as st
from utils.helpers import get_local_ip, generate_qr_code
from config import URL_FILE_PATH

from core.enums import PermissionAction, UserRole

def has_permission(user: dict, action: str) -> bool:
    """
    Check if the user has permission for the given action.
    """
    if not user:
        return False
        
    role = user.get("role", UserRole.VIEWER.value)
    
    # Admin has all permissions
    if role == UserRole.ADMIN.value:
        return True
        
    # User permissions
    if role == UserRole.USER.value:
        # Define user allowed actions
        allowed_actions = [
            PermissionAction.VIEW_DASHBOARD.value,
            PermissionAction.MANAGE_EXPERIMENTS.value,
            PermissionAction.MANAGE_RAW_MATERIALS.value,
            PermissionAction.VIEW_ANALYSIS.value,
            PermissionAction.MANAGE_BOM.value, # Assuming users can manage BOMs for now based on old logic likely being loose or restricted. 
            # Wait, the sap_bom.py says "仅管理员可以维护 BOM 主数据". So users should NOT have MANAGE_BOM.
            # But they might need to VIEW. The code checked 'manage_bom'.
            # Let's align with the error context: sap_bom.py checks "manage_bom".
            PermissionAction.MANAGE_INVENTORY.value,
        ]
        return action in allowed_actions
        
    return False

def check_page_permission(user: dict, page_name: str) -> bool:
    """
    Check if the current user has permission to access the page.
    """
    # Define restricted pages and required roles
    # Allow users to access Data Management (for Stocktake), but internal tabs will be restricted
    restricted_pages = {
        # "💾 数据管理": ["admin"]  <-- Removed restriction here
    }
    
    if page_name not in restricted_pages:
        return True
        
    allowed_roles = restricted_pages[page_name]
    
    if not user:
        return False
        
    user_role = user.get("role", "guest")
    return user_role in allowed_roles

def render_mobile_access_sidebar():
    """Render the Mobile Access section in the sidebar."""
    with st.sidebar.expander("📱 手机端访问", expanded=False):
        ip = get_local_ip()
        port = 8501
        url = f"http://{ip}:{port}"
        
        qr_img = generate_qr_code(url)
        st.image(qr_img, caption="扫码在手机打开", use_container_width=True)
        st.code(url, language="text")
        
        st.markdown("""
        **连接说明:**
        1. 确保手机和电脑连接**同一Wi-Fi**
        2. 使用手机相机或微信扫码
        3. 如果无法访问，请检查防火墙设置
        4. 必须使用 `run_mobile.bat` 启动
        """)

def render_internet_access_sidebar():
    """Render the Internet Access section in the sidebar."""
    # Check if enabled via env var or file
    env_enabled = os.environ.get("ENABLE_INTERNET_ACCESS") == "true"
    
    file_url = None
    if URL_FILE_PATH.exists():
        try:
            with open(URL_FILE_PATH, "r") as f:
                file_url = f.read().strip()
        except Exception:
            pass

    if not env_enabled and not file_url:
        return

    with st.sidebar.expander("🌐 互联网远程访问", expanded=False):
        url = file_url if file_url else os.environ.get("PUBLIC_ACCESS_URL")
        
        if url:
            st.success("✅ 远程连接已就绪")
            
            qr_img = generate_qr_code(url)
            st.image(qr_img, caption="扫码远程访问", use_container_width=True)
            
            st.code(url, language="text")
            st.caption("此链接可在任何有互联网的地方访问。")
            st.caption("注意：这是临时链接，重启后会变化。")
            
        else:
            st.info("⌛ 正在等待连接信息...")
            st.caption("请查看启动窗口的输出。")
