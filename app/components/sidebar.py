
"""
Sidebar Component
Handles the main navigation sidebar.
"""

import streamlit as st
from datetime import datetime
from typing import Callable, Dict
from services.data_service import DataService
from components.ui_manager import render_ui_settings
from components.access_manager import render_mobile_access_sidebar, render_internet_access_sidebar

def render_sidebar(data_service: DataService, page_routes: Dict[str, Callable]):
    """
    Render the main sidebar.
    
    Args:
        data_service: Instance of DataService.
        page_routes: Dictionary mapping page names to render functions.
        
    Returns:
        The selected page function.
    """
    with st.sidebar:
        st.title("导航菜单")
        
        # Navigation
        menu_options = list(page_routes.keys())
        # Default to the first page if not set
        if "selected_page" not in st.session_state:
            st.session_state.selected_page = menu_options[0]
            
        selected_option = st.radio("选择功能", menu_options, key="sidebar_nav_radio")
        
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
        
        return page_routes[selected_option]
