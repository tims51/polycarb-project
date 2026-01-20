
"""
Experiments Page
Renders the experiment management interface.
"""

import streamlit as st
import time
from datetime import datetime, timedelta
import uuid
from services.data_service import DataService

def render_experiments(data_service: DataService):
    """Render the experiment management page."""
    st.header("🧪 实验管理")

    # Initialize session state
    if "selected_experiments" not in st.session_state:
        st.session_state.selected_experiments = {}
    if "editing_experiment_id" not in st.session_state:
        st.session_state.editing_experiment_id = None
    if "show_edit_form" not in st.session_state:
        st.session_state.show_edit_form = False
    if "experiment_page" not in st.session_state:
        st.session_state.experiment_page = 1

    # Fetch data
    experiments = data_service.get_all_experiments()
    projects = data_service.get_all_projects()
    experiment_types = ["合成实验", "净浆实验", "砂浆实验", "混凝土实验", "性能测试", "配方优化", "稳定性测试"]

    # --- Create New Experiment ---
    with st.expander("➕ 创建新实验", expanded=True):
        with st.form("create_experiment_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                exp_name = st.text_input("实验名称*")
                exp_type = st.selectbox("实验类型*", experiment_types)
                
                project_options = {p["name"]: p["id"] for p in projects}
                project_id = None
                if project_options:
                    selected_project_name = st.selectbox("所属项目*", options=list(project_options.keys()))
                    project_id = project_options.get(selected_project_name)
                else:
                    st.warning("请先创建项目！")
            
            with col2:
                planned_date = st.date_input("计划日期*", datetime.now())
                priority = st.select_slider("优先级", options=["低", "中", "高"], value="中")
                exp_status = st.selectbox("状态", ["计划中", "进行中", "已完成", "已取消"])
            
            description = st.text_area("实验描述")
            
            if st.form_submit_button("创建实验", type="primary"):
                if exp_name and project_id:
                    new_experiment = {
                        "name": exp_name,
                        "type": exp_type,
                        "project_id": project_id,
                        "created_date": datetime.now().strftime("%Y-%m-%d"),
                        "planned_date": planned_date.strftime("%Y-%m-%d"),
                        "actual_date": planned_date.strftime("%Y-%m-%d") if exp_status == "已完成" else None,
                        "priority": priority,
                        "status": exp_status,
                        "description": description
                    }
                    if data_service.add_experiment(new_experiment):
                        st.success(f"实验 '{exp_name}' 创建成功！")
                        st.rerun()
                    else:
                        st.error("创建实验失败，请重试")
                else:
                    st.error("请填写必填项")

    st.divider()

    # --- Experiment List & Filters ---
    st.subheader("📋 实验列表")

    # Filters
    col_f1, col_f2, col_f3, col_f4 = st.columns([2, 1.5, 1.5, 2])
    with col_f1:
        search_term = st.text_input("🔍 搜索", placeholder="名称/类型/ID").lower()
    with col_f2:
        type_filter = st.selectbox("类型", ["全部"] + experiment_types)
    with col_f3:
        status_filter = st.selectbox("状态", ["全部", "计划中", "进行中", "已完成", "已取消"])
    with col_f4:
        page_size = st.selectbox("每页显示", [10, 20, 50], index=1)

    # Filter Logic
    filtered_exps = experiments
    if search_term:
        filtered_exps = [e for e in filtered_exps if search_term in str(e).lower()]
    if type_filter != "全部":
        filtered_exps = [e for e in filtered_exps if e.get("type") == type_filter]
    if status_filter != "全部":
        filtered_exps = [e for e in filtered_exps if e.get("status") == status_filter]

    # Pagination
    total_items = len(filtered_exps)
    total_pages = max(1, (total_items + page_size - 1) // page_size)
    current_page = max(1, min(st.session_state.experiment_page, total_pages))
    st.session_state.experiment_page = current_page
    
    start_idx = (current_page - 1) * page_size
    end_idx = min(start_idx + page_size, total_items)
    page_exps = filtered_exps[start_idx:end_idx]

    # Batch Actions
    col_b1, col_b2, col_b3 = st.columns([1, 1, 4])
    selected_ids = [eid for eid, selected in st.session_state.selected_experiments.items() if selected]
    
    with col_b1:
        if st.button("✏️ 编辑选中", disabled=len(selected_ids) != 1):
            st.session_state.editing_experiment_id = selected_ids[0]
            st.session_state.show_edit_form = True
            st.rerun()
            
    with col_b2:
        if st.button("🗑️ 删除选中", disabled=len(selected_ids) == 0):
            st.session_state.show_batch_delete = True

    # Render List
    st.markdown("---")
    
    # Custom Table Header
    cols = st.columns([0.5, 1, 2, 1.5, 2, 1.5, 1.5, 2])
    headers = ["选择", "ID", "名称", "类型", "所属项目", "计划日期", "状态", "描述"]
    for col, header in zip(cols, headers):
        col.markdown(f"**{header}**")
        
    st.markdown("---")

    for exp in page_exps:
        cols = st.columns([0.5, 1, 2, 1.5, 2, 1.5, 1.5, 2])
        exp_id = exp.get("id")
        
        # Checkbox
        is_selected = st.session_state.selected_experiments.get(exp_id, False)
        def on_change(eid=exp_id):
            st.session_state.selected_experiments[eid] = not st.session_state.selected_experiments.get(eid, False)
            
        cols[0].checkbox("", value=is_selected, key=f"chk_{exp_id}", on_change=on_change)
        cols[1].code(exp_id)
        cols[2].write(exp.get("name"))
        cols[3].write(exp.get("type"))
        
        proj_name = next((p["name"] for p in projects if p["id"] == exp.get("project_id")), "未知")
        cols[4].write(proj_name)
        cols[5].write(exp.get("planned_date"))
        cols[6].write(exp.get("status"))
        cols[7].write(exp.get("description", "")[:20] + "..." if len(exp.get("description", "")) > 20 else "")
        st.markdown("<hr style='margin: 5px 0'>", unsafe_allow_html=True)

    # Pagination Controls
    col_p1, col_p2, col_p3 = st.columns([1, 2, 1])
    with col_p2:
        prev, info, next_btn = st.columns([1, 2, 1])
        if prev.button("⬅️", disabled=current_page == 1):
            st.session_state.experiment_page -= 1
            st.rerun()
        info.markdown(f"<div style='text-align: center'>{current_page} / {total_pages}</div>", unsafe_allow_html=True)
        if next_btn.button("➡️", disabled=current_page == total_pages):
            st.session_state.experiment_page += 1
            st.rerun()

    # --- Batch Delete Dialog ---
    if st.session_state.get("show_batch_delete"):
        with st.expander("⚠️ 确认删除", expanded=True):
            st.warning(f"即将删除 {len(selected_ids)} 个实验，此操作不可恢复！")
            if st.button("确认彻底删除", type="primary"):
                count = 0
                for eid in selected_ids:
                    if data_service.delete_experiment(eid):
                        count += 1
                        st.session_state.selected_experiments.pop(eid, None)
                st.success(f"已删除 {count} 个实验")
                st.session_state.show_batch_delete = False
                time.sleep(1)
                st.rerun()
            if st.button("取消"):
                st.session_state.show_batch_delete = False
                st.rerun()

    # --- Edit Form ---
    if st.session_state.show_edit_form and st.session_state.editing_experiment_id:
        exp_to_edit = data_service.get_experiment(st.session_state.editing_experiment_id)
        if exp_to_edit:
            with st.form("edit_exp_form"):
                st.subheader(f"编辑实验: {exp_to_edit.get('name')}")
                e_name = st.text_input("名称", value=exp_to_edit.get("name"))
                e_status = st.selectbox("状态", ["计划中", "进行中", "已完成", "已取消"], index=["计划中", "进行中", "已完成", "已取消"].index(exp_to_edit.get("status", "计划中")))
                
                if st.form_submit_button("保存"):
                    data_service.update_experiment(st.session_state.editing_experiment_id, {"name": e_name, "status": e_status})
                    st.success("更新成功")
                    st.session_state.show_edit_form = False
                    st.rerun()
                if st.form_submit_button("取消"):
                    st.session_state.show_edit_form = False
                    st.rerun()
