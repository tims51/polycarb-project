"""数据管理页面模块"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time
import shutil
from pathlib import Path
import json
import uuid

def render_data_management(data_manager):
    """渲染数据管理页面"""
    st.header("💾 数据管理")
    
    user = st.session_state.get("current_user")
    if not data_manager.has_permission(user, "manage_data"):
        st.info("仅管理员可以访问数据管理与备份功能。")
        return
    
    # 使用标签页组织功能
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🗂️ 实验数据管理",
        "📤 数据导出", 
        "📥 数据导入", 
        "🔙 备份管理",
        "⚙️ 系统设置"
    ])
    
    with tab1:
        _render_experiment_data_management_tab(data_manager)
    
    # 数据导出模块
    with tab2:
        _render_export_tab(data_manager)
    
    # 数据导入模块
    with tab3:
        _render_import_tab(data_manager)
    
    # 备份管理模块
    with tab4:
        _render_backup_tab(data_manager)
    
    # 系统设置模块
    with tab5:
        _render_system_settings_tab(data_manager)

def _render_experiment_data_management_tab(data_manager):
    st.subheader("🗂️ 实验数据管理")
    
    if "data_mgmt_page_id" not in st.session_state:
        st.session_state.data_mgmt_page_id = str(uuid.uuid4())[:8]
    
    paste_tab, mortar_tab, concrete_tab = st.tabs(["🧫 净浆", "🏗️ 砂浆", "🏢 混凝土"])
    
    with paste_tab:
        _render_experiment_records_manager(
            title="🧫 净浆实验数据",
            type_key="paste",
            records=data_manager.get_all_paste_experiments(),
            update_record=data_manager.update_paste_experiment,
            delete_record=data_manager.delete_paste_experiment,
        )
    
    with mortar_tab:
        _render_experiment_records_manager(
            title="🏗️ 砂浆实验数据",
            type_key="mortar",
            records=data_manager.get_all_mortar_experiments(),
            update_record=data_manager.update_mortar_experiment,
            delete_record=data_manager.delete_mortar_experiment,
        )
    
    with concrete_tab:
        _render_experiment_records_manager(
            title="🏢 混凝土实验数据",
            type_key="concrete",
            records=data_manager.get_all_concrete_experiments(),
            update_record=data_manager.update_concrete_experiment,
            delete_record=data_manager.delete_concrete_experiment,
        )

def _safe_parse_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(value), fmt)
        except Exception:
            pass
    return None

def _safe_parse_date(value):
    if not value:
        return None
    if hasattr(value, "year") and hasattr(value, "month") and hasattr(value, "day"):
        return value
    dt = _safe_parse_datetime(value)
    if dt:
        return dt.date()
    return None

def _filter_records(type_key, records, keyword, formula_filter, start_date, end_date):
    keyword_value = (keyword or "").strip().lower()
    
    filtered = []
    for r in records:
        record = r or {}
        if formula_filter and formula_filter != "全部":
            if str(record.get("formula_name", "")) != formula_filter:
                continue
        
        created_at_dt = _safe_parse_datetime(record.get("created_at"))
        if created_at_dt and start_date and end_date:
            if created_at_dt.date() < start_date or created_at_dt.date() > end_date:
                continue
        
        if keyword_value:
            haystack = " ".join([
                str(record.get("id", "")),
                str(record.get("formula_name", "")),
                str(record.get("operator", "")),
                str(record.get("notes", "")),
            ]).lower()
            if keyword_value not in haystack:
                continue
        
        filtered.append(record)
    
    filtered.sort(key=lambda x: (_safe_parse_datetime(x.get("created_at")) or datetime.min), reverse=True)
    return filtered

def _render_experiment_records_manager(title, type_key, records, update_record, delete_record):
    st.markdown(f"### {title}")
    
    normalized_records = [r for r in (records or []) if isinstance(r, dict)]
    st.caption(f"共 {len(normalized_records)} 条记录")
    
    formula_options = sorted({str(r.get("formula_name", "")).strip() for r in normalized_records if str(r.get("formula_name", "")).strip()})
    formula_options = ["全部"] + formula_options
    
    default_start = (datetime.now() - timedelta(days=30)).date()
    default_end = datetime.now().date()
    
    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns([2, 2, 2, 1])
    with filter_col1:
        keyword = st.text_input("关键词", key=f"{type_key}_mgmt_kw_{st.session_state.data_mgmt_page_id}")
    with filter_col2:
        formula_filter = st.selectbox("关联配方", options=formula_options, key=f"{type_key}_mgmt_formula_{st.session_state.data_mgmt_page_id}")
    with filter_col3:
        start_date, end_date = st.date_input(
            "创建时间范围",
            value=[default_start, default_end],
            key=f"{type_key}_mgmt_date_{st.session_state.data_mgmt_page_id}",
        )
    with filter_col4:
        page_size = st.selectbox("每页", options=[10, 20, 50], index=0, key=f"{type_key}_mgmt_ps_{st.session_state.data_mgmt_page_id}")
    
    filtered = _filter_records(type_key, normalized_records, keyword, formula_filter, start_date, end_date)
    st.caption(f"筛选后 {len(filtered)} 条")
    
    selected_key = f"{type_key}_mgmt_selected_ids"
    selected_ids = set(st.session_state.get(selected_key, []))
    
    page_key = f"{type_key}_mgmt_page"
    if page_key not in st.session_state:
        st.session_state[page_key] = 1
    
    total_pages = max(1, (len(filtered) + page_size - 1) // page_size)
    st.session_state[page_key] = min(max(1, st.session_state[page_key]), total_pages)
    page = st.session_state[page_key]
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_records = filtered[start_idx:end_idx]
    
    nav_col1, nav_col2, nav_col3, nav_col4 = st.columns([1, 2, 2, 1])
    with nav_col1:
        if st.button("⬅️ 上一页", disabled=(page <= 1), key=f"{type_key}_mgmt_prev_{st.session_state.data_mgmt_page_id}"):
            st.session_state[page_key] -= 1
            st.rerun()
    with nav_col2:
        st.write(f"第 {page} / {total_pages} 页")
    with nav_col3:
        jump_page = st.number_input(
            "跳转",
            min_value=1,
            max_value=total_pages,
            value=page,
            step=1,
            key=f"{type_key}_mgmt_jump_{st.session_state.data_mgmt_page_id}",
            label_visibility="collapsed",
        )
        if jump_page != page:
            st.session_state[page_key] = int(jump_page)
            st.rerun()
    with nav_col4:
        if st.button("下一页 ➡️", disabled=(page >= total_pages), key=f"{type_key}_mgmt_next_{st.session_state.data_mgmt_page_id}"):
            st.session_state[page_key] += 1
            st.rerun()
    
    action_col1, action_col2, action_col3, action_col4 = st.columns([1.2, 1.2, 2, 1.4])
    with action_col1:
        select_all = st.checkbox("全选本页", value=False, key=f"{type_key}_mgmt_select_all_{st.session_state.data_mgmt_page_id}")
    with action_col2:
        if st.button("清空选择", key=f"{type_key}_mgmt_clear_sel_{st.session_state.data_mgmt_page_id}"):
            st.session_state[selected_key] = []
            st.rerun()
    with action_col3:
        confirm_batch_delete = st.checkbox("确认删除选中记录", value=False, key=f"{type_key}_mgmt_confirm_del_{st.session_state.data_mgmt_page_id}")
    with action_col4:
        if st.button(
            "删除选中",
            type="primary",
            disabled=(not selected_ids or not confirm_batch_delete),
            key=f"{type_key}_mgmt_batch_del_{st.session_state.data_mgmt_page_id}",
        ):
            deleted = 0
            failed = 0
            failed_ids = set()
            for record_id in sorted(selected_ids):
                ok = False
                try:
                    ok = bool(delete_record(record_id))
                except Exception:
                    ok = False
                if ok:
                    deleted += 1
                else:
                    failed += 1
                    failed_ids.add(record_id)
            st.session_state[selected_key] = sorted(failed_ids)
            if deleted:
                st.success(f"已删除 {deleted} 条记录")
            if failed:
                st.error(f"删除失败 {failed} 条记录")
            time.sleep(0.3)
            st.rerun()
    
    header_cols = st.columns([0.7, 1.2, 3.0, 2.5, 1.8])
    header_cols[0].write("选择")
    header_cols[1].write("ID")
    header_cols[2].write("关联配方")
    header_cols[3].write("创建时间")
    header_cols[4].write("操作人")
    
    editing_key = f"{type_key}_mgmt_editing_id"
    for record in page_records:
        record_id = record.get("id")
        row_cols = st.columns([0.7, 1.2, 3.0, 2.5, 1.8])
        
        checkbox_key = f"{type_key}_mgmt_sel_{record_id}_{st.session_state.data_mgmt_page_id}"
        checkbox_value = select_all or (record_id in selected_ids)
        checked = row_cols[0].checkbox("", value=bool(checkbox_value), key=checkbox_key, label_visibility="collapsed")
        if checked:
            selected_ids.add(record_id)
        else:
            selected_ids.discard(record_id)
        
        row_cols[1].write(str(record_id))
        row_cols[2].write(str(record.get("formula_name", "")))
        row_cols[3].write(str(record.get("created_at", "")))
        row_cols[4].write(str(record.get("operator", "")))
        
        with st.expander(f"详情 - ID {record_id}", expanded=False):
            st.json(record)
            btn_col1, btn_col2 = st.columns([1, 1])
            with btn_col1:
                if st.button("编辑", key=f"{type_key}_mgmt_edit_btn_{record_id}_{st.session_state.data_mgmt_page_id}"):
                    st.session_state[editing_key] = record_id
                    st.rerun()
            with btn_col2:
                confirm_single = st.checkbox(
                    "确认删除此条",
                    value=False,
                    key=f"{type_key}_mgmt_single_confirm_{record_id}_{st.session_state.data_mgmt_page_id}",
                )
                if st.button(
                    "删除此条",
                    disabled=not confirm_single,
                    key=f"{type_key}_mgmt_single_del_{record_id}_{st.session_state.data_mgmt_page_id}",
                ):
                    ok = False
                    try:
                        ok = bool(delete_record(record_id))
                    except Exception:
                        ok = False
                    if ok:
                        st.success("已删除")
                        selected_ids.discard(record_id)
                        st.session_state[selected_key] = sorted(selected_ids)
                        time.sleep(0.3)
                        st.rerun()
                    else:
                        st.error("删除失败")
    
    st.session_state[selected_key] = sorted(selected_ids)
    
    editing_id = st.session_state.get(editing_key)
    if editing_id is not None:
        record_map = {r.get("id"): r for r in normalized_records}
        current = record_map.get(editing_id)
        if not current:
            st.session_state[editing_key] = None
            st.rerun()
        
        st.markdown("### ✏️ 编辑记录")
        st.write(f"正在编辑: ID {editing_id}")
        _render_structured_edit_form(
            type_key=type_key,
            record=current,
            update_record=update_record,
            cancel_edit=lambda: _cancel_edit(type_key),
        )

def _cancel_edit(type_key):
    editing_key = f"{type_key}_mgmt_editing_id"
    st.session_state[editing_key] = None
    st.rerun()

def _render_structured_edit_form(type_key, record, update_record, cancel_edit):
    record_id = record.get("id")
    page_id = st.session_state.data_mgmt_page_id
    form_key = f"{type_key}_mgmt_edit_form_{record_id}_{page_id}"
    
    test_date_default = _safe_parse_date(record.get("test_date")) or datetime.now().date()
    performance = record.get("performance") if isinstance(record.get("performance"), dict) else {}
    materials = record.get("materials") if isinstance(record.get("materials"), dict) else {}
    
    with st.form(form_key):
        base_col1, base_col2, base_col3 = st.columns([1.2, 2.2, 2.2])
        with base_col1:
            st.text_input("ID", value=str(record.get("id", "")), disabled=True, key=f"{form_key}_id")
        with base_col2:
            st.text_input("创建时间", value=str(record.get("created_at", "")), disabled=True, key=f"{form_key}_created_at")
        with base_col3:
            st.text_input("最后修改", value=str(record.get("last_modified", "")), disabled=True, key=f"{form_key}_last_modified")
        
        st.markdown("#### 基本信息")
        base2_col1, base2_col2 = st.columns(2)
        with base2_col1:
            formula_name = st.text_input("关联配方", value=str(record.get("formula_name", "")), key=f"{form_key}_formula")
        with base2_col2:
            operator = st.text_input("操作人", value=str(record.get("operator", "")), key=f"{form_key}_operator")
        
        if type_key == "paste":
            st.markdown("#### 配制参数")
            p_col1, p_col2, p_col3 = st.columns(3)
            with p_col1:
                water_cement_ratio = st.number_input(
                    "水胶比",
                    min_value=0.0,
                    value=float(record.get("water_cement_ratio", 0.0) or 0.0),
                    step=0.01,
                    key=f"{form_key}_wc",
                )
                cement_amount_g = st.number_input(
                    "水泥用量 (g)",
                    min_value=0.0,
                    value=float(record.get("cement_amount_g", 0.0) or 0.0),
                    step=1.0,
                    key=f"{form_key}_cement_g",
                )
            with p_col2:
                water_amount_g = st.number_input(
                    "用水量 (g)",
                    min_value=0.0,
                    value=float(record.get("water_amount_g", 0.0) or 0.0),
                    step=0.1,
                    key=f"{form_key}_water_g",
                )
                admixture_dosage_g = st.number_input(
                    "减水剂掺量 (g)",
                    min_value=0.0,
                    value=float(record.get("admixture_dosage_g", 0.0) or 0.0),
                    step=0.01,
                    key=f"{form_key}_dosage_g",
                )
            with p_col3:
                test_date = st.date_input("测试日期", value=test_date_default, key=f"{form_key}_test_date")
            
            st.markdown("#### 性能指标（流动度）")
            perf_col1, perf_col2, perf_col3 = st.columns(3)
            with perf_col1:
                flow_initial_mm = st.number_input(
                    "初始流动度(mm)",
                    min_value=0.0,
                    value=float(performance.get("flow_initial_mm", 0.0) or 0.0),
                    step=1.0,
                    key=f"{form_key}_flow_initial",
                )
                flow_10min_mm = st.number_input(
                    "10min流动度(mm)",
                    min_value=0.0,
                    value=float(performance.get("flow_10min_mm", 0.0) or 0.0),
                    step=1.0,
                    key=f"{form_key}_flow_10min",
                )
            with perf_col2:
                flow_30min_mm = st.number_input(
                    "30min流动度(mm)",
                    min_value=0.0,
                    value=float(performance.get("flow_30min_mm", 0.0) or 0.0),
                    step=1.0,
                    key=f"{form_key}_flow_30min",
                )
                flow_1h_mm = st.number_input(
                    "1h流动度(mm)",
                    min_value=0.0,
                    value=float(performance.get("flow_1h_mm", 0.0) or 0.0),
                    step=1.0,
                    key=f"{form_key}_flow_1h",
                )
            with perf_col3:
                flow_1_5h_mm = st.number_input(
                    "1.5h流动度(mm)",
                    min_value=0.0,
                    value=float(performance.get("flow_1_5h_mm", 0.0) or 0.0),
                    step=1.0,
                    key=f"{form_key}_flow_1_5h",
                )
                flow_2h_mm = st.number_input(
                    "2h流动度(mm)",
                    min_value=0.0,
                    value=float(performance.get("flow_2h_mm", 0.0) or 0.0),
                    step=1.0,
                    key=f"{form_key}_flow_2h",
                )
            
            notes = st.text_area("实验备注", value=str(record.get("notes", "") or ""), height=120, key=f"{form_key}_notes")
            
            submitted = st.form_submit_button("保存修改", type="primary")
            if submitted:
                if not str(formula_name).strip():
                    st.error("关联配方不能为空")
                    return
                updated_fields = {
                    "formula_name": str(formula_name).strip(),
                    "operator": str(operator).strip(),
                    "water_cement_ratio": float(water_cement_ratio),
                    "cement_amount_g": float(cement_amount_g),
                    "water_amount_g": float(water_amount_g),
                    "admixture_dosage_g": float(admixture_dosage_g),
                    "test_date": test_date.strftime("%Y-%m-%d"),
                    "performance": {
                        "flow_initial_mm": float(flow_initial_mm),
                        "flow_10min_mm": float(flow_10min_mm),
                        "flow_30min_mm": float(flow_30min_mm),
                        "flow_1h_mm": float(flow_1h_mm),
                        "flow_1_5h_mm": float(flow_1_5h_mm),
                        "flow_2h_mm": float(flow_2h_mm),
                    },
                    "notes": str(notes),
                }
                ok = bool(update_record(record_id, updated_fields))
                if ok:
                    st.success("保存成功")
                    time.sleep(0.3)
                    cancel_edit()
                else:
                    st.error("保存失败")
        
        if type_key == "mortar":
            st.markdown("#### 配制参数")
            m_col1, m_col2, m_col3 = st.columns(3)
            with m_col1:
                water_cement_ratio = st.number_input(
                    "水胶比",
                    min_value=0.0,
                    value=float(record.get("water_cement_ratio", 0.0) or 0.0),
                    step=0.01,
                    key=f"{form_key}_wc",
                )
                unit_weight = st.number_input(
                    "设计容重 (kg/m³)",
                    min_value=0.0,
                    value=float(record.get("unit_weight", 0.0) or 0.0),
                    step=10.0,
                    key=f"{form_key}_unit_weight",
                )
            with m_col2:
                admixture_dosage = st.number_input(
                    "减水剂掺量 (%)",
                    min_value=0.0,
                    value=float(record.get("admixture_dosage", 0.0) or 0.0),
                    step=0.05,
                    key=f"{form_key}_dosage",
                )
                sand_moisture = st.number_input(
                    "砂含水率 (%)",
                    min_value=0.0,
                    value=float(record.get("sand_moisture", 0.0) or 0.0),
                    step=0.1,
                    key=f"{form_key}_sand_moisture",
                )
            with m_col3:
                test_date = st.date_input("测试日期", value=test_date_default, key=f"{form_key}_test_date")
            
            st.markdown("#### 材料用量 (kg/m³)")
            mat_col1, mat_col2, mat_col3, mat_col4 = st.columns(4)
            with mat_col1:
                cement = st.number_input("水泥", min_value=0.0, value=float(materials.get("cement", 0.0) or 0.0), step=10.0, key=f"{form_key}_cement")
                mineral1 = st.number_input("矿物外加剂1", min_value=0.0, value=float(materials.get("mineral1", 0.0) or 0.0), step=5.0, key=f"{form_key}_min1")
            with mat_col2:
                mineral2 = st.number_input("矿物外加剂2", min_value=0.0, value=float(materials.get("mineral2", 0.0) or 0.0), step=5.0, key=f"{form_key}_min2")
                mineral3 = st.number_input("矿物外加剂3", min_value=0.0, value=float(materials.get("mineral3", 0.0) or 0.0), step=5.0, key=f"{form_key}_min3")
            with mat_col3:
                sand1 = st.number_input("砂1", min_value=0.0, value=float(materials.get("sand1", 0.0) or 0.0), step=10.0, key=f"{form_key}_sand1")
                sand2 = st.number_input("砂2", min_value=0.0, value=float(materials.get("sand2", 0.0) or 0.0), step=10.0, key=f"{form_key}_sand2")
            with mat_col4:
                sand3 = st.number_input("砂3", min_value=0.0, value=float(materials.get("sand3", 0.0) or 0.0), step=10.0, key=f"{form_key}_sand3")
                water = st.number_input("用水量", min_value=0.0, value=float(materials.get("water", 0.0) or 0.0), step=1.0, key=f"{form_key}_water")
            
            st.markdown("#### 性能指标")
            mp_col1, mp_col2, mp_col3 = st.columns(3)
            with mp_col1:
                flow = st.number_input("流动度 (mm)", min_value=0.0, value=float(performance.get("flow", 0.0) or 0.0), step=5.0, key=f"{form_key}_flow")
                strength_7d = st.number_input("7天强度 (MPa)", min_value=0.0, value=float(performance.get("strength_7d", 0.0) or 0.0), step=0.1, key=f"{form_key}_s7")
            with mp_col2:
                strength_28d = st.number_input("28天强度 (MPa)", min_value=0.0, value=float(performance.get("strength_28d", 0.0) or 0.0), step=0.1, key=f"{form_key}_s28")
            with mp_col3:
                air_content = st.number_input("含气量 (%)", min_value=0.0, value=float(performance.get("air_content", 0.0) or 0.0), step=0.1, key=f"{form_key}_air")
            
            notes = st.text_area("实验备注", value=str(record.get("notes", "") or ""), height=120, key=f"{form_key}_notes")
            
            submitted = st.form_submit_button("保存修改", type="primary")
            if submitted:
                if not str(formula_name).strip():
                    st.error("关联配方不能为空")
                    return
                updated_fields = {
                    "formula_name": str(formula_name).strip(),
                    "operator": str(operator).strip(),
                    "water_cement_ratio": float(water_cement_ratio),
                    "unit_weight": float(unit_weight),
                    "admixture_dosage": float(admixture_dosage),
                    "sand_moisture": float(sand_moisture),
                    "test_date": test_date.strftime("%Y-%m-%d"),
                    "materials": {
                        "cement": float(cement),
                        "mineral1": float(mineral1),
                        "mineral2": float(mineral2),
                        "mineral3": float(mineral3),
                        "sand1": float(sand1),
                        "sand2": float(sand2),
                        "sand3": float(sand3),
                        "water": float(water),
                        "actual_water": float(materials.get("actual_water", 0.0) or 0.0),
                    },
                    "performance": {
                        "flow": float(flow),
                        "air_content": float(air_content),
                        "strength_7d": float(strength_7d),
                        "strength_28d": float(strength_28d),
                    },
                    "notes": str(notes),
                }
                ok = bool(update_record(record_id, updated_fields))
                if ok:
                    st.success("保存成功")
                    time.sleep(0.3)
                    cancel_edit()
                else:
                    st.error("保存失败")
        
        if type_key == "concrete":
            st.markdown("#### 配制参数")
            c_col1, c_col2, c_col3 = st.columns(3)
            with c_col1:
                water_cement_ratio = st.number_input(
                    "水胶比",
                    min_value=0.0,
                    value=float(record.get("water_cement_ratio", 0.0) or 0.0),
                    step=0.01,
                    key=f"{form_key}_wc",
                )
                sand_ratio = st.number_input(
                    "砂率 (%)",
                    min_value=0.0,
                    value=float(record.get("sand_ratio", 0.0) or 0.0),
                    step=0.1,
                    key=f"{form_key}_sand_ratio",
                )
            with c_col2:
                unit_weight = st.number_input(
                    "设计容重 (kg/m³)",
                    min_value=0.0,
                    value=float(record.get("unit_weight", 0.0) or 0.0),
                    step=10.0,
                    key=f"{form_key}_unit_weight",
                )
                admixture_dosage = st.number_input(
                    "减水剂掺量 (%)",
                    min_value=0.0,
                    value=float(record.get("admixture_dosage", 0.0) or 0.0),
                    step=0.05,
                    key=f"{form_key}_dosage",
                )
            with c_col3:
                sand_moisture = st.number_input(
                    "砂含水率 (%)",
                    min_value=0.0,
                    value=float(record.get("sand_moisture", 0.0) or 0.0),
                    step=0.1,
                    key=f"{form_key}_sand_moisture",
                )
                stone_moisture = st.number_input(
                    "石含水率 (%)",
                    min_value=0.0,
                    value=float(record.get("stone_moisture", 0.0) or 0.0),
                    step=0.1,
                    key=f"{form_key}_stone_moisture",
                )
                test_date = st.date_input("测试日期", value=test_date_default, key=f"{form_key}_test_date")
            
            st.markdown("#### 材料用量 (kg/m³)")
            cc1, cc2, cc3, cc4 = st.columns(4)
            with cc1:
                cement = st.number_input("水泥", min_value=0.0, value=float(materials.get("cement", 0.0) or 0.0), step=10.0, key=f"{form_key}_cement")
                mineral1 = st.number_input("矿物外加剂1", min_value=0.0, value=float(materials.get("mineral1", 0.0) or 0.0), step=5.0, key=f"{form_key}_min1")
            with cc2:
                mineral2 = st.number_input("矿物外加剂2", min_value=0.0, value=float(materials.get("mineral2", 0.0) or 0.0), step=5.0, key=f"{form_key}_min2")
                mineral3 = st.number_input("矿物外加剂3", min_value=0.0, value=float(materials.get("mineral3", 0.0) or 0.0), step=5.0, key=f"{form_key}_min3")
            with cc3:
                sand1 = st.number_input("砂1", min_value=0.0, value=float(materials.get("sand1", 0.0) or 0.0), step=10.0, key=f"{form_key}_sand1")
                sand2 = st.number_input("砂2", min_value=0.0, value=float(materials.get("sand2", 0.0) or 0.0), step=10.0, key=f"{form_key}_sand2")
            with cc4:
                sand3 = st.number_input("砂3", min_value=0.0, value=float(materials.get("sand3", 0.0) or 0.0), step=10.0, key=f"{form_key}_sand3")
                stone1 = st.number_input("石1", min_value=0.0, value=float(materials.get("stone1", 0.0) or 0.0), step=10.0, key=f"{form_key}_stone1")
            
            cc5, cc6, cc7, cc8 = st.columns(4)
            with cc5:
                stone2 = st.number_input("石2", min_value=0.0, value=float(materials.get("stone2", 0.0) or 0.0), step=10.0, key=f"{form_key}_stone2")
            with cc6:
                stone3 = st.number_input("石3", min_value=0.0, value=float(materials.get("stone3", 0.0) or 0.0), step=10.0, key=f"{form_key}_stone3")
            with cc7:
                water = st.number_input("用水量", min_value=0.0, value=float(materials.get("water", 0.0) or 0.0), step=1.0, key=f"{form_key}_water")
            with cc8:
                actual_water = st.number_input("实际用水量", min_value=0.0, value=float(materials.get("actual_water", 0.0) or 0.0), step=1.0, key=f"{form_key}_actual_water")
            
            st.markdown("#### 性能指标")
            cp1, cp2, cp3 = st.columns(3)
            with cp1:
                slump_mm = st.number_input("坍落度 (mm)", min_value=0.0, value=float(performance.get("slump_mm", performance.get("slump_mm", 0.0)) or 0.0), step=5.0, key=f"{form_key}_slump")
                strength_7d_mpa = st.number_input("7天强度 (MPa)", min_value=0.0, value=float(performance.get("strength_7d_mpa", 0.0) or 0.0), step=0.1, key=f"{form_key}_s7")
            with cp2:
                slump_flow_mm = st.number_input("扩展度 (mm)", min_value=0.0, value=float(performance.get("slump_flow_mm", 0.0) or 0.0), step=10.0, key=f"{form_key}_slump_flow")
                strength_28d_mpa = st.number_input("28天强度 (MPa)", min_value=0.0, value=float(performance.get("strength_28d_mpa", 0.0) or 0.0), step=0.1, key=f"{form_key}_s28")
            with cp3:
                air_content_percent = st.number_input("含气量 (%)", min_value=0.0, value=float(performance.get("air_content_percent", 0.0) or 0.0), step=0.1, key=f"{form_key}_air")
                chloride_content_percent = st.number_input("氯离子含量 (%)", min_value=0.0, value=float(performance.get("chloride_content_percent", 0.0) or 0.0), step=0.001, key=f"{form_key}_cl")
            
            notes = st.text_area("实验备注", value=str(record.get("notes", "") or ""), height=120, key=f"{form_key}_notes")
            
            submitted = st.form_submit_button("保存修改", type="primary")
            if submitted:
                if not str(formula_name).strip():
                    st.error("关联配方不能为空")
                    return
                updated_fields = {
                    "formula_name": str(formula_name).strip(),
                    "operator": str(operator).strip(),
                    "water_cement_ratio": float(water_cement_ratio),
                    "sand_ratio": float(sand_ratio),
                    "unit_weight": float(unit_weight),
                    "admixture_dosage": float(admixture_dosage),
                    "sand_moisture": float(sand_moisture),
                    "stone_moisture": float(stone_moisture),
                    "test_date": test_date.strftime("%Y-%m-%d"),
                    "materials": {
                        "cement": float(cement),
                        "mineral1": float(mineral1),
                        "mineral2": float(mineral2),
                        "mineral3": float(mineral3),
                        "sand1": float(sand1),
                        "sand2": float(sand2),
                        "sand3": float(sand3),
                        "stone1": float(stone1),
                        "stone2": float(stone2),
                        "stone3": float(stone3),
                        "water": float(water),
                        "actual_water": float(actual_water),
                    },
                    "performance": {
                        "slump_mm": float(slump_mm),
                        "slump_flow_mm": float(slump_flow_mm),
                        "air_content_percent": float(air_content_percent),
                        "chloride_content_percent": float(chloride_content_percent),
                        "strength_7d_mpa": float(strength_7d_mpa),
                        "strength_28d_mpa": float(strength_28d_mpa),
                    },
                    "notes": str(notes),
                }
                ok = bool(update_record(record_id, updated_fields))
                if ok:
                    st.success("保存成功")
                    time.sleep(0.3)
                    cancel_edit()
                else:
                    st.error("保存失败")
        
        cancel_button = st.form_submit_button("取消编辑")
        if cancel_button:
            cancel_edit()

def _render_export_tab(data_manager):
    """渲染数据导出标签页"""
    st.subheader("📤 导出数据到Excel")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.info("""
        **导出功能说明:**
        - 导出所有数据到Excel文件
        - 包含项目、实验、原材料、合成实验、成品减水剂等所有数据
        - 自动生成数据字典说明
        - 文件格式: .xlsx (Excel 2007+)
        """)
    
    with col2:
        # 数据统计
        st.metric("项目数量", len(data_manager.get_all_projects()))
        st.metric("实验数量", len(data_manager.get_all_experiments()))
        st.metric("原材料数量", len(data_manager.get_all_raw_materials()))
    
    # 导出选项
    st.markdown("### 导出选项")
    
    col1, col2 = st.columns(2)
    with col1:
        filename = st.text_input(
            "导出文件名",
            value=f"聚羧酸减水剂研发数据_{datetime.now().strftime('%Y%m%d_%H%M')}",
            help="不需要添加.xlsx扩展名"
        )
    
    # 导出按钮
    if st.button("🚀 开始导出数据", type="primary", use_container_width=True):
        with st.spinner("正在准备导出数据..."):
            time.sleep(1)
            
            # 执行导出
            download_link = data_manager.export_to_excel()
            
            if download_link:
                st.success("✅ 数据导出成功！")
                st.markdown(download_link, unsafe_allow_html=True)
                
                # 显示导出统计
                with st.expander("📊 导出数据统计", expanded=False):
                    st.write(f"**项目:** {len(data_manager.get_all_projects())} 条")
                    st.write(f"**实验:** {len(data_manager.get_all_experiments())} 条")
                    st.write(f"**原材料:** {len(data_manager.get_all_raw_materials())} 条")
                    st.write(f"**合成实验:** {len(data_manager.get_all_synthesis_records())} 条")
                    st.write(f"**成品减水剂:** {len(data_manager.get_all_products())} 条")
            else:
                st.error("❌ 数据导出失败，请重试")

def _render_import_tab(data_manager):
    """渲染数据导入标签页"""
    st.subheader("📥 从Excel导入数据")
    
    st.warning("""
    ⚠️ **导入前请注意:**
    1. 建议先备份当前数据
    2. 导入将覆盖现有数据
    3. 确保导入文件格式正确
    4. 导入过程可能需要一些时间
    """)
    
    # 文件上传
    uploaded_file = st.file_uploader(
        "选择Excel文件", 
        type=['xlsx', 'xls'],
        help="支持 .xlsx 和 .xls 格式"
    )
    
    if uploaded_file is not None:
        try:
            # 预览数据
            st.markdown("### 文件预览")
            excel_file = pd.ExcelFile(uploaded_file)
            
            # 显示工作表信息
            sheet_names = excel_file.sheet_names
            st.write(f"**检测到 {len(sheet_names)} 个工作表:**")
            
            for sheet in sheet_names:
                with st.expander(f"📋 {sheet}", expanded=False):
                    try:
                        df = pd.read_excel(uploaded_file, sheet_name=sheet, nrows=10)
                        st.dataframe(df.head(5))
                        st.write(f"总行数: {len(df)}")
                    except Exception as e:
                        st.error(f"读取工作表 '{sheet}' 失败: {e}")
            
            # 导入选项
            st.markdown("### 导入选项")
            
            col1, col2 = st.columns(2)
            with col1:
                import_mode = st.radio(
                    "导入模式",
                    options=["替换现有数据", "合并数据（不重复）"],
                    index=0
                )
            
            with col2:
                conflict_resolution = st.selectbox(
                    "数据冲突处理",
                    options=["跳过重复数据", "覆盖重复数据"],
                    disabled=(import_mode == "替换现有数据")
                )
            
            # 备份选项
            create_backup = st.checkbox("导入前自动备份当前数据", value=True)
            
            # 导入按钮
            if st.button("🚀 开始导入数据", type="primary", use_container_width=True):
                if create_backup:
                    with st.spinner("正在创建备份..."):
                        data_manager.create_backup()
                        st.success("✅ 数据备份完成")
                
                with st.spinner("正在导入数据，请稍候..."):
                    success, message = data_manager.import_from_excel(uploaded_file)
                    
                    if success:
                        st.success(f"✅ 数据导入成功！")
                        st.info(f"导入统计: {message}")
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error(f"❌ 导入失败: {message}")
            
        except Exception as e:
            st.error(f"读取文件失败: {e}")

def _render_backup_tab(data_manager):
    """渲染备份管理标签页"""
    st.subheader("🔙 备份管理")
    
    col1, col2 = st.columns(2)
    with col1:
        # 立即备份
        if st.button("🔄 立即创建备份", use_container_width=True, type="primary"):
            with st.spinner("正在创建备份..."):
                if data_manager.create_backup():
                    st.success("✅ 备份创建成功！")
                    user = st.session_state.get("current_user")
                    data_manager.add_audit_log(user, "BACKUP_CREATED", "立即创建数据备份")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ 备份创建失败")
    
    with col2:
        # 手动触发备份清理
        if st.button("🧹 清理旧备份", use_container_width=True, type="secondary"):
            data_manager._cleanup_old_backups()
            st.success("✅ 备份清理完成")
            user = st.session_state.get("current_user")
            data_manager.add_audit_log(user, "BACKUP_CLEANED", "清理旧备份")
            time.sleep(1)
            st.rerun()
    
    # 备份文件列表
    st.markdown("### 📋 备份文件列表")
    
    backup_files = list(data_manager.backup_dir.glob("data_backup_*.json"))
    
    if backup_files:
        # 按修改时间排序（最新的在前面）
        backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        # 备份统计
        total_size = sum(f.stat().st_size for f in backup_files) / (1024 * 1024)  # MB
        st.write(f"**备份文件数量:** {len(backup_files)} 个")
        st.write(f"**总占用空间:** {total_size:.2f} MB")
        
        # 备份文件表格
        backup_data = []
        for i, file in enumerate(backup_files[:20], 1):
            file_size = file.stat().st_size / 1024  # KB
            modified_time = datetime.fromtimestamp(file.stat().st_mtime)
            backup_data.append({
                "序号": i,
                "文件名": file.name,
                "大小": f"{file_size:.1f} KB",
                "修改时间": modified_time.strftime("%Y-%m-%d %H:%M:%S"),
                "文件路径": str(file)
            })
        
        if backup_data:
            df = pd.DataFrame(backup_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
        
        st.markdown("### 🔧 备份操作")
        password = st.text_input("请输入管理员密码 (删除操作需要)", type="password", key="backup_op_password")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # 选择要恢复的备份
            backup_options = {f"{i+1}. {f.name}": str(f) for i, f in enumerate(backup_files[:10])}
            selected_backup = None
            if backup_options:
                selected_backup_key = st.selectbox(
                    "选择备份文件",
                    options=list(backup_options.keys()),
                    label_visibility="collapsed"
                )
                if selected_backup_key:
                    selected_backup = backup_options[selected_backup_key]
        
        with col2:
            if st.button("📥 恢复选中", disabled=not selected_backup, use_container_width=True):
                backup_file = Path(selected_backup)
                if backup_file.exists():
                    # 先备份当前数据
                    data_manager.create_backup()
                    
                    # 恢复备份
                    try:
                        shutil.copy2(backup_file, data_manager.data_file)
                        st.success("✅ 备份恢复成功！系统将重新加载...")
                        user = st.session_state.get("current_user")
                        detail = f"从备份 {backup_file.name} 恢复数据"
                        data_manager.add_audit_log(user, "BACKUP_RESTORED", detail)
                        time.sleep(2)
                        st.rerun()
                    except Exception as e:
                        st.error(f"恢复失败: {e}")

        with col3:
             if st.button("🗑️ 删除选中", disabled=not selected_backup, type="secondary", use_container_width=True):
                if data_manager.verify_admin_password(password):
                    backup_file = Path(selected_backup)
                    if backup_file.exists():
                        try:
                            backup_file.unlink()
                            st.success(f"✅ 备份 {backup_file.name} 已删除")
                            user = st.session_state.get("current_user")
                            detail = f"删除备份文件 {backup_file.name}"
                            data_manager.add_audit_log(user, "BACKUP_DELETED", detail)
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"删除失败: {e}")
                    else:
                        st.error("文件不存在")
                else:
                    st.error("密码错误")
        
        with col4:
            if st.button("� 删除所有", type="secondary", use_container_width=True):
                if data_manager.verify_admin_password(password):
                    if st.checkbox("确认删除所有?", key="confirm_del_all_backups"): # This checkbox logic inside button might be tricky in Streamlit reruns
                        # Streamlit button click resets on rerun. 
                        # Nested button/checkbox pattern is flaky.
                        # Better use a session state or just password + button is enough security?
                        # Or use st.popover (if available in this version) or expander.
                        pass
                    
                    # Let's simplify: Password is the confirmation.
                    # But "Delete All" is very dangerous.
                    # Let's use a separate expander for "Delete All" to be safe.
                    pass
                else:
                     st.error("密码错误")
                     
        if data_manager.verify_admin_password(password):
            with st.expander("🔥 危险操作：删除所有备份", expanded=False):
                st.warning("此操作将永久删除所有备份文件，不可恢复！")
                if st.button("确认永久删除所有备份", type="primary"):
                    for file in backup_files:
                        try:
                            file.unlink()
                        except: pass
                    st.success("✅ 所有备份文件已删除")
                    user = st.session_state.get("current_user")
                    data_manager.add_audit_log(user, "BACKUP_DELETED_ALL", "删除所有备份文件")
                    time.sleep(2)
                    st.rerun()

    else:
        st.info("暂无备份文件")

def _render_system_settings_tab(data_manager):
    """渲染系统设置标签页"""
    st.subheader("⚙️ 系统设置")
    
    st.markdown("### 系统信息")
    current_user = st.session_state.get("current_user")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if data_manager.data_file.exists():
            file_size = data_manager.data_file.stat().st_size / 1024  # KB
            st.metric("数据文件大小", f"{file_size:.1f} KB")
        else:
            st.metric("数据文件大小", "0 KB")
    
    with col2:
        backup_count = len(list(data_manager.backup_dir.glob("data_backup_*.json")))
        st.metric("备份文件数量", backup_count)
    
    with col3:
        if data_manager.data_file.exists():
            st.metric("最后修改", datetime.fromtimestamp(
                data_manager.data_file.stat().st_mtime).strftime("%m-%d %H:%M")
            )
        else:
            st.metric("最后修改", "无")
    
    st.markdown("### 🔐 管理员口令设置")
    with st.form("admin_password_form"):
        col_old, col_new, col_confirm = st.columns(3)
        with col_old:
            old_pwd = st.text_input("当前口令", type="password", key="admin_pwd_old")
        with col_new:
            new_pwd = st.text_input("新口令", type="password", key="admin_pwd_new")
        with col_confirm:
            confirm_pwd = st.text_input("确认新口令", type="password", key="admin_pwd_confirm")
        submitted = st.form_submit_button("保存口令")
        if submitted:
            if not old_pwd or not new_pwd or not confirm_pwd:
                st.error("请完整填写所有字段")
            elif not data_manager.verify_admin_password(old_pwd):
                st.error("当前口令错误")
            elif new_pwd != confirm_pwd:
                st.error("两次输入的新口令不一致")
            else:
                ok = data_manager.set_admin_password(new_pwd)
                if ok:
                    st.success("管理员口令已更新")
                    data_manager.add_audit_log(current_user, "ADMIN_PASSWORD_CHANGED", "管理员口令已更新")
                else:
                    st.error("保存管理员口令失败")
    
    st.markdown("### 👤 管理员账号信息")
    admin_users = data_manager.get_admin_users()
    if admin_users:
        cols = st.columns([2, 2, 2])
        cols[0].markdown("**用户名**")
        cols[1].markdown("**角色**")
        cols[2].markdown("**状态**")
        for u in admin_users:
            c1, c2, c3 = st.columns([2, 2, 2])
            c1.write(str(u.get("username", "")))
            c2.write("管理员")
            status_label = "启用" if u.get("active", True) else "停用"
            c3.write(status_label)
    else:
        st.info("当前没有激活的管理员用户，系统将自动创建默认管理员。")
    st.caption("默认情况下，当系统没有管理员用户时，会自动创建用户名为 admin 的管理员账号。其初始密码为环境变量 APP_ADMIN_PASSWORD 的值，如未设置则为 admin。管理员口令仅用于系统设置中的高危操作二次验证，与登录密码相互独立。")
    
    st.markdown("### 🔑 管理员登录密码修改")
    if not current_user or current_user.get("role") != "admin":
        st.info("仅管理员登录账号可以在此修改登录密码。")
    else:
        with st.form("admin_login_password_form"):
            col_old, col_new, col_confirm = st.columns(3)
            with col_old:
                old_login_pwd = st.text_input("当前登录密码", type="password", key="admin_login_pwd_old")
            with col_new:
                new_login_pwd = st.text_input("新登录密码", type="password", key="admin_login_pwd_new")
            with col_confirm:
                confirm_login_pwd = st.text_input("确认新登录密码", type="password", key="admin_login_pwd_confirm")
            submitted_admin_login = st.form_submit_button("保存登录密码")
            if submitted_admin_login:
                if not old_login_pwd or not new_login_pwd or not confirm_login_pwd:
                    st.error("请完整填写所有字段")
                elif new_login_pwd != confirm_login_pwd:
                    st.error("两次输入的新登录密码不一致")
                else:
                    ok, msg = data_manager.change_user_password(current_user.get("id"), old_login_pwd, new_login_pwd)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)
    
    st.markdown("### 👥 用户与权限管理")
    users = data_manager.get_all_users()
    if users:
        total_users = len(users)
        total_admins = len([u for u in users if u.get("role") == "admin" and u.get("active", True)])
        total_inactive = len([u for u in users if not u.get("active", True)])
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("用户总数", total_users)
        mc2.metric("激活的管理员", total_admins)
        mc3.metric("已停用用户", total_inactive)
        
        role_options = ["user", "admin"]
        for u in users:
            user_id = u.get("id")
            username = str(u.get("username", ""))
            current_role = u.get("role", "user")
            current_active = u.get("active", True)
            created_at = str(u.get("created_at", ""))
            
            box = st.container()
            with box:
                c1, c2, c3, c4 = st.columns([2.2, 1.6, 1.4, 2.0])
                c1.markdown(f"**{username}**")
                new_role = c2.selectbox(
                    "角色",
                    options=role_options,
                    index=role_options.index(current_role) if current_role in role_options else 0,
                    key=f"user_role_{user_id}",
                )
                new_active = c3.checkbox(
                    "启用",
                    value=bool(current_active),
                    key=f"user_active_{user_id}",
                )
                c4.caption(f"创建时间：{created_at}")
                
                btn_col1, btn_col2 = st.columns([1, 3])
                with btn_col1:
                    if st.button("保存修改", key=f"user_save_{user_id}"):
                        fields = {}
                        if new_role != current_role:
                            fields["role"] = new_role
                        if bool(new_active) != bool(current_active):
                            fields["active"] = bool(new_active)
                        if not fields:
                            st.info("没有需要保存的变更")
                        else:
                            active_admins = [x for x in users if x.get("role") == "admin" and x.get("active", True)]
                            is_last_admin = (
                                current_role == "admin"
                                and current_active
                                and len(active_admins) <= 1
                            )
                            will_remove_admin = ("role" in fields and fields["role"] != "admin") or ("active" in fields and fields["active"] is False)
                            if is_last_admin and will_remove_admin:
                                st.error("系统至少需要一个激活的管理员，无法移除最后一个管理员。")
                            else:
                                ok = data_manager.update_user(user_id, fields)
                                if ok:
                                    st.success("用户信息已更新")
                                    changes = []
                                    if "role" in fields:
                                        changes.append(f"角色: {current_role} -> {fields['role']}")
                                    if "active" in fields:
                                        status_before = "启用" if current_active else "停用"
                                        status_after = "启用" if fields["active"] else "停用"
                                        changes.append(f"状态: {status_before} -> {status_after}")
                                    detail = f"修改用户 {username}（ID={user_id}）"
                                    if changes:
                                        detail = detail + "；" + "，".join(changes)
                                    data_manager.add_audit_log(current_user, "USER_UPDATED", detail)
                                    time.sleep(0.3)
                                    st.rerun()
                                else:
                                    st.error("用户信息更新失败")
                with btn_col2:
                    st.caption(f"ID: {user_id}")
    else:
        st.info("当前没有用户记录。")
    
    st.markdown("### 🧹 数据清理")
    
    with st.expander("高级数据清理选项", expanded=False):
        st.warning("⚠️ 这些操作不可逆，请谨慎操作！")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 清理空数据
            if st.button("清理空记录", type="secondary"):
                st.info("清理空记录功能开发中...")
        
        with col2:
            # 重置系统
            if st.button("重置系统数据", type="secondary"):
                st.error("🚨 危险操作！")
                confirm = st.checkbox("我确认要重置所有数据")
                if confirm and st.button("确认重置", type="primary"):
                    # 备份当前数据
                    data_manager.create_backup()
                    
                    # 重置为初始数据
                    initial_data = data_manager.get_initial_data()
                    data_manager.save_data(initial_data)
                    
                    st.success("✅ 系统已重置为初始状态")
                    time.sleep(2)
                    st.rerun()
    
    st.markdown("### 📜 操作审计日志")
    logs = data_manager.get_audit_logs()
    if not logs:
        st.info("当前还没有审计日志记录。")
    else:
        logs_sorted = sorted(logs, key=lambda x: x.get("time", ""), reverse=True)
        user_names = sorted({(l.get("username") or "系统") for l in logs_sorted})
        actions = sorted({l.get("action") for l in logs_sorted})
        col_f1, col_f2, col_f3 = st.columns([2, 2, 1])
        with col_f1:
            user_filter = st.selectbox("按用户筛选", ["全部"] + user_names, index=0)
        with col_f2:
            action_filter = st.selectbox("按操作类型筛选", ["全部"] + actions, index=0)
        with col_f3:
            limit = st.number_input("显示条数", min_value=10, max_value=500, value=200, step=10)
        filtered = []
        for item in logs_sorted:
            name = item.get("username") or "系统"
            action = item.get("action")
            if user_filter != "全部" and name != user_filter:
                continue
            if action_filter != "全部" and action != action_filter:
                continue
            filtered.append(item)
        filtered = filtered[: int(limit)]
        if not filtered:
            st.info("没有满足筛选条件的记录。")
        else:
            df_logs = pd.DataFrame(
                [
                    {
                        "时间": item.get("time"),
                        "用户": item.get("username") or "系统",
                        "角色": item.get("role") or "",
                        "操作": item.get("action"),
                        "详情": item.get("detail"),
                    }
                    for item in filtered
                ]
            )
            st.dataframe(df_logs, use_container_width=True, hide_index=True)
