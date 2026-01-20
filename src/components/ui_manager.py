
"""
UI Manager Component
Handles global CSS injection and UI settings.
"""

import streamlit as st
import time
from contextlib import contextmanager
import pandas as pd
from config import (
    PRIMARY_COLOR, 
    BACKGROUND_COLOR, 
    TEXT_COLOR, 
    DEFAULT_FONT_SCALE,
    DEFAULT_MOBILE_MODE
)

class UIManager:
    """
    Unified UI Manager for consistent styling and components.
    """
    
    @staticmethod
    def render_card(title: str, value: str, sub_value: str = None, icon: str = None, color: str = None):
        """
        Render a styled metric card.
        """
        # Determine styling
        border_left = f"4px solid {color}" if color else f"4px solid {PRIMARY_COLOR}"
        
        icon_html = f"<div style='font-size: 1.5rem; margin-right: 0.5rem;'>{icon}</div>" if icon else ""
        sub_html = f"<div style='font-size: 0.8rem; color: #666; margin-top: 0.2rem;'>{sub_value}</div>" if sub_value else ""
        
        html = f"""
        <div style="
            background-color: white;
            padding: 1rem;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            border-left: {border_left};
            margin-bottom: 1rem;
            transition: transform 0.2s;
        " onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform='translateY(0)'">
            <div style="display: flex; align-items: center; margin-bottom: 0.5rem;">
                {icon_html}
                <div style="font-size: 0.9rem; color: #555; font-weight: 600;">{title}</div>
            </div>
            <div style="font-size: 1.5rem; font-weight: 700; color: #333;">{value}</div>
            {sub_html}
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)

    @staticmethod
    def render_status_badge(status: str, size: str = "normal"):
        """
        Render a status badge with consistent coloring.
        """
        color_map = {
            "completed": "#28a745", "已完成": "#28a745", "合格": "#28a745", "released": "#28a745", "finished": "#28a745",
            "in_progress": "#007bff", "进行中": "#007bff", "issued": "#007bff",
            "pending": "#ffc107", "waiting": "#ffc107", "not_started": "#ffc107", "尚未开始": "#ffc107", "待检": "#ffc107", "created": "#ffc107",
            "failed": "#dc3545", "error": "#dc3545", "不合格": "#dc3545", "rejected": "#dc3545", "closed": "#6c757d", "frozen": "#6c757d", "冻结": "#6c757d"
        }
        
        bg_color = color_map.get(str(status).lower(), "#6c757d")
        font_size = "0.75rem" if size == "small" else "0.85rem"
        padding = "0.2rem 0.5rem" if size == "small" else "0.3rem 0.6rem"
        
        html = f"""
        <span style="
            background-color: {bg_color};
            color: white;
            padding: {padding};
            border-radius: 12px;
            font-size: {font_size};
            font-weight: 600;
            display: inline-block;
        ">
            {status}
        </span>
        """
        st.markdown(html, unsafe_allow_html=True)

    @staticmethod
    def render_data_table(df: pd.DataFrame, key_col: str = "id", mobile_cols: list = None, **kwargs):
        """
        Render a data table that adapts to mobile views.
        On Desktop: Uses st.dataframe/data_editor
        On Mobile: Uses a card-based list view
        """
        is_mobile = st.session_state.get('ui_mobile_mode', False)
        
        if is_mobile:
            # Render list view
            st.markdown("---")
            for idx, row in df.iterrows():
                # Primary title
                title = str(row.iloc[0]) # Default to first col
                if mobile_cols and len(mobile_cols) > 0:
                    title = str(row[mobile_cols[0]])
                
                # Secondary info
                details = []
                if mobile_cols and len(mobile_cols) > 1:
                    for col in mobile_cols[1:]:
                        if col in row:
                            details.append(f"**{col}:** {row[col]}")
                else:
                    # Default to first 3 cols
                    cols = df.columns[:3]
                    for col in cols:
                        details.append(f"**{col}:** {row[col]}")
                
                details_str = " | ".join(details)
                
                # Card style
                st.markdown(f"""
                <div style="
                    border: 1px solid #eee;
                    border-radius: 8px;
                    padding: 12px;
                    margin-bottom: 8px;
                    background: white;
                ">
                    <div style="font-weight: bold; font-size: 1.1em; margin-bottom: 4px;">{title}</div>
                    <div style="color: #666; font-size: 0.9em;">{details_str}</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.caption(f"共 {len(df)} 条记录 (移动端视图)")
            
        else:
            # Render standard table
            st.dataframe(df, use_container_width=True, **kwargs)

    @staticmethod
    @contextmanager
    def with_spinner(text: str = "正在处理..."):
        """
        Context manager for showing spinner during operations.
        """
        with st.spinner(text):
            yield

    @staticmethod
    def toast(message: str, type: str = "success", icon: str = None):
        """
        Show a toast notification.
        Type: success, error, warning, info
        """
        icon_map = {
            "success": "✅",
            "error": "❌",
            "warning": "⚠️",
            "info": "ℹ️"
        }
        display_icon = icon or icon_map.get(type, "🔔")
        st.toast(message, icon=display_icon)

def load_global_css(font_scale: float = 1.0, mobile_optimized: bool = True):
    """
    Inject global CSS for styling, responsiveness, and mobile optimization.
    """
    
    # Base font size (px)
    base_size_px = 16 * font_scale
    
    # Mobile optimization CSS
    mobile_css = ""
    if mobile_optimized:
        mobile_css = """
        /* === Mobile Touch Optimization === */
        
        .stButton button, .stDownloadButton button, .stFormSubmitButton button {
            min-height: 48px !important;
            min-width: 48px !important;
            padding-top: 0.5rem !important;
            padding-bottom: 0.5rem !important;
            border-radius: 8px !important;
            margin-bottom: 8px !important;
        }
        
        .stTextInput input, .stSelectbox div[data-baseweb="select"], .stNumberInput input {
            min-height: 48px !important;
            border-radius: 8px !important;
        }
        
        .stCheckbox label, .stRadio label {
            padding-top: 4px !important;
            padding-bottom: 4px !important;
        }
        
        /* === Responsive Layout === */
        @media (max-width: 768px) {
            .stButton button, .stDownloadButton button, .stFormSubmitButton button {
                width: 100% !important;
            }
            
            .block-container {
                padding-top: 3rem !important;
                padding-left: 1rem !important;
                padding-right: 1rem !important;
                padding-bottom: 2rem !important;
            }
            
            h1 { font-size: 1.75rem !important; }
            h2 { font-size: 1.5rem !important; }
            h3 { font-size: 1.25rem !important; }
        }
        """

    css = f"""
    <style>
    :root {{
        /* === Design Tokens === */
        --primary-color: {PRIMARY_COLOR};
        --background-color: {BACKGROUND_COLOR};
        --text-color: {TEXT_COLOR};
        --font-base-size: {base_size_px}px;
    }}
    
    html {{
        font-size: var(--font-base-size);
    }}
    
    /* === Typography === */
    p, .stMarkdown, .stText, .stCode, .stJson {{
        font-size: 1rem !important; 
        line-height: 1.6 !important;
    }}
    
    h1 {{ font-size: 2.2rem !important; font-weight: 700 !important; margin-bottom: 1.5rem !important; }}
    h2 {{ font-size: 1.8rem !important; font-weight: 600 !important; margin-top: 1.5rem !important; margin-bottom: 1rem !important; }}
    h3 {{ font-size: 1.4rem !important; font-weight: 600 !important; }}
    
    .stButton button, .stTextInput input, .stSelectbox div, .stNumberInput input {{
        font-size: 1rem !important;
    }}
    
    .stDataFrame div {{
        font-size: 0.9rem !important;
    }}
    
    [data-testid="stSidebar"] .block-container {{
        padding-top: 2rem;
    }}
    
    /* === Desktop/General Enhancements === */
    
    /* Metric Cards */
    [data-testid="stMetric"] {{
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        border: 1px solid #e9ecef;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }}
    
    [data-testid="stMetric"]:hover {{
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        background-color: #ffffff;
        border-color: var(--primary-color);
    }}
    
    [data-testid="stMetric"] label {{
        color: #666 !important;
        font-size: 0.9rem !important;
    }}
    
    [data-testid="stMetric"] [data-testid="stMetricValue"] {{
        color: var(--primary-color) !important;
        font-weight: 700 !important;
    }}

    /* Tables */
    .stDataFrame {{
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }}

    /* Buttons */
    .stButton button {{
        transition: all 0.2s ease;
        border-width: 1px !important;
    }}
    
    .stButton button:hover {{
        transform: translateY(-1px);
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }}

    /* Expanders */
    .streamlit-expanderHeader {{
        border-radius: 8px !important;
        background-color: #fcfcfc !important;
        border: 1px solid #f0f0f0 !important;
    }}
    
    .streamlit-expanderContent {{
        border: 1px solid #f0f0f0;
        border-top: none;
        border-bottom-left-radius: 8px;
        border-bottom-right-radius: 8px;
        padding: 1rem !important;
    }}

    /* Sidebar */
    [data-testid="stSidebar"] {{
        background-color: #f8f9fa;
        border-right: 1px solid #e0e0e0;
    }}

    {mobile_css}
    </style>
    """
    
    st.markdown(css, unsafe_allow_html=True)

def render_ui_settings():
    """
    Render UI settings in the sidebar.
    Returns:
        tuple: (font_scale, mobile_mode)
    """
    if 'ui_font_scale' not in st.session_state:
        st.session_state['ui_font_scale'] = DEFAULT_FONT_SCALE
    if 'ui_mobile_mode' not in st.session_state:
        st.session_state['ui_mobile_mode'] = DEFAULT_MOBILE_MODE

    with st.sidebar:
        with st.expander("🎨 界面显示设置", expanded=False):
            st.caption("自定义字体大小与布局")
            
            st.markdown("**字体大小**")
            font_mode = st.select_slider(
                "选择字号模式",
                options=["小", "标准", "大", "特大"],
                value="标准",
                label_visibility="collapsed"
            )
            
            scale_map = {
                "小": 0.85,
                "标准": 1.0,
                "大": 1.15,
                "特大": 1.3
            }
            
            use_custom = st.checkbox("启用自定义缩放", value=False)
            
            if use_custom:
                scale = st.slider("缩放比例", 0.7, 1.5, st.session_state['ui_font_scale'], 0.05)
                st.session_state['ui_font_scale'] = scale
            else:
                st.session_state['ui_font_scale'] = scale_map[font_mode]
            
            st.divider()
            
            st.markdown("**移动端适配**")
            mobile_mode = st.toggle("触控增强模式", value=st.session_state['ui_mobile_mode'], help="增大按钮和输入框尺寸")
            st.session_state['ui_mobile_mode'] = mobile_mode
            
            if mobile_mode:
                st.caption("✅ 已启用大尺寸触控目标")
    
    return st.session_state['ui_font_scale'], st.session_state['ui_mobile_mode']
