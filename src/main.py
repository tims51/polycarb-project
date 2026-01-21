"""聚羧酸减水剂研发管理系统 - 主程序 (模块化重构版)"""

import streamlit as st
from datetime import datetime
import time

# 导入服务容器与模型
from core.container import ServiceContainer
from schemas.user import UserLogin, UserCreate

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

# -------------------- 页面配置 --------------------
st.set_page_config(
    page_title="聚羧酸减水剂研发管理系统",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------- UI 全局设置 --------------------
if 'ui_font_scale' not in st.session_state:
    st.session_state['ui_font_scale'] = 1.0
if 'ui_mobile_mode' not in st.session_state:
    st.session_state['ui_mobile_mode'] = True

load_global_css(
    font_scale=st.session_state['ui_font_scale'], 
    mobile_optimized=st.session_state['ui_mobile_mode']
)

def render_report_page():
    """渲染报告生成页面"""
    st.header("📄 报告生成")
    st.info("报告生成页面开发中...")

def render_login_page(auth_service):
    st.markdown(
        """
        <style>
        .login-page-title {
            font-size: 2.4rem;
            font-weight: 600;
            background: linear-gradient(120deg, #36cfc9, #597ef7, #9254de);
            -webkit-background-clip: text;
            color: transparent;
        }
        .login-page-subtitle {
            font-size: 0.95rem;
            color: #8c8c8c;
        }
        .login-accent {
            font-size: 0.8rem;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: #40a9ff;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    
    st.markdown("<div class='login-accent'>Polycarboxylate Superplasticizer R&D Platform</div>", unsafe_allow_html=True)
    st.markdown("<div class='login-page-title'>聚羧酸减水剂研发管理系统</div>", unsafe_allow_html=True)
    st.markdown("<div class='login-page-subtitle'>统一管理配方、实验、数据与库存的数字化实验室平台</div>", unsafe_allow_html=True)
    
    st.markdown("")
    
    col_left, col_right = st.columns([1.2, 1])
    
    with col_left:
        st.metric("版本", "v3.0")
        st.metric("状态", "系统在线")
        st.markdown("---")
        st.markdown("**特性**")
        st.caption("• 实验全流程追踪")
        st.caption("• 数据自动备份与恢复")
        st.caption("• 角色权限与安全控制")
    
    with col_right:
        tabs = st.tabs(["登录", "注册"])
        with tabs[0]:
            username = st.text_input("用户名", key="login_username_main")
            password = st.text_input("密码", type="password", key="login_password_main")
            if st.button("登录", type="primary", use_container_width=True, key="login_btn_main"):
                # 使用 AuthService 进行认证
                ok, user_resp = auth_service.authenticate_user(UserLogin(username=username, password=password))
                if ok:
                    # 转换为字典以兼容现有逻辑
                    st.session_state['user'] = user_resp.model_dump()
                    st.success(f"欢迎，{user_resp.username}")
                    time.sleep(0.3)
                    st.rerun()
                else:
                    st.error("用户名或密码错误")
        with tabs[1]:
            new_username = st.text_input("新用户名（格式：姓名 手机号，如 张三 13800000000）", key="reg_username_main")
            new_password = st.text_input("新密码", type="password", key="reg_password_main")
            new_password2 = st.text_input("确认密码", type="password", key="reg_password2_main")
            if st.button("注册", use_container_width=True, key="reg_btn_main"):
                if not new_username or not new_password:
                    st.error("用户名和密码不能为空")
                elif new_password != new_password2:
                    st.error("两次输入的密码不一致")
                else:
                    # 使用 AuthService 进行注册
                    ok, msg = auth_service.create_user(UserCreate(username=new_username, password=new_password, role="user"))
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)

def main():
    """主函数"""
    # 初始化服务容器
    if 'container' not in st.session_state:
        st.session_state.container = ServiceContainer()
        # 确保默认管理员存在
        st.session_state.container.auth_service.ensure_default_admin()
        
    container = st.session_state.container

    # 初始化服务到 session_state (为了兼容旧代码直接从 session_state 获取)
    if 'services' not in st.session_state:
        st.session_state.services = {}
    st.session_state.services['bom_service'] = container.bom_service
    # 也可以放入其他 service
    st.session_state.services['inventory_service'] = container.inventory_service
    st.session_state.services['auth_service'] = container.auth_service

    # 路由配置 - 注入特定服务
    # 注意：这里的键名必须与 src/components/sidebar.py 中的 menu_structure 完全一致
    PAGE_ROUTES = {
        "📊 项目概览": lambda: render_dashboard(container.data_service),
        "🧪 实验管理": lambda: render_experiment_management(container.data_service),
        "📝 数据记录": lambda: render_data_recording(container.data_service),
        "📈 数据分析": lambda: render_analysis_page(container.data_service),
        "🧱 原材料管理": lambda: render_raw_material_management(container.inventory_service, container.data_service),
        "📦 成品库存": lambda: render_product_inventory_page(container.inventory_service),
        "🏭 SAP/BOM": lambda: render_sap_bom(container.bom_service, container.inventory_service, container.data_service),
        "💾 数据管理": lambda: render_data_management(container.data_service, container.inventory_service, container.auth_service),
        "📄 报告生成": lambda: render_report_page()
    }

    if "user" not in st.session_state:
        st.session_state['user'] = None

    with st.sidebar:
        if st.session_state.get('user'):
            st.markdown(f"当前用户：**{st.session_state['user']['username']}** ({st.session_state['user'].get('role', 'user')})")
            if st.button("退出登录", use_container_width=True):
                st.session_state['user'] = None
                st.rerun()

    if not st.session_state.get('user'):
        render_login_page(container.auth_service)
        return

    # DataService 已经实现了所需接口，直接传递
    selected_page_name = render_sidebar(container.data_service, PAGE_ROUTES)
    
    # 获取对应页面的渲染函数
    selected_page_func = PAGE_ROUTES.get(selected_page_name)
    
    # 渲染选中的页面
    if selected_page_func:
        with st.container():
            selected_page_func()
    else:
        st.error(f"未找到页面: {selected_page_name}")
    
    # 页脚
    st.markdown("---")
    st.caption("聚羧酸减水剂研发管理系统 v3.0 | 模块化重构版 | 最后更新: 2024年1月")

# -------------------- 程序执行 --------------------
if __name__ == "__main__":
    main()
