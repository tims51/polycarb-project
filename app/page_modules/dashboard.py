"""项目概览页面模块"""

import streamlit as st
from datetime import datetime, timedelta
import time

def render_dashboard(data_manager):
    """渲染项目概览页面"""
    st.header("📊 项目概览")
    
    # 获取数据
    projects = data_manager.get_all_projects()
    experiments = data_manager.get_all_experiments()
    
    # 关键指标卡片
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        active_projects = sum(1 for p in projects if p.get("status") == "进行中")
        st.metric("进行中项目", active_projects)
    with col2:
        completed_projects = sum(1 for p in projects if p.get("status") == "已完成")
        st.metric("已完成项目", completed_projects)
    with col3:
        total_experiments = len(experiments)
        st.metric("总实验数", total_experiments)
    with col4:
        upcoming_exps = sum(1 for e in experiments if e.get("status") == "计划中")
        st.metric("待进行实验", upcoming_exps)
    
    st.divider()
    
    # 新增项目表单
    with st.expander("➕ 新增项目", expanded=False):
        _render_add_project_form(data_manager)
    
    st.divider()
    
    # 编辑和删除项目
    st.subheader("项目管理")
    edit_col, delete_col = st.columns(2)
    
    with edit_col:
        _render_edit_project_section(data_manager, projects)
    
    with delete_col:
        _render_delete_project_section(data_manager, projects)
    
    st.divider()
    
    # 项目详情总览
    st.subheader("📋 项目详情总览")
    _render_project_details(data_manager, projects)

def _render_add_project_form(data_manager):
    """渲染新增项目表单"""
    with st.form("add_project_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            new_name = st.text_input("项目名称*", key="new_project_name")
            new_leader = st.text_input("负责人*", key="new_project_leader")
            new_status = st.selectbox("状态*", ["计划中", "进行中", "已暂停", "已完成"], key="new_project_status")
        with col2:
            new_start = st.date_input("开始日期*", datetime.now(), key="new_project_start")
            new_end = st.date_input("结束日期", datetime.now() + timedelta(days=60), key="new_project_end")
            new_progress = st.slider("进度 (%)", 0, 100, 0, key="new_project_progress")
        
        new_desc = st.text_area("项目描述", key="new_project_desc", height=80)
        
        submitted = st.form_submit_button("添加项目", type="primary")
        if submitted:
            if new_name and new_leader:
                new_project = {
                    "name": new_name,
                    "leader": new_leader,
                    "start_date": new_start,
                    "end_date": new_end,
                    "status": new_status,
                    "progress": new_progress,
                    "description": new_desc
                }
                if data_manager.add_project(new_project):
                    st.success(f"项目 '{new_name}' 添加成功！")
                    st.rerun()
                else:
                    st.error("添加项目失败，请重试")
            else:
                st.error("请填写带*的必填项")

def _render_edit_project_section(data_manager, projects):
    """渲染编辑项目部分"""
    with st.expander("✏️ 编辑项目", expanded=False):
        if projects:
            # 创建项目选择下拉框
            edit_options = {f"{p['id']}: {p['name']}": p['id'] for p in projects}
            selected_edit_key = st.selectbox(
                "选择项目",
                options=list(edit_options.keys()),
                key="edit_project_select_main"
            )
            
            if selected_edit_key:
                selected_edit_id = edit_options[selected_edit_key]
                _render_edit_project_form(data_manager, selected_edit_id, projects)
        else:
            st.info("暂无项目可编辑")

def _render_edit_project_form(data_manager, project_id, projects):
    """渲染编辑项目表单"""
    project_to_edit = data_manager.get_project(project_id)
    
    if project_to_edit:
        with st.form(f"edit_project_form_{project_id}", clear_on_submit=False):
            col_a, col_b = st.columns(2)
            
            with col_a:
                edit_name = st.text_input(
                    "项目名称*",
                    value=project_to_edit.get("name", ""),
                    key=f"name_{project_id}"
                )
                edit_leader = st.text_input(
                    "负责人*",
                    value=project_to_edit.get("leader", ""),
                    key=f"leader_{project_id}"
                )
            
            with col_b:
                current_status = project_to_edit.get("status", "计划中")
                status_options = ["计划中", "进行中", "已暂停", "已完成"]
                status_index = status_options.index(current_status) if current_status in status_options else 0
                
                edit_status = st.selectbox(
                    "状态",
                    options=status_options,
                    index=status_index,
                    key=f"status_{project_id}"
                )
                edit_progress = st.slider(
                    "进度 (%)",
                    0, 100,
                    value=project_to_edit.get("progress", 0),
                    key=f"progress_{project_id}"
                )
            
            # 时间和描述
            col_c, col_d = st.columns(2)
            with col_c:
                start_date_str = project_to_edit.get("start_date", "")
                try:
                    if start_date_str:
                        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                    else:
                        start_date = datetime.now().date()
                except (ValueError, TypeError):
                    start_date = datetime.now().date()
                
                edit_start_date = st.date_input(
                    "开始日期",
                    value=start_date,
                    key=f"start_date_{project_id}"
                )
            
            with col_d:
                end_date_str = project_to_edit.get("end_date", "")
                try:
                    if end_date_str:
                        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                    else:
                        end_date = datetime.now().date() + timedelta(days=60)
                except (ValueError, TypeError):
                    end_date = datetime.now().date() + timedelta(days=60)
                
                edit_end_date = st.date_input(
                    "结束日期",
                    value=end_date,
                    key=f"end_date_{project_id}"
                )
            
            edit_description = st.text_area(
                "项目描述",
                value=project_to_edit.get("description", ""),
                height=80,
                key=f"description_{project_id}"
            )
            
            # 操作按钮
            submit_col1, submit_col2 = st.columns(2)
            with submit_col1:
                submitted = st.form_submit_button(
                    "💾 保存修改",
                    type="primary",
                    use_container_width=True
                )
            
            with submit_col2:
                if st.form_submit_button("🔄 重置", use_container_width=True):
                    st.rerun()
            
            # 处理表单提交
            if submitted:
                if edit_name and edit_leader:
                    updated_fields = {
                        "name": edit_name,
                        "leader": edit_leader,
                        "status": edit_status,
                        "progress": edit_progress,
                        "start_date": edit_start_date.strftime("%Y-%m-%d"),
                        "end_date": edit_end_date.strftime("%Y-%m-%d"),
                        "description": edit_description
                    }
                    
                    if data_manager.update_project(project_id, updated_fields):
                        st.success(f"✅ 项目 '{edit_name}' 更新成功！")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("❌ 更新项目失败，请重试")
                else:
                    st.error("⚠️ 项目名称和负责人为必填项")

def _render_delete_project_section(data_manager, projects):
    """渲染删除项目部分"""
    with st.expander("🗑️ 删除项目", expanded=False):
        if projects:
            project_options = {f"{p['id']}: {p['name']}": p['id'] for p in projects}
            
            selected_delete_key = st.selectbox(
                "选择项目",
                options=list(project_options.keys()),
                key="delete_project_select_main"
            )
            
            if selected_delete_key:
                selected_delete_id = project_options[selected_delete_key]
                project_name = selected_delete_key.split(": ")[1]
                _render_delete_confirmation(data_manager, selected_delete_id, project_name)
        else:
            st.info("暂无项目可删除")

def _render_delete_confirmation(data_manager, project_id, project_name):
    """渲染删除确认界面"""
    delete_state_key = f"delete_confirm_{project_id}"
    if delete_state_key not in st.session_state:
        st.session_state[delete_state_key] = {
            "show_confirm": False,
            "project_name": project_name
        }
    
    st.session_state[delete_state_key]["project_name"] = project_name
    
    # 显示确认界面
    if not st.session_state[delete_state_key]["show_confirm"]:
        if st.button(
            "🗑️ 删除项目", 
            key=f"init_delete_{project_id}",
            use_container_width=True,
            type="secondary"
        ):
            st.session_state[delete_state_key]["show_confirm"] = True
            st.rerun()
    
    # 显示二次确认
    if st.session_state[delete_state_key]["show_confirm"]:
        current_project = st.session_state[delete_state_key]["project_name"]
        
        st.warning(f"⚠️ 确认删除项目: **{current_project}**")
        st.info("此操作不可恢复，删除后相关实验数据也将丢失。")
        
        confirm_col1, confirm_col2 = st.columns(2)
        
        with confirm_col1:
            if st.button(
                "✅ 确认删除", 
                key=f"final_confirm_{project_id}",
                type="primary",
                use_container_width=True
            ):
                with st.spinner(f"正在删除项目 '{current_project}'..."):
                    if data_manager.delete_project(project_id):
                        st.success(f"✅ 项目 '{current_project}' 已成功删除！")
                        
                        if delete_state_key in st.session_state:
                            del st.session_state[delete_state_key]
                        
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"❌ 删除项目 '{current_project}' 失败")
                        st.session_state[delete_state_key]["show_confirm"] = False
        
        with confirm_col2:
            if st.button(
                "❌ 取消", 
                key=f"cancel_delete_{project_id}",
                use_container_width=True
            ):
                st.session_state[delete_state_key]["show_confirm"] = False
                st.info("已取消删除操作")
                time.sleep(0.5)
                st.rerun()

def _render_project_details(data_manager, projects):
    """渲染项目详情"""
    if projects:
        for i, project in enumerate(projects):
            with st.container():
                # 卡片标题行
                status_colors = {
                    "计划中": "🟡",
                    "进行中": "🟢",
                    "已暂停": "🟠",
                    "已完成": "🔵"
                }
                status_emoji = status_colors.get(project.get("status", "计划中"), "⚪")
                
                col_title, col_status = st.columns([3, 1])
                with col_title:
                    st.markdown(f"### {status_emoji} {project.get('name', '未命名项目')}")
                with col_status:
                    st.markdown(f"**{project.get('status', '未知')}**")
                
                # 详细信息
                col_info, col_desc = st.columns([2, 2])
                
                with col_info:
                    _render_project_info_html(project)
                
                with col_desc:
                    _render_project_progress_and_timeline(data_manager, project)
                
                # 卡片分隔线
                if i < len(projects) - 1:
                    st.divider()
    else:
        st.info("暂无项目数据，请点击上方'新增项目'创建第一个项目")

def _render_project_info_html(project):
    """渲染项目信息HTML"""
    st.markdown("""
    <style>
    .project-info-row {
        display: flex;
        justify-content: space-between;
        padding: 6px 0;
        border-bottom: 1px solid #f0f0f0;
        font-size: 0.9em;
    }
    .info-label {
        font-weight: 600;
        color: #666;
    }
    .info-value {
        color: #333;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="project-info-row">
        <span class="info-label">负责人</span>
        <span class="info-value">{project.get('leader', '未指定')}</span>
    </div>
    <div class="project-info-row">
        <span class="info-label">开始时间</span>
        <span class="info-value">{project.get('start_date', '未设置')}</span>
    </div>
    <div class="project-info-row">
        <span class="info-label">结束时间</span>
        <span class="info-value">{project.get('end_date', '未设置')}</span>
    </div>
    <div class="project-info-row">
        <span class="info-label">项目描述</span>
        <span class="info-value">{project.get('description', '暂无描述')[:50]}{'...' if len(project.get('description', '')) > 50 else ''}</span>
    </div>
    """, unsafe_allow_html=True)

def _render_project_progress_and_timeline(data_manager, project):
    """渲染项目进度和时间线"""
    progress_value = project.get("progress", 0)
    
    st.markdown(f"**进度:** {progress_value}%")
    st.progress(progress_value / 100)
    
    timeline_info = data_manager.get_project_timeline(project.get("id"))
    
    if timeline_info and timeline_info.get('is_valid'):
        status = timeline_info.get('status', '未知')
        status_emoji = timeline_info.get('status_emoji', '📅')
        passed_days = timeline_info.get('passed_days', 0)
        total_days = timeline_info.get('total_days', 1)
        
        st.markdown(f"**{status_emoji} {status}**")
        
        timeline_col1, timeline_col2 = st.columns([3, 1])
        with timeline_col1:
            percent = timeline_info.get('percent', 0)
            st.progress(percent / 100)
        with timeline_col2:
            st.caption(f"{passed_days}/{total_days}天")
        
        start_date = timeline_info.get('start_date')
        end_date = timeline_info.get('end_date')
        if start_date and end_date:
            st.caption(f"📅 {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")
        
        if status == "尚未开始":
            st.info(f"项目将于 {start_date.strftime('%Y-%m-%d')} 开始")
        elif status == "已完成":
            st.success("项目已按时完成")
        elif status == "进行中":
            remaining_days = total_days - passed_days
            if remaining_days > 0:
                estimated_completion = timeline_info.get('estimated_completion')
                if estimated_completion:
                    st.info(f"剩余 {remaining_days} 天，预计 {estimated_completion.strftime('%Y-%m-%d')} 完成")
    else:
        st.info("时间线信息不可用")