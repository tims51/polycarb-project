"""聚羧酸减水剂研发管理系统 - 主程序 (模块化重构版)"""

import streamlit as st
from datetime import datetime
import time

# 导入核心模块
from core.data_manager import DataManager

# 导入页面模块
from page_modules.dashboard import render_dashboard
from page_modules.experiment_management import render_experiment_management
from page_modules.raw_material_management import render_raw_material_management
from page_modules.data_recording import render_data_recording
from page_modules.data_management import render_data_management
from page_modules.data_analysis import render_analysis_page
from page_modules.sap_bom import render_sap_bom
from page_modules.product_inventory import render_product_inventory_page
from utils.mobile_helper import render_mobile_connect_sidebar
from utils.internet_helper import render_internet_access_sidebar
from utils.ui_manager import render_ui_settings, load_global_css

from components.sidebar import render_sidebar

# -------------------- 初始化数据管理器 --------------------
# Force reload trigger
data_manager = DataManager()

# -------------------- 页面配置 --------------------
st.set_page_config(
    page_title="聚羧酸减水剂研发管理系统",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------- UI 全局设置 --------------------
# 在页面最顶端加载 CSS，确保样式生效
# 注意：render_ui_settings 需要在侧边栏中渲染，这里先获取 session_state 的默认值
if 'ui_font_scale' not in st.session_state:
    st.session_state['ui_font_scale'] = 1.0
if 'ui_mobile_mode' not in st.session_state:
    st.session_state['ui_mobile_mode'] = True

load_global_css(
    font_scale=st.session_state['ui_font_scale'], 
    mobile_optimized=st.session_state['ui_mobile_mode']
)

# -------------------- 页面路由 --------------------
PAGE_ROUTES = {
    "📊 项目概览": lambda: render_dashboard(data_manager),
    "🧪 实验管理": lambda: render_experiment_management(data_manager),
    "🏭 SAP/BOM": lambda: render_sap_bom(data_manager),
    "📦 成品库存": lambda: render_product_inventory_page(data_manager),
    " 原材料管理": lambda: render_raw_material_management(data_manager),
    "📝 数据记录": lambda: render_data_recording(data_manager),
    "💾 数据管理": lambda: render_data_management(data_manager),
    "📈 数据分析": lambda: render_analysis_page(data_manager),
    "📄 报告生成": lambda: render_report_page()
}

def render_report_page():
    """渲染报告生成页面"""
    st.header("📄 报告生成")
    st.info("报告生成页面开发中...")

def main():
    """主函数"""
    # 页面标题 (仅在非侧边栏模式下显示，这里可选)
    # st.title("🧪 聚羧酸减水剂研发管理系统") 
    
    # 渲染侧边栏并获取选择
    # 注意：components/sidebar.py 中的 render_sidebar 已经包含了大部分逻辑
    # 我们需要传递 data_manager 和 PAGE_ROUTES
    
    # 传递给 sidebar 的数据服务 wrapper (简单封装以匹配接口)
    class DataServiceWrapper:
        def get_all_projects(self): return data_manager.get_all_projects()
        def get_all_experiments(self): return data_manager.get_all_experiments()
        def get_all_raw_materials(self): return data_manager.get_all_raw_materials()
    
    data_service = DataServiceWrapper()
    
    # 调用新的 sidebar 组件
    selected_page_func = render_sidebar(data_service, PAGE_ROUTES)
    
    # 渲染选中的页面
    if selected_page_func:
        # 使用容器来渲染页面内容，避免侧边栏重叠
        with st.container():
            selected_page_func()
    
    # 页脚
    st.markdown("---")
    st.caption("聚羧酸减水剂研发管理系统 v3.0 | 模块化重构版 | 最后更新: 2024年1月")

# -------------------- 程序执行 --------------------
if __name__ == "__main__":
    main()
