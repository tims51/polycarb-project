"""实验管理页面模块"""

import streamlit as st
from datetime import datetime
import time
import pandas as pd

def render_experiment_management(data_manager):
    """渲染实验管理页面"""
    # 定义更新选择状态的辅助函数
    def update_selection(exp_id, checkbox_key):
        """更新实验选择状态的辅助函数"""
        st.session_state.selected_experiments[exp_id] = st.session_state[checkbox_key]
    
    # 初始化编辑状态
    if "editing_experiment_id" not in st.session_state:
        st.session_state.editing_experiment_id = None
    
    if "show_edit_form" not in st.session_state:
        st.session_state.show_edit_form = False
    
    # 初始化分页状态
    if "experiment_page" not in st.session_state:
        st.session_state.experiment_page = 1
    
    st.header("🧪 实验管理")
    
    # 获取数据
    experiments = data_manager.get_all_experiments()
    projects = data_manager.get_all_projects()
    
    # 创建新实验的表单
    with st.expander("➕ 创建新实验", expanded=True):
        with st.form("create_experiment_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                exp_name = st.text_input("实验名称*")
                exp_type = st.selectbox("实验类型*", ["合成实验", "性能测试", "配方优化", "稳定性测试"])
                
                # 项目选择
                project_options = {p["name"]: p["id"] for p in projects}
                if project_options:
                    selected_project_name = st.selectbox(
                        "所属项目*",
                        options=list(project_options.keys())
                    )
                    project_id = project_options.get(selected_project_name)
                else:
                    st.warning("请先创建项目！")
                    project_id = None
            
            with col2:
                planned_date = st.date_input("计划日期*", datetime.now())
                priority = st.select_slider("优先级", options=["低", "中", "高"], value="中")
                exp_status = st.selectbox("状态", ["计划中", "进行中", "已完成", "已取消"])
            
            description = st.text_area("实验描述")
            
            submitted = st.form_submit_button("创建实验", type="primary")
            if submitted:
                if exp_name and project_id:
                    new_experiment = {
                        "name": exp_name,
                        "type": exp_type,
                        "project_id": project_id,
                        "planned_date": planned_date.strftime("%Y-%m-%d"),
                        "actual_date": planned_date.strftime("%Y-%m-%d") if exp_status == "已完成" else None,
                        "priority": priority,
                        "status": exp_status,
                        "description": description
                    }
                    if data_manager.add_experiment(new_experiment):
                        st.success(f"实验 '{exp_name}' 创建成功！")
                        st.rerun()
                    else:
                        st.error("创建实验失败，请重试")
                else:
                    st.error("请填写必填项")
    
    st.divider()
    
    # 实验列表（集成勾选框删除功能）
    st.subheader("📋 实验列表")
    
    # 添加CSS样式
    st.markdown("""
    <style>
    /* 调整实验列表区域字体大小和行高 */
    .experiment-list-area div[data-testid="column"] p,
    .experiment-list-area div[data-testid="column"] code,
    .experiment-list-area div[data-testid="column"] span {
        font-size: 15px !important;
        line-height: 1.2 !important;
        margin-bottom: 4px !important;
        margin-top: 4px !important;
    }
    
    /* 调整表头字体 */
    .experiment-list-area div[data-testid="column"] h1,
    .experiment-list-area div[data-testid="column"] h2,
    .experiment-list-area div[data-testid="column"] h3,
    .experiment-list-area div[data-testid="column"] h4,
    .experiment-list-area div[data-testid="column"] h5,
    .experiment-list-area div[data-testid="column"] h6 {
        font-size: 16px !important;
        margin-bottom: 6px !important;
        margin-top: 6px !important;
    }
    
    /* 调整复选框大小和位置 */
    .experiment-list-area .stCheckbox {
        margin-top: 4px;
        margin-bottom: 4px;
        padding-top: 2px !important;
        padding-bottom: 2px !important;
    }
    
    /* 调整复选框标签 */
    .experiment-list-area .stCheckbox > label {
        padding-top: 2px !important;
        padding-bottom: 2px !important;
        min-height: 24px !important;
    }
    
    /* 调整ID列的代码字体 */
    .experiment-list-area code {
        font-size: 14px !important;
        font-weight: bold;
        padding: 1px 3px !important;
    }
    
    /* 调整实验名称字体 */
    .experiment-list-area strong {
        font-size: 15px !important;
    }
    
    /* 调整状态图标大小 */
    .experiment-list-area span[role="img"] {
        font-size: 16px;
    }
    
    /* 调整列间距 */
    .experiment-list-area div[data-testid="column"] {
        padding-top: 2px !important;
        padding-bottom: 2px !important;
    }
    
    /* 调整行分隔线 */
    .experiment-list-area hr {
        margin-top: 4px !important;
        margin-bottom: 4px !important;
        height: 1px !important;
    }
    
    /* 分页按钮样式 */
    .pagination-buttons .stButton {
        min-height: 28px !important;
    }
    
    /* 紧凑表格样式 */
    .compact-table-row {
        padding: 2px 0 !important;
        margin: 0 !important;
    }
    
    /* 页码信息样式 */
    .page-info {
        text-align: center;
        padding: 6px 0;
        font-size: 14px;
        color: #666;
    }
    </style>
    """, unsafe_allow_html=True)
    
    if experiments:
        # 初始化选择状态
        if "selected_experiments" not in st.session_state:
            st.session_state.selected_experiments = {}
        
        # 批量操作工具栏
        with st.container():
            batch_col1, batch_col2, batch_col3, batch_col4, batch_col5 = st.columns([1, 1, 1, 1, 2])
            
            with batch_col1:
                # 全选按钮
                if st.button("全选", key="select_all_btn", use_container_width=True, type="secondary"):
                    for exp in experiments:
                        exp_id = exp["id"]
                        st.session_state.selected_experiments[exp_id] = True
                    st.rerun()
            
            with batch_col2:
                # 取消全选按钮
                if st.button("取消全选", key="deselect_all_btn", use_container_width=True, type="secondary"):
                    for exp in experiments:
                        exp_id = exp["id"]
                        st.session_state.selected_experiments[exp_id] = False
                    st.rerun()
            
            with batch_col3:
                # 编辑按钮
                selected_count = sum(1 for exp in experiments 
                                   if exp["id"] in st.session_state.selected_experiments 
                                   and st.session_state.selected_experiments[exp["id"]])
                
                selected_exp_ids = []
                for exp in experiments:
                    exp_id = exp["id"]
                    if exp_id in st.session_state.selected_experiments:
                        if st.session_state.selected_experiments[exp_id]:
                            selected_exp_ids.append(exp_id)
                
                if selected_count == 1:
                    edit_disabled = False
                    selected_exp_id = selected_exp_ids[0]
                else:
                    edit_disabled = True
                    selected_exp_id = None
                
                if st.button(
                    "✏️ 编辑", 
                    key="edit_selected_btn",
                    use_container_width=True,
                    type="secondary",
                    disabled=edit_disabled
                ) and selected_exp_id:
                    st.session_state.editing_experiment_id = selected_exp_id
                    st.session_state.show_edit_form = True
                    st.rerun()
            
            with batch_col4:
                # 刷新列表按钮
                if st.button("🔄 刷新", key="refresh_list", use_container_width=True, type="secondary"):
                    st.rerun()
            
            with batch_col5:
                # 统计信息
                selected_count = sum(1 for exp in experiments 
                                   if exp["id"] in st.session_state.selected_experiments 
                                   and st.session_state.selected_experiments[exp["id"]])
                status_text = f"已选择 {selected_count} 个实验"
                
                if selected_count == 1:
                    selected_exp_id = selected_exp_ids[0]
                    selected_exp = next((e for e in experiments if e["id"] == selected_exp_id), None)
                    if selected_exp:
                        status_text = f"已选择: {selected_exp['name']}"
                
                st.caption(status_text)
        
        # 实验编辑表单
        if st.session_state.show_edit_form and st.session_state.editing_experiment_id:
            editing_exp = next((e for e in experiments if e["id"] == st.session_state.editing_experiment_id), None)
            
            if editing_exp:
                # 查找所属项目名称
                editing_project_name = "未知项目"
                for p in projects:
                    if p.get("id") == editing_exp.get("project_id"):
                        editing_project_name = p.get("name")
                        break
                
                with st.expander(f"✏️ 编辑实验: {editing_exp['name']}", expanded=True):
                    with st.form("edit_experiment_form"):
                        col1, col2 = st.columns(2)
                        with col1:
                            edit_exp_name = st.text_input(
                                "实验名称*", 
                                value=editing_exp.get("name", ""),
                                key="edit_exp_name"
                            )
                            edit_exp_type = st.selectbox(
                                "实验类型*", 
                                ["合成实验", "性能测试", "配方优化", "稳定性测试"],
                                index=["合成实验", "性能测试", "配方优化", "稳定性测试"].index(editing_exp.get("type", "合成实验")),
                                key="edit_exp_type"
                            )
                            
                            # 项目选择
                            project_options = {p["name"]: p["id"] for p in projects}
                            if project_options:
                                current_project_name = None
                                for p_name, p_id in project_options.items():
                                    if p_id == editing_exp.get("project_id"):
                                        current_project_name = p_name
                                        break
                                
                                if current_project_name is None and project_options:
                                    current_project_name = list(project_options.keys())[0]
                                
                                edit_project_name = st.selectbox(
                                    "所属项目*",
                                    options=list(project_options.keys()),
                                    index=list(project_options.keys()).index(current_project_name) if current_project_name in project_options else 0,
                                    key="edit_project_select"
                                )
                                edit_project_id = project_options.get(edit_project_name)
                        
                        with col2:
                            # 解析计划日期
                            planned_date_str = editing_exp.get("planned_date", "")
                            try:
                                if planned_date_str:
                                    edit_planned_date = st.date_input(
                                        "计划日期*", 
                                        value=datetime.strptime(planned_date_str, "%Y-%m-%d"),
                                        key="edit_planned_date"
                                    )
                                else:
                                    edit_planned_date = st.date_input(
                                        "计划日期*", 
                                        value=datetime.now(),
                                        key="edit_planned_date"
                                    )
                            except (ValueError, TypeError):
                                edit_planned_date = st.date_input(
                                    "计划日期*", 
                                    value=datetime.now(),
                                    key="edit_planned_date"
                                )
                            
                            priority_options = ["低", "中", "高"]
                            current_priority = editing_exp.get("priority", "中")
                            priority_index = priority_options.index(current_priority) if current_priority in priority_options else 1
                            
                            edit_priority = st.select_slider(
                                "优先级", 
                                options=priority_options,
                                value=priority_options[priority_index],
                                key="edit_priority"
                            )
                            
                            status_options = ["计划中", "进行中", "已完成", "已取消"]
                            current_status = editing_exp.get("status", "计划中")
                            status_index = status_options.index(current_status) if current_status in status_options else 0
                            
                            edit_status = st.selectbox(
                                "状态", 
                                status_options,
                                index=status_index,
                                key="edit_status"
                            )
                        
                        edit_description = st.text_area(
                            "实验描述", 
                            value=editing_exp.get("description", ""),
                            height=100,
                            key="edit_description"
                        )
                        
                        # 操作按钮
                        col_btn1, col_btn2, col_btn3 = st.columns(3)
                        
                        with col_btn1:
                            save_submitted = st.form_submit_button(
                                "💾 保存修改", 
                                type="primary",
                                use_container_width=True
                            )
                        
                        with col_btn2:
                            if st.form_submit_button(
                                "🔄 重置表单", 
                                type="secondary",
                                use_container_width=True
                            ):
                                st.rerun()
                        
                        with col_btn3:
                            cancel_submitted = st.form_submit_button(
                                "❌ 取消编辑", 
                                type="secondary",
                                use_container_width=True
                            )
                        
                        # 处理表单提交
                        if save_submitted:
                            if edit_exp_name and edit_project_id:
                                updated_experiment = {
                                    "name": edit_exp_name,
                                    "type": edit_exp_type,
                                    "project_id": edit_project_id,
                                    "planned_date": edit_planned_date.strftime("%Y-%m-%d"),
                                    "actual_date": edit_planned_date.strftime("%Y-%m-%d") if edit_status == "已完成" else None,
                                    "priority": edit_priority,
                                    "status": edit_status,
                                    "description": edit_description,
                                }
                                
                                if data_manager.update_experiment(st.session_state.editing_experiment_id, updated_experiment):
                                    st.success(f"✅ 实验 '{edit_exp_name}' 更新成功！")
                                    
                                    st.session_state.editing_experiment_id = None
                                    st.session_state.show_edit_form = False
                                    
                                    for exp in experiments:
                                        exp_id = exp["id"]
                                        st.session_state.selected_experiments[exp_id] = False
                                    
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error("❌ 保存修改失败，请重试")
                            else:
                                st.error("⚠️ 实验名称和所属项目为必填项")
                        
                        if cancel_submitted:
                            st.session_state.editing_experiment_id = None
                            st.session_state.show_edit_form = False
                            st.info("已取消编辑操作")
                            time.sleep(0.5)
                            st.rerun()
        
        # 分页设置
        PAGE_SIZE = 20
        total_experiments = len(experiments)
        total_pages = (total_experiments + PAGE_SIZE - 1) // PAGE_SIZE
        
        # 确保当前页码有效
        if st.session_state.experiment_page < 1:
            st.session_state.experiment_page = 1
        elif st.session_state.experiment_page > total_pages and total_pages > 0:
            st.session_state.experiment_page = total_pages
        
        # 获取当前页的实验数据
        start_idx = (st.session_state.experiment_page - 1) * PAGE_SIZE
        end_idx = min(start_idx + PAGE_SIZE, total_experiments)
        current_page_experiments = experiments[start_idx:end_idx]
        
        # 创建带勾选框的实验表格
        st.markdown("---")
        
        # 使用CSS类包装整个实验列表区域
        st.markdown('<div class="experiment-list-area">', unsafe_allow_html=True)
        
        # 表头
        col_header = st.columns([1, 2, 2, 2, 2, 2, 2, 3])
        headers = ["选择", "ID", "实验名称", "类型", "所属项目", "计划日期", "状态", "描述"]
        for i, header in enumerate(headers):
            col_header[i].markdown(f"<h5 style='margin:0; padding:4px 0; font-size:15px;'>{header}</h5>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        # 实验行数据
        for exp in current_page_experiments:
            # 查找项目名称
            project_name = "未知项目"
            for p in projects:
                if p.get("id") == exp.get("project_id"):
                    project_name = p.get("name")
                    break
            
            # 获取实验信息
            exp_id = exp.get("id")
            exp_name = exp.get("name", "未命名")
            exp_type = exp.get("type", "")
            exp_plan_date = exp.get("planned_date", "")
            exp_status = exp.get("status", "")
            exp_desc = exp.get("description", "")[:25] + "..." if len(exp.get("description", "")) > 25 else exp.get("description", "")
            
            # 创建一行
            col_row = st.columns([1, 2, 2, 2, 2, 2, 2, 3])
            
            # 勾选框
            with col_row[0]:
                current_value = st.session_state.selected_experiments.get(exp_id, False)
                checkbox_key = f"exp_checkbox_{exp_id}"
                
                if checkbox_key not in st.session_state:
                    st.session_state[checkbox_key] = current_value
                
                is_selected = st.checkbox(
                    "",
                    value=st.session_state[checkbox_key],
                    key=checkbox_key,
                    label_visibility="collapsed",
                    on_change=lambda exp_id=exp_id, key=checkbox_key: update_selection(exp_id, key)
                )
                
                st.session_state.selected_experiments[exp_id] = is_selected
            
            # 其他列数据
            with col_row[1]:
                st.markdown(f"<span style='font-size:14px; font-weight:bold; padding:2px 0; display:block;'>`{exp_id}`</span>", unsafe_allow_html=True)
            
            with col_row[2]:
                st.markdown(f"<strong style='font-size:14px; padding:2px 0; display:block;'>{exp_name}</strong>", unsafe_allow_html=True)
            
            with col_row[3]:
                st.markdown(f"<span style='font-size:14px; padding:2px 0; display:block;'>{exp_type}</span>", unsafe_allow_html=True)
            
            with col_row[4]:
                st.markdown(f"<span style='font-size:14px; padding:2px 0; display:block;'>{project_name}</span>", unsafe_allow_html=True)
            
            with col_row[5]:
                st.markdown(f"<span style='font-size:14px; padding:2px 0; display:block;'>{exp_plan_date}</span>", unsafe_allow_html=True)
            
            with col_row[6]:
                status_colors = {
                    "计划中": "🟡",
                    "进行中": "🟢",
                    "已完成": "✅",
                    "已取消": "❌"
                }
                status_emoji = status_colors.get(exp_status, "⚪")
                st.markdown(f"<span style='font-size:14px; padding:2px 0; display:block;'>{status_emoji} {exp_status}</span>", unsafe_allow_html=True)
            
            with col_row[7]:
                st.markdown(f"<span style='font-size:13px; padding:2px 0; display:block;'>{exp_desc}</span>", unsafe_allow_html=True)
            
            # 更细的行分隔线
            st.markdown("<hr style='margin:2px 0; height:0.5px;'>", unsafe_allow_html=True)
        
        # 关闭CSS包装器
        st.markdown('</div>', unsafe_allow_html=True)
        
        # 分页控制
        if total_pages > 1:
            st.markdown("---")
            
            current_page = st.session_state.experiment_page
            start_num = (current_page - 1) * PAGE_SIZE + 1
            end_num = min(current_page * PAGE_SIZE, total_experiments)
            
            # 页码信息行
            info_col1, info_col2, info_col3 = st.columns([1, 2, 1])
            
            with info_col2:
                st.markdown(
                    f"<div class='page-info'>"
                    f"第 <strong>{current_page}</strong> 页 / 共 <strong>{total_pages}</strong> 页 · "
                    f"显示 <strong>{start_num}-{end_num}</strong> 条，共 <strong>{total_experiments}</strong> 条"
                    f"</div>", 
                    unsafe_allow_html=True
                )
            
            # 分页按钮行
            pagination_col1, pagination_col2, pagination_col3, pagination_col4 = st.columns([2, 1, 1, 2])
            
            with pagination_col2:
                if st.button(
                    "⬅️ 上一页", 
                    key="prev_page", 
                    disabled=st.session_state.experiment_page <= 1, 
                    use_container_width=True,
                    type="secondary"
                ):
                    st.session_state.experiment_page -= 1
                    st.rerun()
            
            with pagination_col3:
                if st.button(
                    "下一页 ➡️", 
                    key="next_page", 
                    disabled=st.session_state.experiment_page >= total_pages, 
                    use_container_width=True,
                    type="secondary"
                ):
                    st.session_state.experiment_page += 1
                    st.rerun()
            
            # 快速跳转行
            if total_pages > 5:
                jump_col1, jump_col2, jump_col3 = st.columns([1, 2, 1])
                
                with jump_col2:
                    jump_page = st.number_input(
                        "跳转到",
                        min_value=1,
                        max_value=total_pages,
                        value=st.session_state.experiment_page,
                        key="jump_page_input",
                        label_visibility="collapsed",
                        step=1
                    )
                    
                    if jump_page != st.session_state.experiment_page:
                        st.session_state.experiment_page = jump_page
                        st.rerun()
        
        # 批量删除功能
        st.markdown("### 🗑️ 批量删除")
        
        # 统计选中的实验
        selected_exp_ids = []
        for exp in experiments:
            exp_id = exp["id"]
            if exp_id in st.session_state.selected_experiments:
                if st.session_state.selected_experiments[exp_id]:
                    selected_exp_ids.append(exp_id)
        
        if selected_exp_ids:
            # 获取选中的实验名称
            selected_exp_names = []
            for exp in experiments:
                if exp["id"] in selected_exp_ids:
                    selected_exp_names.append(exp["name"])
            
            st.warning(f"⚠️ 已选择 {len(selected_exp_ids)} 个实验进行删除")
            
            # 显示选中的实验列表
            with st.expander("📋 查看选中实验", expanded=False):
                for i, exp_id in enumerate(selected_exp_ids):
                    exp_info = next((e for e in experiments if e["id"] == exp_id), None)
                    if exp_info:
                        st.markdown(f"{i+1}. **{exp_info['name']}** (ID: {exp_id})")
            
            # 删除确认
            delete_col1, delete_col2 = st.columns(2)
            
            with delete_col1:
                if st.button(
                    "🗑️ 删除选中", 
                    key="delete_selected_exps",
                    use_container_width=True,
                    type="primary"
                ):
                    st.session_state.confirm_batch_delete = True
                    st.rerun()
            
            with delete_col2:
                if st.button(
                    "❌ 取消", 
                    key="cancel_batch_delete",
                    use_container_width=True,
                    type="secondary"
                ):
                    for exp in experiments:
                        exp_id = exp["id"]
                        st.session_state.selected_experiments[exp_id] = False
                        checkbox_key = f"exp_checkbox_{exp_id}"
                        if checkbox_key in st.session_state:
                            st.session_state[checkbox_key] = False
                    st.rerun()
            
            # 确认对话框
            if "confirm_batch_delete" in st.session_state and st.session_state.confirm_batch_delete:
                with st.container(border=True):
                    st.markdown("#### ⚠️ 确认批量删除")
                    st.error("**危险操作！** 此操作将永久删除以下实验，不可恢复！")
                    
                    st.markdown("**将要删除的实验:**")
                    for i, exp_id in enumerate(selected_exp_ids):
                        exp_info = next((e for e in experiments if e["id"] == exp_id), None)
                        if exp_info:
                            st.markdown(f"- **{exp_info['name']}** (ID: {exp_id})")
                    
                    st.markdown("---")
                    confirm_text = st.text_input(
                        "请输入 '确认删除' 以继续:",
                        key="batch_delete_confirm_text",
                        placeholder="请输入 '确认删除'"
                    )
                    
                    confirm_col1, confirm_col2 = st.columns(2)
                    
                    with confirm_col1:
                        if st.button(
                            "✅ 确认删除", 
                            key="final_batch_delete",
                            use_container_width=True,
                            type="primary",
                            disabled=confirm_text != "确认删除"
                        ):
                            with st.spinner("正在删除选中的实验..."):
                                success_count = 0
                                error_count = 0
                                
                                for exp_id in selected_exp_ids:
                                    if data_manager.delete_experiment(exp_id):
                                        success_count += 1
                                    else:
                                        error_count += 1
                                
                                del st.session_state.confirm_batch_delete
                                
                                for exp_id in selected_exp_ids:
                                    if exp_id in st.session_state.selected_experiments:
                                        st.session_state.selected_experiments[exp_id] = False
                                    checkbox_key = f"exp_checkbox_{exp_id}"
                                    if checkbox_key in st.session_state:
                                        st.session_state[checkbox_key] = False
                                
                                if error_count == 0:
                                    st.success(f"✅ 成功删除 {success_count} 个实验！")
                                else:
                                    st.warning(f"⚠️ 成功删除 {success_count} 个实验，{error_count} 个删除失败")
                                
                                time.sleep(1.5)
                                st.rerun()
                    
                    with confirm_col2:
                        if st.button(
                            "❌ 取消删除", 
                            key="cancel_final_delete",
                            use_container_width=True,
                            type="secondary"
                        ):
                            del st.session_state.confirm_batch_delete
                            st.info("已取消批量删除操作")
                            time.sleep(0.5)
                            st.rerun()
        else:
            st.info("请先勾选要删除的实验")
            
            with st.expander("💡 使用提示", expanded=False):
                st.markdown("""
                1. **勾选实验**: 点击每行前面的复选框选择实验
                2. **全选**: 点击"全选"按钮一次性选择所有实验
                3. **取消全选**: 点击"取消全选"按钮取消所有选择
                4. **编辑实验**: 勾选一个实验后，点击"编辑"按钮修改实验信息
                5. **刷新**: 点击"刷新"按钮重新加载实验列表
                6. **分页浏览**: 使用表格下方的分页控制浏览所有实验
                7. **批量删除**: 选择实验后，点击"删除选中"按钮进行批量删除
                8. **防误删**: 删除操作需要双重确认，防止误操作
                """)
    else:
        st.info("暂无实验数据，请创建第一个实验。")
