
"""
Sidebar Component
Handles the main navigation sidebar.
"""

import streamlit as st
from datetime import datetime
from typing import Callable, Dict
from services.data_service import DataService
from components.ui_manager import render_ui_settings, UIManager
from components.access_manager import render_mobile_access_sidebar, render_internet_access_sidebar, check_page_permission

def render_sidebar(data_service: DataService, page_routes: Dict[str, Callable]):
    """
    Render the main sidebar with collapsible groups.
    """
    with st.sidebar:
        st.title("导航菜单")
        
        user = st.session_state.get("user")
        
        # 1. Define Menu Structure
        # Map page names (keys in page_routes) to Groups
        # Note: We rely on exact string matching with main.py keys
        # 注意：这里的名称必须与 src/main.py 中的 PAGE_ROUTES 键名完全一致
        menu_structure = {
            "📊 仪表盘": ["📊 项目概览"],
            "🧪 实验管理": ["📝 数据记录", "🧪 实验管理"],
            "📈 数据洞察": ["📈 数据分析"],
            "🏭 供应链与生产": ["🧱 原材料管理", "📦 成品库存", "🏭 SAP/BOM"],
            "⚙️ 系统设置": ["💾 数据管理"]
        }
        
        # Fallback for pages not in structure
        known_pages = [p for group in menu_structure.values() for p in group]
        others = [p for p in page_routes.keys() if p not in known_pages]
        if others:
            menu_structure["📦 其他功能"] = others
            
        # 2. Render Navigation
        if "selected_page" not in st.session_state:
            st.session_state.selected_page = "📊 项目概览" # Default
            
        # Filter available pages based on permission
        available_pages = [p for p in page_routes.keys() if check_page_permission(user, p)]
        
        # If current selection is invalid, reset
        if st.session_state.selected_page not in available_pages and available_pages:
             st.session_state.selected_page = available_pages[0]
        
        # Render Groups
        for group_name, pages in menu_structure.items():
            # Filter pages in this group
            group_pages = [p for p in pages if p in available_pages]
            
            if not group_pages:
                continue
            
            # Auto-expand if current page is in this group
            is_expanded = st.session_state.selected_page in group_pages
            
            # Special case for Dashboard (no expander needed usually, but for consistency we can use one or just buttons)
            # If group has only 1 item and it's Dashboard, maybe just show button? 
            # But "collapsible groups" was requested.
            
            with st.expander(group_name, expanded=is_expanded):
                for page_name in group_pages:
                    # Use button for navigation
                    # Highlight active page
                    if st.session_state.selected_page == page_name:
                        st.button(f"📍 {page_name}", key=f"nav_{page_name}", type="primary", use_container_width=True, disabled=True)
                    else:
                        if st.button(page_name, key=f"nav_{page_name}", use_container_width=True):
                            st.session_state.selected_page = page_name
                            st.rerun()
                            
        st.markdown("---")
        
        # UI Settings
        render_ui_settings()
        
        # System Info
        st.markdown("### 系统信息")
        st.info(f"当前时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        # Stats
        projects = data_service.get_all_projects()
        experiments = data_service.get_all_experiments()
        # raw_materials = data_service.get_all_raw_materials() # Removed as requested
        
        c1, c2 = st.columns(2)
        with c1:
            st.metric("项目", len(projects))
        with c2:
            st.metric("实验", len(experiments))
        
        # Backup Status
        last_backup = st.session_state.get("last_backup_time")
        if last_backup:
            time_str = last_backup
            if not isinstance(last_backup, str):
                time_str = last_backup.strftime('%Y-%m-%d %H:%M:%S')
            
            with st.expander("💾 备份状态", expanded=False):
                st.markdown(f"<div style='font-size: 0.85em; color: grey;'>{time_str}</div>", unsafe_allow_html=True)
        
        # Access Info
        render_mobile_access_sidebar()
        render_internet_access_sidebar()
        
        return st.session_state.selected_page
