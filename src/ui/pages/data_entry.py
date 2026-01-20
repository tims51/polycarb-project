
"""
Data Entry Page
Handles data recording for Synthesis, Paste, Mortar, and Concrete experiments.
Redirects to the full-featured data_recording module.
"""

import streamlit as st
import sys
from pathlib import Path

# Ensure app directory is in sys.path to allow imports from page_modules and core
# app/ui/pages/data_entry.py -> app/ui/pages -> app/ui -> app
app_dir = Path(__file__).parent.parent.parent
if str(app_dir) not in sys.path:
    sys.path.append(str(app_dir))

from services.data_service import DataService
from core.data_manager import DataManager
from page_modules.data_recording import render_data_recording

def render_data_entry(data_service: DataService):
    """
    Render the data entry page.
    Now redirects to the comprehensive render_data_recording function from page_modules.
    """
    # Instantiate DataManager which is used by the new module
    # We create a new instance to ensure fresh data, or we could store it in session state
    if "data_manager" not in st.session_state:
        st.session_state.data_manager = DataManager()
    
    # Call the full-featured render function
    render_data_recording(st.session_state.data_manager)
