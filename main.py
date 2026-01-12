"""
Polycarboxylate Superplasticizer R&D Management System
Main Entry Point
Refactored for modular architecture and scalability.
"""

import streamlit as st
import logging
import sys
from pathlib import Path

# Add project root to path
root_dir = Path(__file__).parent.absolute()
sys.path.append(str(root_dir))

# Import modular components
from app.config import APP_NAME, VERSION, PAGE_CONFIG
from app.services.data_service import DataService
from app.components.sidebar import render_sidebar
from app.components.ui_manager import UIManager
from app.ui.pages.dashboard import render_dashboard
from app.ui.pages.experiments import render_experiments
from app.ui.pages.data_entry import render_data_entry
from app.ui.pages.analysis import render_analysis
from app.ui.pages.reports import render_reports
from app.utils.logger import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

def main():
    # 1. Page Configuration
    st.set_page_config(**PAGE_CONFIG)
    
    # 2. UI Initialization (CSS, Theme)
    ui_manager = UIManager()
    ui_manager.load_global_css()
    
    # 3. Service Initialization
    # Use session state to persist service instances if needed, 
    # though DataService is lightweight enough to re-init.
    if "data_service" not in st.session_state:
        st.session_state.data_service = DataService()
    
    data_service = st.session_state.data_service
    
    # 4. Routing & Navigation
    # Define available pages
    page_routes = {
        "dashboard": render_dashboard,
        "experiments": render_experiments,
        "data_entry": render_data_entry,
        "analysis": render_analysis,
        "reports": render_reports
    }
    
    # Render Sidebar and get current page selection
    # The sidebar component handles the navigation UI and returns the selected page key
    selected_page = render_sidebar(data_service, page_routes)
    
    # 5. Render Main Content
    try:
        if selected_page in page_routes:
            page_routes[selected_page](data_service)
        else:
            st.error(f"Page '{selected_page}' not found.")
            render_dashboard(data_service)
    except Exception as e:
        logger.error(f"Error rendering page {selected_page}: {e}", exc_info=True)
        st.error(f"An unexpected error occurred: {e}")
        with st.expander("Error Details"):
            st.exception(e)

if __name__ == "__main__":
    main()
