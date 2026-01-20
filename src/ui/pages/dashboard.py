"""
Dashboard Page
Renders the project overview dashboard.
"""

import streamlit as st
import time
from datetime import datetime, timedelta
from services.data_service import DataService
from services.timeline_service import TimelineService

def render_dashboard(data_service: DataService):
    """Render the project overview dashboard."""
    # Initialize session state for UI toggles
    if "show_add_project_form" not in st.session_state:
        st.session_state.show_add_project_form = False
        
    st.header("📊 项目概览")
    
    # Get data
    projects = data_service.get_all_projects()
    experiments = data_service.get_all_experiments()
    
    # Alerts
    _render_strength_alerts(data_service)
    
    # 1. Metrics Area (Compact)
    _render_metrics(projects, experiments)
    
    st.divider()
    
    # 2. Project Management Section
    _render_project_management(data_service, projects)

def _render_metrics(projects, experiments):
    """Render key metrics in a compact layout."""
    with st.container():
        col1, col2, col3, col4 = st.columns(4)
        
        # Calculate metrics
        active_count = sum(1 for p in projects if p.get("status") == "进行中")
        completed_count = sum(1 for p in projects if p.get("status") == "已完成")
        total_exp = len(experiments)
        upcoming_exp = sum(1 for e in experiments if e.get("status") == "计划中")
        
        col1.metric("🔥 进行中项目", active_count, delta_color="normal")
        col2.metric("✅ 已完成项目", completed_count, delta_color="off")
        col3.metric("🧪 总实验数", total_exp)
        col4.metric("📅 待进行实验", upcoming_exp)

def _render_strength_alerts(data_service):
    """Render alerts for pending strength tests."""
    alerts = []
    today = datetime.now().date()
    
    def parse_age(age_str):
        if not age_str: return 0
        if age_str.endswith('d'): return int(age_str[:-1])
        if age_str.endswith('y'): return int(age_str[:-1]) * 365
        return 0

    # Check Mortar Experiments
    mortar_exps = data_service.get_all_mortar_experiments()
    for exp in mortar_exps:
        test_date_str = exp.get("test_date")
        if not test_date_str: continue
        try:
            test_date = datetime.strptime(test_date_str, "%Y-%m-%d").date()
        except: continue
        
        perf = exp.get("performance", {})
        strengths = perf.get("compressive_strengths", {})
        
        # Fallback for old data
        if not strengths:
            # Assume 7d and 28d are required if missing
            if float(perf.get("strength_7d", 0)) == 0: strengths["7d"] = 0
            if float(perf.get("strength_28d", 0)) == 0: strengths["28d"] = 0
            
        for age, val in strengths.items():
            if float(val) > 0: continue
            
            days = parse_age(age)
            if days == 0: continue
            
            due_date = test_date + timedelta(days=days)
            if today >= due_date:
                alerts.append({
                    "type": "砂浆",
                    "id": exp.get("id"),
                    "formula": exp.get("formula_name"),
                    "age": age,
                    "due_date": due_date,
                    "days_overdue": (today - due_date).days
                })

    # Check Concrete Experiments
    concrete_exps = data_service.get_all_concrete_experiments()
    for exp in concrete_exps:
        test_date_str = exp.get("test_date")
        if not test_date_str: continue
        try:
            test_date = datetime.strptime(test_date_str, "%Y-%m-%d").date()
        except: continue
        
        perf = exp.get("performance", {})
        strengths = perf.get("compressive_strengths", {})
        
        # Fallback for old data
        if not strengths:
            if float(perf.get("strength_7d_mpa", 0)) == 0: strengths["7d"] = 0
            if float(perf.get("strength_28d_mpa", 0)) == 0: strengths["28d"] = 0
            
        for age, val in strengths.items():
            if float(val) > 0: continue
            
            days = parse_age(age)
            if days == 0: continue
            
            due_date = test_date + timedelta(days=days)
            if today >= due_date:
                alerts.append({
                    "type": "混凝土",
                    "id": exp.get("id"),
                    "formula": exp.get("formula_name"),
                    "age": age,
                    "due_date": due_date,
                    "days_overdue": (today - due_date).days
                })
    
    if alerts:
        st.warning(f"🔔 发现 {len(alerts)} 个待测强度指标已到期")
        with st.expander("查看详细列表", expanded=False):
            for alert in alerts:
                due_str = alert["due_date"].strftime("%Y-%m-%d")
                overdue = alert["days_overdue"]
                msg = f"**[{alert['type']}]** 配方: {alert['formula']} (ID: {alert['id']}) - **{alert['age']}** 强度 (应测: {due_str})"
                if overdue > 0:
                    st.error(f"{msg} - 已逾期 {overdue} 天")
                else:
                    st.warning(f"{msg} - 今天到期")

def _render_project_management(data_service, projects):
    """Render project management section including list and actions."""
    
    st.subheader("📋 项目管理中心")
    
    # --- Management Tabs: Add, Edit, Delete ---
    mgmt_tab1, mgmt_tab2, mgmt_tab3 = st.tabs(["➕ 新建项目", "✏️ 编辑项目", "🗑️ 删除项目"])
    
    # 1. Add Project
    with mgmt_tab1:
        with st.form("add_project_form_central", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                new_name = st.text_input("项目名称*", key="central_new_name")
                new_leader = st.text_input("负责人*", key="central_new_leader")
                new_status = st.selectbox("状态*", ["计划中", "进行中", "已暂停", "已完成"], key="central_new_status")
            with col2:
                new_start = st.date_input("开始日期*", datetime.now(), key="central_new_start")
                new_end = st.date_input("结束日期", datetime.now() + timedelta(days=60), key="central_new_end")
                new_progress = st.slider("进度 (%)", 0, 100, 0, key="central_new_progress")
            
            new_desc = st.text_area("项目描述", height=80, key="central_new_desc")
            
            submitted = st.form_submit_button("确认创建", type="primary", use_container_width=True)
            if submitted:
                if new_name and new_leader:
                    new_project = {
                        "name": new_name,
                        "leader": new_leader,
                        "start_date": new_start.strftime("%Y-%m-%d"),
                        "end_date": new_end.strftime("%Y-%m-%d"),
                        "status": new_status,
                        "progress": new_progress,
                        "description": new_desc
                    }
                    if data_service.add_project(new_project):
                        st.success(f"项目 '{new_name}' 创建成功！")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("创建失败")
                else:
                    st.error("请填写必填项")

    # 2. Edit Project
    with mgmt_tab2:
        if projects:
            project_options = {f"{p['id']}: {p['name']}": p for p in projects}
            selected_p_key = st.selectbox("选择要编辑的项目", options=list(project_options.keys()), key="mgmt_edit_select")
            
            if selected_p_key:
                project = project_options[selected_p_key]
                p_id = project['id']
                
                with st.form(key=f"mgmt_edit_form_{p_id}"):
                    c1, c2 = st.columns(2)
                    e_name = c1.text_input("名称", value=project.get('name', ''), key=f"mgmt_e_name_{p_id}")
                    e_leader = c2.text_input("负责人", value=project.get('leader', ''), key=f"mgmt_e_leader_{p_id}")
                    
                    c3, c4 = st.columns(2)
                    current_status = project.get('status', '计划中')
                    status_options = ["计划中", "进行中", "已暂停", "已完成"]
                    try: status_idx = status_options.index(current_status)
                    except: status_idx = 0
                    
                    e_status = c3.selectbox("状态", status_options, index=status_idx, key=f"mgmt_e_status_{p_id}")
                    e_progress = c4.slider("进度", 0, 100, project.get('progress', 0), key=f"mgmt_e_progress_{p_id}")
                    
                    c5, c6 = st.columns(2)
                    def safe_date(d_str):
                        try: return datetime.strptime(str(d_str), "%Y-%m-%d").date()
                        except: return datetime.now().date()
                    
                    e_start = c5.date_input("开始", value=safe_date(project.get('start_date')), key=f"mgmt_e_start_{p_id}")
                    e_end = c6.date_input("结束", value=safe_date(project.get('end_date')), key=f"mgmt_e_end_{p_id}")
                    
                    e_desc = st.text_area("描述", value=project.get('description', ''), height=60, key=f"mgmt_e_desc_{p_id}")
                    
                    if st.form_submit_button("保存更改", type="primary", use_container_width=True):
                        updates = {
                            "name": e_name, 
                            "leader": e_leader, 
                            "status": e_status, 
                            "progress": e_progress, 
                            "description": e_desc,
                            "start_date": e_start.strftime("%Y-%m-%d"),
                            "end_date": e_end.strftime("%Y-%m-%d")
                        }
                        if data_service.update_project(p_id, updates):
                            st.success("更新成功")
                            time.sleep(0.5)
                            st.rerun()
        else:
            st.info("暂无项目")

    # 3. Delete Project
    with mgmt_tab3:
        if projects:
            project_options_del = {f"{p['id']}: {p['name']}": p['id'] for p in projects}
            selected_del_key = st.selectbox("选择要删除的项目", options=list(project_options_del.keys()), key="mgmt_del_select")
            
            if selected_del_key:
                del_id = project_options_del[selected_del_key]
                st.warning(f"⚠️ 即将删除: **{selected_del_key}**")
                st.info("此操作不可恢复，所有关联数据将被永久删除。")
                
                if st.button("🚨 确认删除", type="primary", key="mgmt_confirm_del"):
                    if data_service.delete_project(del_id):
                        st.success("删除成功")
                        time.sleep(1)
                        st.rerun()
        else:
            st.info("暂无项目")

    st.divider()
    
    # --- Project List Display ---
    st.subheader("📑 项目列表")
    
    # Filter
    status_filter = st.multiselect(
        "状态筛选",
        options=["计划中", "进行中", "已暂停", "已完成"],
        default=["进行中", "计划中"],
        placeholder="筛选项目状态...",
        label_visibility="collapsed",
        key="dashboard_status_filter"
    )
    
    filtered_projects = [p for p in projects if p.get("status") in status_filter] if status_filter else projects
    
    if not filtered_projects:
        st.info("没有找到符合条件的项目。")
        return

    for project in filtered_projects:
        _render_project_card(project, data_service)

def _render_project_card(project, data_service):
    """Render a single project card with tabs."""
    p_id = project['id']
    status_colors = {"计划中": "🟡", "进行中": "🟢", "已暂停": "🟠", "已完成": "🔵"}
    status_emoji = status_colors.get(project.get("status"), "⚪")
    
    # Custom CSS-like formatting for title using Markdown
    card_title = f"{status_emoji} **{project.get('name')}** (ID: {p_id}) | 负责人: {project.get('leader')}"
    
    with st.expander(card_title, expanded=False):
        tab1, tab2 = st.tabs(["📊 概览", "ℹ️ 详细信息"])
        
        # Tab 1: Overview
        with tab1:
            st.markdown(f"**项目描述**: {project.get('description') or '无'}")
            
            # Timeline
            timeline = TimelineService.calculate_timeline(project)
            if timeline['is_valid']:
                st.progress(timeline['percent'] / 100)
                st.caption(f"⏱️ {TimelineService.get_timeline_summary(timeline)}")
            else:
                st.warning("时间线信息无效")
        
        # Tab 2: Details
        with tab2:
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                st.markdown(f"**开始日期**: {project.get('start_date')}")
                st.markdown(f"**结束日期**: {project.get('end_date')}")
            with col_d2:
                st.markdown(f"**当前状态**: {project.get('status')}")
                st.markdown(f"**进度**: {project.get('progress')}%")
