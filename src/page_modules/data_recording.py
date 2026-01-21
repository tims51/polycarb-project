"""数据记录页面模块 - 完整功能版 (修复版)"""

import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import time
import uuid
from components.paste_fluidity_widget import PasteFluidityWidget

# 常量定义
AGE_OPTIONS = ["1d", "3d", "7d", "14d", "28d", "56d", "90d", "1y"]

def _parse_age_days(age_str):
    """解析龄期字符串为天数"""
    if not age_str: return 0
    if age_str.endswith('d'):
        return int(age_str[:-1])
    elif age_str.endswith('y'):
        return int(age_str[:-1]) * 365
    return 0

def _render_strength_inputs(container, current_strengths=None, key_prefix=""):
    """
    渲染动态强度输入框
    Args:
        container: Streamlit容器 (st 或 st.expander)
        current_strengths: 现有强度字典 {age: value}
        key_prefix: 唯一的key前缀
    Returns:
        dict: 更新后的强度字典 {age: value}
    """
    existing = current_strengths if current_strengths else {}
    
    # 默认选中项：如果有现有数据，则选中现有的key；否则默认7d, 28d
    default_sel = list(existing.keys())
    if not default_sel:
        default_sel = ["7d", "28d"]
    
    # 确保默认选中项在选项列表中
    valid_defaults = [age for age in default_sel if age in AGE_OPTIONS]
    
    # 允许用户选择需要记录的龄期
    selected_ages = container.multiselect(
        "选择测试龄期",
        options=AGE_OPTIONS,
        default=valid_defaults,
        key=f"{key_prefix}_target_ages"
    )
    
    # 按天数排序显示
    selected_ages.sort(key=_parse_age_days)
    
    new_strengths = {}
    if selected_ages:
        # 使用列布局显示输入框
        cols = container.columns(min(len(selected_ages), 4))
        for i, age in enumerate(selected_ages):
            col_idx = i % 4
            val = existing.get(age, 0.0)
            with cols[col_idx]:
                new_val = st.number_input(
                    f"{age}强度 (MPa)",
                    min_value=0.0,
                    value=float(val),
                    step=0.1,
                    key=f"{key_prefix}_strength_{age}"
                )
                new_strengths[age] = new_val
                
    return new_strengths

def render_data_recording(data_manager):
    """渲染数据记录页面"""
    st.header("📝 数据记录")
    
    # 使用标签页组织不同模块
    tab1, tab_mother, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "🧪 合成实验", 
        "💧 母液管理",
        "📊 成品减水剂",
        "🧫 净浆实验", 
        "🏗️ 砂浆实验", 
        "🏢 混凝土实验",
        "🛠️ 数据维护"
    ])
    
    # ==================== 母液管理模块 ====================
    with tab_mother:
        _render_mother_liquor_tab(data_manager)

    # ==================== 合成实验模块 ====================
    with tab1:
        _render_synthesis_experiments_tab(data_manager)
    
    # ==================== 成品减水剂模块 ====================
    with tab3:
        _render_products_tab(data_manager)
    
    # ==================== 净浆实验模块 ====================
    with tab4:
        _render_paste_experiments_tab(data_manager)
    
    # ==================== 砂浆实验模块 ====================
    with tab5:
        _render_mortar_experiments_tab(data_manager)
    
    # ==================== 混凝土实验模块 ====================
    with tab6:
        _render_concrete_experiments_tab(data_manager)

    # ==================== 数据维护模块 ====================
    with tab7:
        _render_data_maintenance_tab(data_manager)



# ==================== 合成实验模块函数 ====================
@st.dialog("批量删除确认")
def batch_delete_synthesis_dialog(selected_records, selected_ids, data_manager):
    st.markdown("#### ⚠️ 确认批量删除")
    st.error("此操作将永久删除选中的合成实验记录，不可恢复！")
    
    for r in selected_records[:30]:
        st.markdown(f"- **{r.get('formula_id', '')}** (ID: {r.get('id')})")
    if len(selected_records) > 30:
        st.caption(f"其余 {len(selected_records) - 30} 条未展开显示")
    
    confirm_text = st.text_input(
        "请输入 '确认删除' 以继续：",
        key="syn_batch_delete_confirm_text",
        placeholder="请输入 '确认删除'",
    )
    
    d1, d2 = st.columns(2)
    with d1:
        if st.button(
            "✅ 确认删除",
            type="primary",
            use_container_width=True,
            disabled=(confirm_text != "确认删除"),
            key="syn_batch_delete_confirm_btn",
        ):
            success_count = 0
            error_count = 0
            for rid in selected_ids:
                ok = data_manager.delete_synthesis_record(rid)
                if ok:
                    success_count += 1
                else:
                    error_count += 1
            
            for rid in selected_ids:
                st.session_state.syn_selected_records[rid] = False
                ck = f"syn_select_{rid}"
                if ck in st.session_state:
                    st.session_state[ck] = False
            
            st.session_state.syn_show_batch_delete_dialog = False
            
            if error_count == 0:
                st.success(f"✅ 成功删除 {success_count} 条记录")
            else:
                st.warning(f"⚠️ 成功删除 {success_count} 条记录，{error_count} 条删除失败")
            time.sleep(1.0)
            st.rerun()
    with d2:
        if st.button(
            "❌ 取消",
            use_container_width=True,
            key="syn_batch_delete_cancel_btn",
        ):
            st.session_state.syn_show_batch_delete_dialog = False
            st.rerun()

def _render_mother_liquor_tab(data_manager):
    """渲染母液管理标签页"""
    st.subheader("💧 母液管理")

    # 1. 顶部：新建母液区域
    with st.expander("➕ 添加新母液", expanded=True):
        source_type = st.radio("来源类型", ["合成实验", "大生产母液", "外来样品"], horizontal=True, key="mother_liquor_source_type")
        
        with st.form("add_mother_liquor_form", clear_on_submit=True):
            if source_type == "合成实验":
                # 获取所有合成实验
                synthesis_experiments = data_manager.get_all_synthesis_records()
                if synthesis_experiments:
                    # 创建选项列表: ID - 配方编号 (日期)
                    exp_options = {f"{exp['id']}: {exp.get('formula_id', '未命名')} ({exp.get('synthesis_date', '')})": exp for exp in synthesis_experiments}
                    selected_exp_key = st.selectbox("选择合成实验*", options=list(exp_options.keys()), key="ml_synthesis_exp")
                    
                    if selected_exp_key:
                        selected_exp = exp_options[selected_exp_key]
                        st.info(f"已选择合成实验: {selected_exp.get('formula_id')} (ID: {selected_exp['id']})")
                        
                        # 自动填充部分信息
                        ml_name = st.text_input("母液名称*", value=f"{selected_exp.get('formula_id')}-母液", key="ml_name_syn")
                        
                        # 其他属性手动录入
                        c1, c2 = st.columns(2)
                        ml_solid = c1.number_input("固含 (%)", min_value=0.0, max_value=100.0, value=40.0, step=0.1, key="ml_solid_syn")
                        ml_ph = c2.number_input("pH值", min_value=0.0, max_value=14.0, value=7.0, step=0.1, key="ml_ph_syn")
                        
                        c3, c4 = st.columns(2)
                        ml_density = c3.number_input("密度 (g/cm³)", min_value=0.0, value=1.05, step=0.01, key="ml_density_syn")
                        ml_color = c4.text_input("颜色", value="无色透明", key="ml_color_syn")

                        ml_desc = st.text_area("备注", height=60, key="ml_desc_syn")

                        if st.form_submit_button("保存母液信息", type="primary"):
                            if ml_name:
                                new_ml = {
                                    "name": ml_name,
                                    "source_type": "synthesis",
                                    "source_id": selected_exp['id'],
                                    "solid_content": ml_solid,
                                    "ph_value": ml_ph,
                                    "density": ml_density,
                                    "color": ml_color,
                                    "description": ml_desc,
                                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
                                }
                                # 保存逻辑
                                if hasattr(data_manager, 'add_mother_liquor'):
                                    if data_manager.add_mother_liquor(new_ml):
                                        st.success("母液添加成功！")
                                        time.sleep(0.5)
                                        st.rerun()
                                    else:
                                        st.error("添加失败")
                                else:
                                    st.error("DataManager 尚未实现 add_mother_liquor 方法")
                            else:
                                st.error("请填写母液名称")
                else:
                    st.warning("暂无合成实验记录，请先添加合成实验。")
                    st.form_submit_button("暂无法保存", disabled=True)

            elif source_type == "大生产母液":
                c1, c2 = st.columns(2)
                ml_name = c1.text_input("母液名称*", key="ml_name_prod")
                batch_number = c2.text_input("生产批号*", key="ml_batch_prod")
                
                c3, c4 = st.columns(2)
                production_date = c3.date_input("生产日期", value=datetime.now(), key="ml_date_prod")
                production_mode = c4.radio("生产方式", ["工厂自产", "代工生产"], horizontal=True, key="ml_mode_prod")
                
                manufacturer = ""
                if production_mode == "代工生产":
                    manufacturer = st.text_input("厂家名称*", key="ml_manufacturer_prod")
                
                st.markdown("---")
                st.caption("母液指标")
                
                i1, i2, i3, i4 = st.columns(4)
                ml_solid = i1.number_input("固含 (%)", min_value=0.0, max_value=100.0, value=40.0, step=0.1, key="ml_solid_prod")
                ml_ph = i2.number_input("pH值", min_value=0.0, max_value=14.0, value=7.0, step=0.1, key="ml_ph_prod")
                ml_density = i3.number_input("密度 (g/cm³)", min_value=0.0, value=1.05, step=0.01, key="ml_density_prod")
                ml_color = i4.text_input("颜色", value="无色透明", key="ml_color_prod")
                
                ml_desc = st.text_area("备注", height=60, key="ml_desc_prod")
                
                if st.form_submit_button("保存母液信息", type="primary"):
                    if ml_name and batch_number:
                        if production_mode == "代工生产" and not manufacturer:
                            st.error("请填写代工厂家名称")
                        else:
                            new_ml = {
                                "name": ml_name,
                                "source_type": "production",
                                "batch_number": batch_number,
                                "production_date": production_date.strftime("%Y-%m-%d"),
                                "production_mode": production_mode,
                                "manufacturer": manufacturer,
                                "solid_content": ml_solid,
                                "ph_value": ml_ph,
                                "density": ml_density,
                                "color": ml_color,
                                "description": ml_desc,
                                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
                            }
                            # 保存逻辑
                            if hasattr(data_manager, 'add_mother_liquor'):
                                if data_manager.add_mother_liquor(new_ml):
                                    st.success("母液添加成功！")
                                    time.sleep(0.5)
                                    st.rerun()
                                else:
                                    st.error("添加失败")
                            else:
                                st.error("DataManager 尚未实现 add_mother_liquor 方法")
                    else:
                        st.error("请填写母液名称和批号")

            else: # 外来样品
                c1, c2 = st.columns(2)
                ml_name = c1.text_input("母液名称*", key="ml_name_ext")
                ml_type = c2.text_input("母液类型", placeholder="e.g. 聚醚类/聚酯类", key="ml_type_ext")
                
                c3, c4, c5, c6 = st.columns(4)
                ml_solid = c3.number_input("固含 (%)", min_value=0.0, max_value=100.0, value=40.0, step=0.1, key="ml_solid_ext")
                ml_ph = c4.number_input("pH值", min_value=0.0, max_value=14.0, value=7.0, step=0.1, key="ml_ph_ext")
                ml_density = c5.number_input("密度 (g/cm³)", min_value=0.0, value=1.05, step=0.01, key="ml_density_ext")
                ml_color = c6.text_input("颜色", value="无色透明", key="ml_color_ext")
                
                ml_desc = st.text_area("备注", height=60, key="ml_desc_ext")
                
                if st.form_submit_button("保存母液信息", type="primary"):
                    if ml_name:
                        new_ml = {
                            "name": ml_name,
                            "source_type": "external",
                            "mother_liquor_type": ml_type,
                            "solid_content": ml_solid,
                            "ph_value": ml_ph,
                            "density": ml_density,
                            "color": ml_color,
                            "description": ml_desc,
                            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
                        }
                         # 保存逻辑
                        if hasattr(data_manager, 'add_mother_liquor'):
                            if data_manager.add_mother_liquor(new_ml):
                                st.success("母液添加成功！")
                                time.sleep(0.5)
                                st.rerun()
                            else:
                                st.error("添加失败")
                        else:
                            st.error("DataManager 尚未实现 add_mother_liquor 方法")
                    else:
                        st.error("请填写母液名称")

    # 2. 列表显示区域
    st.divider()
    st.markdown("#### 📋 母液列表")
    
    # 搜索框
    search_term = st.text_input("🔍 搜索母液 (名称/来源)", key="ml_search")
    
    # 获取母液列表 (需要 DataManager 支持 get_all_mother_liquors)
    mother_liquors = []
    if hasattr(data_manager, 'get_all_mother_liquors'):
        mother_liquors = data_manager.get_all_mother_liquors()
    
    # 过滤
    if search_term:
        mother_liquors = [ml for ml in mother_liquors if search_term.lower() in ml.get('name', '').lower() or search_term.lower() in ml.get('source_type', '').lower()]

    if mother_liquors:
        # 表头
        h1, h2, h3, h4, h5, h6 = st.columns([2, 1.5, 1, 1, 1, 1.5])
        h1.markdown("**母液名称**")
        h2.markdown("**来源**")
        h3.markdown("**固含(%)**")
        h4.markdown("**pH**")
        h5.markdown("**密度**")
        h6.markdown("**操作**")
        st.divider()

        for idx, ml in enumerate(mother_liquors):
            with st.container():
                c1, c2, c3, c4, c5, c6 = st.columns([2, 1.5, 1, 1, 1, 1.5])
                c1.write(f"**{ml.get('name')}**")
                
                source_display = "外来样品"
                if ml.get('source_type') == 'synthesis':
                    source_display = "合成实验"
                    if ml.get('source_id'):
                        source_display += f" (ID:{ml.get('source_id')})"
                elif ml.get('source_type') == 'external':
                    source_display = f"外来 ({ml.get('mother_liquor_type', '-')})"
                elif ml.get('source_type') == 'production':
                    mode = ml.get('production_mode', '未知')
                    batch = ml.get('batch_number', '')
                    source_display = f"大生产 ({mode})"
                    if batch:
                        source_display += f"\n批号: {batch}"
                c2.write(source_display)
                
                c3.write(f"{ml.get('solid_content', '-')}")
                c4.write(f"{ml.get('ph_value', '-')}")
                c5.write(f"{ml.get('density', '-')}")
                
                # 操作列
                with c6:
                    btn_col1, btn_col2, btn_col3 = st.columns(3)
                    with btn_col1:
                         # 详情按钮
                         if st.button("📄", key=f"ml_detail_{idx}", help="查看详情"):
                             st.session_state[f"show_ml_detail_{ml.get('id')}"] = not st.session_state.get(f"show_ml_detail_{ml.get('id')}", False)
                    with btn_col2:
                         if st.button("✏️", key=f"ml_edit_{idx}", help="编辑"):
                             st.session_state.ml_edit_id = ml.get('id')
                             st.rerun()
                    with btn_col3:
                         if st.button("🗑️", key=f"ml_del_{idx}", help="删除"):
                             if hasattr(data_manager, 'delete_mother_liquor'):
                                 if data_manager.delete_mother_liquor(ml.get('id')):
                                     st.success("已删除")
                                     time.sleep(0.5)
                                     st.rerun()
                
                # 详情展开区域
                if st.session_state.get(f"show_ml_detail_{ml.get('id')}", False):
                    with st.container():
                        st.info(f"📝 备注: {ml.get('description', '无')}")
                        
                        # 显示大生产信息
                        if ml.get('source_type') == 'production':
                            st.markdown("###### 🏭 生产信息")
                            prod_info_col1, prod_info_col2 = st.columns(2)
                            with prod_info_col1:
                                st.write(f"**批号:** {ml.get('batch_number', '-')}")
                                st.write(f"**生产日期:** {ml.get('production_date', '-')}")
                            with prod_info_col2:
                                st.write(f"**生产方式:** {ml.get('production_mode', '-')}")
                                if ml.get('production_mode') == '代工生产':
                                    st.write(f"**厂家:** {ml.get('manufacturer', '-')}")

                        if ml.get('source_type') == 'synthesis' and ml.get('source_id'):
                             # 显示关联的合成实验配方
                             syn_exp = data_manager.get_synthesis_experiment(ml.get('source_id'))
                             if syn_exp:
                                st.markdown("###### 🧬 关联配方信息")
                                st.caption(f"配方编号: {syn_exp.get('formula_id')} | 合成时间: {syn_exp.get('synthesis_date')}")
                                
                                # 提取有数据的原料
                                recipe_data = []
                                # 遍历四个部分的物料
                                for section_name, section_key in [("反应釜", "reactor_materials"), ("A料", "a_materials"), ("B料", "b_materials"), ("助剂", "additive_materials")]:
                                    items = syn_exp.get(section_key, [])
                                    if items:
                                        for item in items:
                                            # 只显示有名称且用量大于0的原料
                                            if item.get("material_name") and item.get("material_name") != "请选择..." and float(item.get("amount", 0) or 0) > 0:
                                                row = {
                                                    "部位": section_name,
                                                    "原料名称": item.get("material_name"),
                                                    "用量 (g)": item.get("amount")
                                                }
                                                # 如果是助剂，显示额外信息
                                                if section_key == "additive_materials":
                                                    info = []
                                                    if item.get("time_point"):
                                                        info.append(f"时间:{item.get('time_point')}")
                                                    if item.get("stir_time"):
                                                        info.append(f"搅拌:{item.get('stir_time')}min")
                                                    if info:
                                                        row["备注"] = "; ".join(info)
                                                else:
                                                    row["备注"] = ""
                                                
                                                recipe_data.append(row)
                                
                                if recipe_data:
                                    st.dataframe(recipe_data, use_container_width=True, hide_index=True)
                                else:
                                    st.caption("无有效配方数据")
                        else:
                            st.warning("关联的合成实验已不存在")
                        
                        # 编辑表单 (如果处于编辑模式)
                        if st.session_state.get('ml_edit_id') == ml.get('id'):
                            with st.form(f"edit_ml_form_{ml.get('id')}"):
                                st.markdown("#### 编辑母液信息")
                                e_name = st.text_input("名称", value=ml.get('name'), key=f"e_ml_name_{ml.get('id')}")
                                ec1, ec2, ec3, ec4 = st.columns(4)
                                e_solid = ec1.number_input("固含", value=float(ml.get('solid_content', 0)), key=f"e_ml_solid_{ml.get('id')}")
                                e_ph = ec2.number_input("pH", value=float(ml.get('ph_value', 7)), key=f"e_ml_ph_{ml.get('id')}")
                                e_density = ec3.number_input("密度", value=float(ml.get('density', 1)), key=f"e_ml_den_{ml.get('id')}")
                                e_color = ec4.text_input("颜色", value=ml.get('color', ''), key=f"e_ml_col_{ml.get('id')}")
                                e_desc = st.text_area("备注", value=ml.get('description', ''), key=f"e_ml_desc_{ml.get('id')}")
                                
                                if st.form_submit_button("💾 保存修改"):
                                    updates = {
                                        "name": e_name,
                                        "solid_content": e_solid,
                                        "ph_value": e_ph,
                                        "density": e_density,
                                        "color": e_color,
                                        "description": e_desc
                                    }
                                    if hasattr(data_manager, 'update_mother_liquor'):
                                        if data_manager.update_mother_liquor(ml.get('id'), updates):
                                            st.success("更新成功")
                                            st.session_state.ml_edit_id = None
                                            time.sleep(0.5)
                                            st.rerun()

                st.divider()
    else:
        st.info("暂无母液数据")


def _render_synthesis_experiments_tab(data_manager):
    """渲染合成实验标签页"""
    st.subheader("🧪 合成实验记录")
    
    # 获取数据
    synthesis_records = data_manager.get_all_synthesis_records()
    experiments = data_manager.get_all_experiments()
    raw_materials = data_manager.get_all_raw_materials()
    
    # 获取实验项目选项
    experiment_options = {f"{e['id']}: {e['name']}": e['id'] for e in experiments} if experiments else {}
    
    # 获取原材料选项
    raw_material_names = []
    if raw_materials:
        for m in raw_materials:
            name = m['name']
            extras = []
            if m.get('abbreviation'):
                extras.append(m['abbreviation'])
            if m.get('manufacturer'):
                extras.append(m['manufacturer'])
            
            if extras:
                name += f" ({' | '.join(extras)})"
            raw_material_names.append(name)
    
    # 添加新合成实验表单 - 使用唯一ID
    form_id = "syn_add"
    with st.expander("➕ 新增合成实验", expanded=True):
        with st.form(f"synthesis_experiment_form_{form_id}", clear_on_submit=True):
            # ==================== 第一部分：基础信息 ====================
            st.markdown("### 📝 第一部分：基础信息")
            base_col1, base_col2 = st.columns(2)
            
            with base_col1:
                # 关联实验项目
                if experiment_options:
                    selected_exp_key = st.selectbox(
                        "关联实验项目*",
                        options=["请选择..."] + list(experiment_options.keys()),
                        key=f"syn_project_select_{form_id}"
                    )
                    experiment_id = experiment_options.get(selected_exp_key) if selected_exp_key != "请选择..." else None
                else:
                    st.warning("请先在实验管理模块创建实验")
                    experiment_id = None
                
                # 配方编号
                formula_id = st.text_input("配方编号*", 
                                         placeholder="例如: PC-001-202401",
                                         key=f"syn_formula_id_{form_id}")
                
            with base_col2:
                # 设计固含
                design_solid_content = st.number_input("设计固含 (%)*", 
                                                      min_value=0.0, 
                                                      max_value=100.0,
                                                      value=40.0,
                                                      step=0.1,
                                                      help="设计的固含量百分比",
                                                      key=f"syn_design_solid_{form_id}")
                
                # 合成日期
                synthesis_date = st.date_input("合成日期", 
                                              datetime.now(),
                                              key=f"syn_date_{form_id}")
                
                # 操作人
                operator = st.text_input("操作人*", 
                                        placeholder="请输入操作人员姓名",
                                        key=f"syn_operator_{form_id}")
            
            st.divider()
            
            # ==================== 第二部分：反应釜物料 ====================
            st.markdown("### ⚗️ 第二部分：反应釜物料")
            st.info("请从原材料库中选择以下物料并填写用量（单位: g）")
            
            # 反应釜物料 - 使用表格布局
            reactor_cols = st.columns(7)
            reactor_materials = []
            
            # 定义反应釜物料列表
            reactor_items = [
                {"name": "单体1", "key": "monomer1"},
                {"name": "单体2", "key": "monomer2"},
                {"name": "单体3", "key": "monomer3"},
                {"name": "单体4", "key": "monomer4"},
                {"name": "引发剂", "key": "initiator"},
                {"name": "链转移剂1", "key": "chain_transfer1"},
                {"name": "水", "key": "water_reactor"}
            ]
            
            reactor_amounts = []
            for i, item in enumerate(reactor_items):
                with reactor_cols[i]:
                    st.markdown(f"**{item['name']}**")
                    
                    # 物料选择
                    material_options = ["请选择..."] + raw_material_names
                    selected_material = st.selectbox(
                        f"选择{item['name']}",
                        options=material_options,
                        key=f"syn_reactor_{item['key']}_select_{i}_{form_id}",
                        help="输入名称搜索原材料",
                        index=0,
                        label_visibility="collapsed"
                    )
                    
                    # 用量输入
                    amount = st.number_input(
                        f"用量 (g)",
                        min_value=0.0,
                        step=0.1,
                        value=0.0,
                        key=f"syn_reactor_{item['key']}_amount_{i}_{form_id}",
                        label_visibility="collapsed"
                    )
                    
                    if selected_material and selected_material != "请选择..." and amount > 0:
                        reactor_materials.append({
                            "name": item["name"],
                            "material_name": selected_material,
                            "amount": amount
                        })
                    reactor_amounts.append(amount)
            
            # 显示反应釜物料总用量 - 实时计算
            total_reactor = sum(reactor_amounts)
            st.caption(f"反应釜物料总用量: **{total_reactor:.2f} g**")
            
            st.divider()
            
            # ==================== 第三部分：A料 ====================
            st.markdown("### 🔴 第三部分：A料")
            st.info("A料组成及滴加参数")
            
            # A料物料
            a_cols = st.columns(6)
            a_materials = []
            
            # 定义A料物料列表
            a_items = [
                {"name": "单体a", "key": "monomer_a"},
                {"name": "单体b", "key": "monomer_b"},
                {"name": "单体c", "key": "monomer_c"},
                {"name": "单体d", "key": "monomer_d"},
                {"name": "水", "key": "water_a"},
                {"name": "其他", "key": "other_a"}
            ]
            
            a_amounts = []
            for i, item in enumerate(a_items):
                with a_cols[i]:
                    st.markdown(f"**{item['name']}**")
                    
                    # 物料选择
                    material_options = ["请选择..."] + raw_material_names
                    selected_material = st.selectbox(
                        f"选择{item['name']}",
                        options=material_options,
                        key=f"syn_a_{item['key']}_select_{i}_{form_id}",
                        help="输入名称搜索原材料",
                        index=0,
                        label_visibility="collapsed"
                    )
                    
                    # 用量输入
                    amount = st.number_input(
                        f"用量 (g)",
                        min_value=0.0,
                        step=0.1,
                        value=0.0,
                        key=f"syn_a_{item['key']}_amount_{i}_{form_id}",
                        label_visibility="collapsed"
                    )
                    
                    if selected_material and selected_material != "请选择..." and amount > 0:
                        a_materials.append({
                            "name": item["name"],
                            "material_name": selected_material,
                            "amount": amount
                        })
                    a_amounts.append(amount)
            
            # A料滴加参数
            st.markdown("**滴加参数**")
            a_drip_col1, a_drip_col2, a_drip_col3 = st.columns(3)
            
            with a_drip_col1:
                # A料总量（自动计算）
                a_total_amount = sum(a_amounts)
                st.metric("A料总用量", f"{a_total_amount:.2f} g")
            
            with a_drip_col2:
                # 滴加时间
                a_drip_time = st.number_input(
                    "滴加时间 (分钟)*",
                    min_value=0.0,
                    value=120.0,
                    step=1.0,
                    key=f"syn_a_drip_time_{form_id}"
                )
            
            with a_drip_col3:
                # 滴加速度（自动计算）
                a_drip_speed = 0.0
                if a_drip_time > 0 and a_total_amount > 0:
                    a_drip_speed = a_total_amount / a_drip_time
                st.metric("滴加速度", f"{a_drip_speed:.2f} g/min")
            
            st.divider()
            
            # ==================== 第四部分：B料 ====================
            st.markdown("### 🔵 第四部分：B料")
            st.info("B料组成及滴加参数")
            
            # B料物料
            b_cols = st.columns(5)
            b_materials = []
            
            # 定义B料物料列表
            b_items = [
                {"name": "引发剂2", "key": "initiator2"},
                {"name": "链转移剂2", "key": "chain_transfer2"},
                {"name": "水", "key": "water_b"},
                {"name": "其他1", "key": "other_b1"},
                {"name": "其他2", "key": "other_b2"}
            ]
            
            b_amounts = []
            for i, item in enumerate(b_items):
                with b_cols[i]:
                    st.markdown(f"**{item['name']}**")
                    
                    # 物料选择
                    material_options = ["请选择..."] + raw_material_names
                    selected_material = st.selectbox(
                        f"选择{item['name']}",
                        options=material_options,
                        key=f"syn_b_{item['key']}_select_{i}_{form_id}",
                        help="输入名称搜索原材料",
                        index=0,
                        label_visibility="collapsed"
                    )
                    
                    # 用量输入
                    amount = st.number_input(
                        f"用量 (g)",
                        min_value=0.0,
                        step=0.1,
                        value=0.0,
                        key=f"syn_b_{item['key']}_amount_{i}_{form_id}",
                        label_visibility="collapsed"
                    )
                    
                    if selected_material and selected_material != "请选择..." and amount > 0:
                        b_materials.append({
                            "name": item["name"],
                            "material_name": selected_material,
                            "amount": amount
                        })
                    b_amounts.append(amount)
            
            # B料滴加参数
            st.markdown("**滴加参数**")
            b_drip_col1, b_drip_col2, b_drip_col3 = st.columns(3)
            
            with b_drip_col1:
                # B料总量（自动计算）
                b_total_amount = sum(b_amounts)
                st.metric("B料总用量", f"{b_total_amount:.2f} g")
            
            with b_drip_col2:
                # 滴加时间
                b_drip_time = st.number_input(
                    "滴加时间 (分钟)*",
                    min_value=0.0,
                    value=60.0,
                    step=1.0,
                    key=f"syn_b_drip_time_{form_id}"
                )
            
            with b_drip_col3:
                # 滴加速度（自动计算）
                b_drip_speed = 0.0
                if b_drip_time > 0 and b_total_amount > 0:
                    b_drip_speed = b_total_amount / b_drip_time
                st.metric("滴加速度", f"{b_drip_speed:.2f} g/min")
            
            st.divider()
            
            # ==================== 第五部分：助剂添加 ====================
            st.markdown("### 🧪 第五部分：助剂添加")
            st.info("添加额外的功能性助剂（可选）")
            
            additive_cols = st.columns(3)
            additive_materials = []
            
            # 定义3个助剂位
            for i in range(3):
                with additive_cols[i]:
                    st.markdown(f"**助剂 {i+1}**")
                    
                    # 助剂选择
                    additive_options = ["请选择..."] + raw_material_names
                    selected_additive = st.selectbox(
                        f"选择助剂",
                        options=additive_options,
                        key=f"syn_additive_select_{i}_{form_id}",
                        index=0,
                        label_visibility="collapsed"
                    )
                    
                    # 用量
                    add_amount = st.number_input(
                        f"用量 (g)",
                        min_value=0.0,
                        step=0.1,
                        value=0.0,
                        key=f"syn_additive_amount_{i}_{form_id}",
                    )
                    
                    # 添加时间点
                    add_time_point = st.text_input(
                        "添加时间点",
                        placeholder="例如: 保温结束前30分钟",
                        key=f"syn_additive_time_{i}_{form_id}"
                    )
                    
                    # 搅拌时长
                    stir_time = st.number_input(
                        "添加后搅拌时长 (分钟)",
                        min_value=0.0,
                        step=1.0,
                        value=0.0,
                        key=f"syn_additive_stir_{i}_{form_id}"
                    )
                    
                    if selected_additive and selected_additive != "请选择..." and add_amount > 0:
                        additive_materials.append({
                            "name": f"助剂{i+1}",
                            "material_name": selected_additive,
                            "amount": add_amount,
                            "time_point": add_time_point,
                            "stir_time": stir_time
                        })
            
            st.divider()
            
            # ==================== 第六部分：反应参数 ====================
            st.markdown("### 🔥 第六部分：反应参数")
            
            # 反应参数
            st.markdown("**温度控制**")
            reaction_col1, reaction_col2, reaction_col3 = st.columns(3)
            
            with reaction_col1:
                # 起始温度
                start_temp = st.number_input(
                    "起始温度 (°C)*",
                    min_value=0.0,
                    max_value=100.0,
                    value=20.0,
                    step=0.5,
                    key=f"syn_start_temp_{form_id}"
                )
            
            with reaction_col2:
                # 最高温度
                max_temp = st.number_input(
                    "最高温度 (°C)*",
                    min_value=0.0,
                    max_value=200.0,
                    value=80.0,
                    step=0.5,
                    key=f"syn_max_temp_{form_id}"
                )
            
            with reaction_col3:
                # 保温时间
                holding_time = st.number_input(
                    "保温时间 (小时)*",
                    min_value=0.0,
                    max_value=24.0,
                    value=2.0,
                    step=0.5,
                    key=f"syn_holding_time_{form_id}"
                )
            
            # 工艺备注
            process_notes = st.text_area(
                "实验工艺备注",
                height=150,
                placeholder="请详细记录实验过程中的观察、调整、异常情况等工艺信息...",
                key=f"syn_process_notes_{form_id}"
            )
            
            # 提交按钮
            submitted = st.form_submit_button("💾 保存合成实验记录", type="primary")
            
            if submitted:
                # 验证必填项
                validation_errors = []
                
                if not experiment_id:
                    validation_errors.append("请选择关联实验项目")
                
                if not formula_id:
                    validation_errors.append("请输入配方编号")
                
                if not design_solid_content:
                    validation_errors.append("请输入设计固含")
                
                if not operator:
                    validation_errors.append("请输入操作人")
                
                if a_drip_time <= 0:
                    validation_errors.append("请输入有效的A料滴加时间")
                
                if b_drip_time <= 0:
                    validation_errors.append("请输入有效的B料滴加时间")
                
                if start_temp <= 0:
                    validation_errors.append("请输入有效的起始温度")
                
                if max_temp <= 0 or max_temp < start_temp:
                    validation_errors.append("最高温度必须大于起始温度")
                
                if holding_time <= 0:
                    validation_errors.append("请输入有效的保温时间")
                
                # 检查是否选择了至少一种物料
                if not reactor_materials and not a_materials and not b_materials:
                    validation_errors.append("请至少添加一种物料")
                
                if validation_errors:
                    for error in validation_errors:
                        st.error(error)
                else:
                    # 构建新的合成实验记录
                    new_record = {
                        "formula_id": formula_id,
                        "experiment_id": experiment_id,
                        "design_solid_content": design_solid_content,
                        "operator": operator,
                        "synthesis_date": synthesis_date.strftime("%Y-%m-%d"),
                        
                        # 反应釜物料
                        "reactor_materials": reactor_materials,
                        "reactor_total_amount": total_reactor,
                        
                        # A料
                        "a_materials": a_materials,
                        "a_total_amount": a_total_amount,
                        "a_drip_time": a_drip_time,
                        "a_drip_speed": a_drip_speed,
                        
                        # B料
                        "b_materials": b_materials,
                        "b_total_amount": b_total_amount,
                        "b_drip_time": b_drip_time,
                        "b_drip_speed": b_drip_speed,
                        
                        # 助剂
                        "additive_materials": additive_materials,
                        
                        # 反应参数
                        "start_temp": start_temp,
                        "max_temp": max_temp,
                        "holding_time": holding_time,
                        
                        # 备注
                        "process_notes": process_notes,
                        
                        # 元数据
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "last_modified": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    # 保存到数据管理器
                    if data_manager.add_synthesis_record(new_record):
                        st.success(f"✅ 合成实验记录 '{formula_id}' 保存成功！")
                        
                        # 显示数据摘要
                        with st.expander("📋 查看数据摘要", expanded=False):
                            summary_col1, summary_col2 = st.columns(2)
                            
                            with summary_col1:
                                st.markdown("**基础信息**")
                                st.write(f"**配方编号:** {formula_id}")
                                st.write(f"**操作人:** {operator}")
                                st.write(f"**设计固含:** {design_solid_content}%")
                                st.write(f"**合成日期:** {synthesis_date.strftime('%Y-%m-%d')}")
                            
                            with summary_col2:
                                st.markdown("**物料总览**")
                                st.write(f"**反应釜总用量:** {total_reactor:.2f} g")
                                st.write(f"**A料总用量:** {a_total_amount:.2f} g")
                                st.write(f"**B料总用量:** {b_total_amount:.2f} g")
                                total_materials = total_reactor + a_total_amount + b_total_amount
                                st.write(f"**总物料量:** {total_materials:.2f} g")
                        
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("保存失败，请重试")
    
    # ==================== 合成实验数据查看 ====================
    st.divider()
    st.subheader("📊 合成实验数据查看")
    
    if synthesis_records:
        # 搜索和过滤功能
        search_col1, search_col2, search_col3 = st.columns([2, 2, 1])
        with search_col1:
            search_formula = st.text_input("搜索配方编号", 
                                         placeholder="输入配方编号",
                                         key="syn_search_formula")
        with search_col2:
            search_operator = st.text_input("搜索操作人", 
                                          placeholder="输入操作人姓名",
                                          key="syn_search_operator")
        with search_col3:
            items_per_page = st.selectbox("每页显示", [10, 20, 50], index=1, key="syn_page_size")
        
        with st.expander("高级筛选", expanded=False):
            f_col1, f_col2 = st.columns(2)
            with f_col1:
                exp_id_options = ["全部"] + [f"{e.get('id')}: {e.get('name', '')}" for e in experiments]
                exp_id_selected = st.selectbox("关联实验项目", options=exp_id_options, key="syn_filter_experiment")
            with f_col2:
                date_range = st.date_input(
                    "合成日期范围",
                    value=(datetime.now().date() - timedelta(days=30), datetime.now().date()),
                    key="syn_filter_date_range"
                )
        
        current_query_signature = (
            search_formula,
            search_operator,
            items_per_page,
            st.session_state.get("syn_filter_experiment"),
            tuple(st.session_state.get("syn_filter_date_range", ())),
        )
        if st.session_state.get("syn_query_signature") != current_query_signature:
            st.session_state.syn_query_signature = current_query_signature
            st.session_state.syn_page = 1
            st.session_state.syn_selected_records = {}
        
        # 过滤数据
        filtered_records = synthesis_records
        if search_formula:
            filtered_records = [
                r for r in filtered_records
                if search_formula.lower() in r.get("formula_id", "").lower()
            ]
        if search_operator:
            filtered_records = [
                r for r in filtered_records
                if search_operator.lower() in r.get("operator", "").lower()
            ]
        
        exp_id_selected = st.session_state.get("syn_filter_experiment", "全部")
        if exp_id_selected != "全部":
            try:
                exp_id_value = int(str(exp_id_selected).split(":", 1)[0].strip())
            except Exception:
                exp_id_value = None
            if exp_id_value is not None:
                filtered_records = [r for r in filtered_records if r.get("experiment_id") == exp_id_value]
        
        date_range = st.session_state.get("syn_filter_date_range")
        if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
            start_date, end_date = date_range
            
            def _parse_date(value):
                if not value:
                    return None
                if hasattr(value, "year"):
                    return value
                try:
                    return datetime.strptime(str(value), "%Y-%m-%d").date()
                except Exception:
                    return None
            
            filtered_records = [
                r for r in filtered_records
                if (d := _parse_date(r.get("synthesis_date"))) is not None and start_date <= d <= end_date
            ]
        
        # 分页状态管理
        if "syn_page" not in st.session_state:
            st.session_state.syn_page = 1
        if "syn_selected_records" not in st.session_state:
            st.session_state.syn_selected_records = {}
        if "syn_show_batch_delete_dialog" not in st.session_state:
            st.session_state.syn_show_batch_delete_dialog = False
        
        total_pages = max(1, (len(filtered_records) + items_per_page - 1) // items_per_page)
        
        # 确保当前页码有效
        if st.session_state.syn_page > total_pages:
            st.session_state.syn_page = total_pages
            
        start_idx = (st.session_state.syn_page - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, len(filtered_records))
        current_records = filtered_records[start_idx:end_idx]
        
        # 显示表格
        if current_records:
            def _syn_update_selection(record_id, checkbox_key):
                st.session_state.syn_selected_records[record_id] = st.session_state.get(checkbox_key, False)
            
            selected_ids = [
                rid for rid, selected in st.session_state.syn_selected_records.items()
                if selected
            ]
            
            tool_col1, tool_col2, tool_col3, tool_col4 = st.columns([1, 1, 1.4, 2.6])
            with tool_col1:
                if st.button("全选本页", key="syn_select_all_page", type="secondary", use_container_width=True):
                    for r in current_records:
                        rid = r.get("id")
                        if rid is not None:
                            st.session_state.syn_selected_records[rid] = True
                            ck = f"syn_select_{rid}"
                            st.session_state[ck] = True
                    st.rerun()
            with tool_col2:
                if st.button("取消本页", key="syn_deselect_all_page", type="secondary", use_container_width=True):
                    for r in current_records:
                        rid = r.get("id")
                        if rid is not None:
                            st.session_state.syn_selected_records[rid] = False
                            ck = f"syn_select_{rid}"
                            st.session_state[ck] = False
                    st.rerun()
            with tool_col3:
                if st.button(
                    "🗑️ 删除选中",
                    key="syn_batch_delete_btn",
                    type="primary",
                    use_container_width=True,
                    disabled=(len(selected_ids) == 0),
                ):
                    st.session_state.syn_show_batch_delete_dialog = True
                    st.rerun()
            with tool_col4:
                st.caption(f"已选择 {len(selected_ids)} 条记录")
            
            if st.session_state.syn_show_batch_delete_dialog:
                selected_ids = [
                    rid for rid, selected in st.session_state.syn_selected_records.items()
                    if selected
                ]
                selected_records = [r for r in filtered_records if r.get("id") in selected_ids]
                
                batch_delete_synthesis_dialog(selected_records, selected_ids, data_manager)

            # 表头
            header_cols = st.columns([1, 1, 2, 2, 2, 2, 2])
            headers = ["选择", "序号", "配方编号", "操作人", "合成日期", "关联实验", "操作"]
            
            for i, header in enumerate(headers):
                header_cols[i].markdown(f"**{header}**")
            
            st.divider()
            
            # 数据行
            for idx, record in enumerate(current_records, start=start_idx+1):
                with st.container():
                    row_cols = st.columns([1, 1, 2, 2, 2, 2, 2])
                    
                    record_id = record.get("id")
                    record_key = record_id if record_id is not None else f"idx_{idx}"
                    checkbox_key = f"syn_select_{record_id}"
                    with row_cols[0]:
                        current_selected = bool(st.session_state.syn_selected_records.get(record_id, False))
                        if checkbox_key not in st.session_state:
                            st.session_state[checkbox_key] = current_selected
                        is_selected = st.checkbox(
                            "",
                            value=st.session_state[checkbox_key],
                            key=checkbox_key,
                            disabled=(record_id is None),
                            label_visibility="collapsed",
                            on_change=lambda rid=record_id, ck=checkbox_key: _syn_update_selection(rid, ck),
                        )
                        if record_id is not None:
                            st.session_state.syn_selected_records[record_id] = bool(is_selected)
                    
                    with row_cols[1]:
                        st.write(idx)
                    
                    with row_cols[2]:
                        formula = record.get("formula_id", "")
                        st.write(f"`{formula}`")
                    
                    with row_cols[3]:
                        st.write(record.get("operator", ""))
                    
                    with row_cols[4]:
                        st.write(record.get("synthesis_date", ""))
                    
                    with row_cols[5]:
                        exp_name = ""
                        exp_id_value = record.get("experiment_id")
                        if exp_id_value is not None:
                            exp = next((e for e in experiments if e.get("id") == exp_id_value), None)
                            if exp:
                                exp_name = f"{exp.get('id')}: {exp.get('name', '')}"
                            else:
                                exp_name = str(exp_id_value)
                        st.write(exp_name)
                    
                    with row_cols[6]:
                        # 查看详情按钮
                        view_key = f"syn_view_{record_key}"
                        if st.button("📋 详情", key=view_key, disabled=record_id is None):
                            detail_key = f"syn_show_detail_{record_id}"
                            if detail_key not in st.session_state:
                                st.session_state[detail_key] = False
                            st.session_state[detail_key] = not st.session_state[detail_key]
                            st.rerun()
                    
                    # 详细信息（可折叠）
                    detail_key = f"syn_show_detail_{record_id}" if record_id is not None else None
                    if detail_key and st.session_state.get(detail_key, False):
                        with st.expander(f"📋 配方 {formula} 详细信息", expanded=True):
                            # 生成 BOM 按钮
                            if st.button("🏭 生成 BOM (草稿)", key=f"gen_bom_syn_{record['id']}"):
                                bom_data = {
                                    "bom_code": f"BOM-{record.get('formula_id', 'Unknown')}",
                                    "bom_name": f"From {record.get('formula_id')}",
                                    "bom_type": "母液", # 使用中文
                                    "status": "draft"
                                }
                                new_bom_id = data_manager.add_bom(bom_data)
                                if new_bom_id:
                                    # 汇总物料
                                    lines = []
                                    # Reactor
                                    for m in record.get('reactor_materials', []):
                                         lines.append({"item_type": "raw_material", "item_name": m.get('material_name'), "qty": float(m.get('amount', 0)), "phase": "reactor"})
                                    # A
                                    for m in record.get('a_materials', []):
                                         lines.append({"item_type": "raw_material", "item_name": m.get('material_name'), "qty": float(m.get('amount', 0)), "phase": "A"})
                                    # B
                                    for m in record.get('b_materials', []):
                                         lines.append({"item_type": "raw_material", "item_name": m.get('material_name'), "qty": float(m.get('amount', 0)), "phase": "B"})
                                    
                                    total_yield = float(record.get('reactor_total_amount', 0)) + float(record.get('a_total_amount', 0)) + float(record.get('b_total_amount', 0))
                                    
                                    user = st.session_state.get("current_user", None)
                                    ver_data = {
                                        "bom_id": new_bom_id,
                                        "version": "V1", 
                                        "effective_from": datetime.now().strftime("%Y-%m-%d"),
                                        "yield_base": total_yield if total_yield > 0 else 1000.0,
                                        "lines": lines,
                                        "status": "pending",
                                    }
                                    if user:
                                        ver_data["created_by"] = user.get("username")
                                        ver_data["created_role"] = user.get("role")
                                    data_manager.add_bom_version(ver_data)
                                    st.success(f"BOM 已生成: {bom_data['bom_code']}")

                            # 分页显示详细信息
                            detail_tabs = st.tabs(["基础信息", "反应釜物料", "A料", "B料", "助剂", "反应参数", "工艺备注"])
                            
                            with detail_tabs[0]:
                                base_col1, base_col2 = st.columns(2)
                                with base_col1:
                                    st.markdown("**基础信息**")
                                    st.write(f"**配方编号:** {record.get('formula_id')}")
                                    st.write(f"**操作人:** {record.get('operator')}")
                                    st.write(f"**合成日期:** {record.get('synthesis_date')}")
                                
                                with base_col2:
                                    st.markdown("**设计参数**")
                                    st.write(f"**设计固含:** {record.get('design_solid_content')}%")
                                    st.write(f"**起始温度:** {record.get('start_temp')}°C")
                                    st.write(f"**最高温度:** {record.get('max_temp')}°C")
                                    st.write(f"**保温时间:** {record.get('holding_time')}小时")
                            
                            with detail_tabs[1]:
                                if record.get('reactor_materials'):
                                    st.markdown("**反应釜物料组成**")
                                    reactor_df = pd.DataFrame(record['reactor_materials'])
                                    st.dataframe(reactor_df, use_container_width=True)
                                    st.metric("反应釜总用量", f"{record.get('reactor_total_amount', 0):.2f} g")
                                else:
                                    st.info("暂无反应釜物料数据")
                            
                            with detail_tabs[2]:
                                if record.get('a_materials'):
                                    st.markdown("**A料组成**")
                                    a_df = pd.DataFrame(record['a_materials'])
                                    st.dataframe(a_df, use_container_width=True)
                                    
                                    a_info_col1, a_info_col2, a_info_col3 = st.columns(3)
                                    with a_info_col1:
                                        st.metric("A料总用量", f"{record.get('a_total_amount', 0):.2f} g")
                                    with a_info_col2:
                                        st.metric("滴加时间", f"{record.get('a_drip_time', 0)} 分钟")
                                    with a_info_col3:
                                        st.metric("滴加速度", f"{record.get('a_drip_speed', 0):.2f} g/min")
                                else:
                                    st.info("暂无A料数据")
                            
                            with detail_tabs[3]:
                                if record.get('b_materials'):
                                    st.markdown("**B料组成**")
                                    b_df = pd.DataFrame(record['b_materials'])
                                    st.dataframe(b_df, use_container_width=True)
                                    
                                    b_info_col1, b_info_col2, b_info_col3 = st.columns(3)
                                    with b_info_col1:
                                        st.metric("B料总用量", f"{record.get('b_total_amount', 0):.2f} g")
                                    with b_info_col2:
                                        st.metric("滴加时间", f"{record.get('b_drip_time', 0)} 分钟")
                                    with b_info_col3:
                                        st.metric("滴加速度", f"{record.get('b_drip_speed', 0):.2f} g/min")
                                else:
                                    st.info("暂无B料数据")
                            
                            with detail_tabs[4]:
                                if record.get('additive_materials'):
                                    st.markdown("**助剂添加**")
                                    # 处理显示数据
                                    add_display_data = []
                                    for item in record['additive_materials']:
                                        add_display_data.append({
                                            "助剂名称": item.get("name"),
                                            "原料名称": item.get("material_name"),
                                            "用量 (g)": item.get("amount"),
                                            "添加时间点": item.get("time_point"),
                                            "搅拌时长 (min)": item.get("stir_time")
                                        })
                                    add_df = pd.DataFrame(add_display_data)
                                    st.dataframe(add_df, use_container_width=True)
                                else:
                                    st.info("暂无助剂数据")
                                    
                            with detail_tabs[5]:
                                st.markdown("**反应参数**")
                                reaction_cols = st.columns(3)
                                with reaction_cols[0]:
                                    st.metric("起始温度", f"{record.get('start_temp', 0)}°C")
                                with reaction_cols[1]:
                                    st.metric("最高温度", f"{record.get('max_temp', 0)}°C")
                                with reaction_cols[2]:
                                    st.metric("保温时间", f"{record.get('holding_time', 0)}小时")
                            
                            with detail_tabs[6]:
                                if record.get('process_notes'):
                                    st.markdown("**实验工艺备注**")
                                    st.info(record['process_notes'])
                                else:
                                    st.info("暂无工艺备注")
                    
                    st.divider()
            
            # 分页控制
            if total_pages > 1:
                st.markdown("---")
                pag_col1, pag_col2, pag_col3 = st.columns([2, 1, 2])
                
                with pag_col1:
                    if st.button("⬅️ 上一页", 
                               disabled=st.session_state.syn_page <= 1,
                               key="syn_prev_btn"):
                        st.session_state.syn_page -= 1
                        st.rerun()
                
                with pag_col2:
                    st.markdown(f"**第 {st.session_state.syn_page}/{total_pages} 页**")
                
                with pag_col3:
                    if st.button("下一页 ➡️", 
                               disabled=st.session_state.syn_page >= total_pages,
                               key="syn_next_btn"):
                        st.session_state.syn_page += 1
                        st.rerun()
        else:
            st.info("没有找到匹配的合成实验记录")
    else:
        st.info("暂无合成实验数据，请添加第一条记录")

# ==================== 成品减水剂模块函数 ====================
def _render_products_tab(data_manager):
    """渲染成品减水剂标签页 - 增强版（带查找、编辑、固含计算）"""
    st.subheader("📊 成品减水剂管理")
    
    # 获取数据
    products = data_manager.get_all_products()
    synthesis_records = data_manager.get_all_synthesis_records()
    raw_materials = data_manager.get_all_raw_materials()
    
    # 使用标签页组织功能
    tab1, tab2, tab3 = st.tabs(["📝 新增成品", "🔍 查找与编辑", "📋 成品列表"])
    
    # ==================== 新增成品标签页 ====================
    with tab1:
        _render_add_product_tab(data_manager, raw_materials, synthesis_records)
    
    # ==================== 查找与编辑标签页 ====================
    with tab2:
        _render_search_edit_tab(data_manager, products, raw_materials, synthesis_records)
    
    # ==================== 成品列表标签页 ====================
    with tab3:
        _render_products_list_tab(data_manager, products, raw_materials)

def _calculate_theoretical_solid(ingredients, raw_materials_map):
    """计算理论固含"""
    total_mass = 0.0
    total_solid_mass = 0.0
    
    for item in ingredients:
        name = item.get("name")
        amount = float(item.get("amount", 0.0) or 0.0)
        
        if name and amount > 0:
            total_mass += amount
            
            # 查找原材料固含
            raw_mat = raw_materials_map.get(name)
            solid_percent = 0.0
            if raw_mat:
                solid_percent = float(raw_mat.get("solid_content", 0.0) or 0.0)
            
            total_solid_mass += amount * (solid_percent / 100.0)
            
    if total_mass > 0:
        return (total_solid_mass / total_mass) * 100.0
    return 0.0

def _render_add_product_tab(data_manager, raw_materials, synthesis_records):
    """渲染新增成品标签页"""
    st.markdown("### ➕ 新增成品减水剂")
    
    # 初始化session state
    if "ingredient_rows" not in st.session_state:
        st.session_state.ingredient_rows = [{"name": "", "amount": 0.0}]
    
    # 原料选择下拉选项
    material_options = {}
    if raw_materials:
        for m in raw_materials:
            name = m['name']
            extras = []
            if m.get('abbreviation'):
                extras.append(m['abbreviation'])
            if m.get('manufacturer'):
                extras.append(m['manufacturer'])
            
            if extras:
                name += f" ({' | '.join(extras)})"
            material_options[name] = m
            
    material_names = list(material_options.keys())
    
    form_id = "product_add"
    with st.form(f"add_product_form_{form_id}", clear_on_submit=True):
        # 基本信息
        col1, col2 = st.columns(2)
        
        with col1:
            product_name = st.text_input(
                "成品名称*", 
                placeholder="例如: PC-2024-HP高保坍型",
                help="请输入成品减水剂的名称",
                key=f"product_name_{form_id}"
            )
            product_code = st.text_input(
                "产品编号*",
                placeholder="例如: PC001-2024-01",
                help="唯一的产品编号，用于标识",
                key=f"product_code_{form_id}"
            )
            
            # 选择关联的合成实验
            syn_options = ["无"] + [f"{r['formula_id']}" for r in synthesis_records]
            related_synthesis = st.selectbox(
                "关联合成实验",
                options=syn_options,
                help="可选：关联到具体的合成实验",
                key=f"related_synthesis_{form_id}"
            )
        
        with col2:
            batch_number = st.text_input(
                "生产批号*",
                placeholder="例如: 20240115-001",
                help="生产批号，用于追溯",
                key=f"batch_number_{form_id}"
            )
            production_date = st.date_input(
                "生产日期*",
                value=datetime.now(),
                key=f"production_date_{form_id}"
            )
            expiration_date = st.date_input(
                "有效期至",
                value=datetime.now() + pd.Timedelta(days=180),
                key=f"expiration_date_{form_id}"
            )
        
        # 物化性质
        st.markdown("### 🔬 匀质性指标")
        
        prop_col1, prop_col2, prop_col3, prop_col4 = st.columns(4)
        
        with prop_col1:
            solid_content = st.number_input(
                "固含(%)*", 
                min_value=0.0, 
                max_value=100.0,
                value=40.0,
                step=0.1,
                help="成品的固含量百分比",
                key=f"solid_content_{form_id}"
            )
            density = st.number_input(
                "密度 (g/cm³)*", 
                min_value=0.8, 
                max_value=2.0,
                value=1.05,
                step=0.01,
                key=f"density_{form_id}"
            )
        
        with prop_col2:
            ph_value = st.number_input(
                "pH值*", 
                min_value=0.0, 
                max_value=14.0,
                value=7.0,
                step=0.1,
                key=f"ph_value_{form_id}"
            )
            viscosity = st.number_input(
                "粘度 (mPa·s)", 
                min_value=0.0,
                value=50.0,
                step=1.0,
                key=f"viscosity_{form_id}"
            )
        
        with prop_col3:
            color = st.selectbox(
                "外观颜色",
                ["无色透明", "淡黄色", "黄色", "褐色", "其他"],
                key=f"color_{form_id}"
            )
            odor = st.selectbox(
                "气味",
                ["无味", "轻微气味", "刺激性气味", "其他"],
                key=f"odor_{form_id}"
            )
        
        with prop_col4:
            water_reduction_rate = st.number_input(
                "减水率 (%)",
                min_value=0.0,
                max_value=100.0,
                value=0.0,
                step=0.1,
                key=f"water_reduction_rate_{form_id}"
            )
            wr_dosage = st.number_input(
                "减水率测试掺量 (%)",
                min_value=0.0,
                value=0.0,
                step=0.01,
                help="测试减水率时的折固掺量或液体掺量",
                key=f"wr_dosage_{form_id}"
            )
        
        # ==================== 配方 ====================
        st.markdown("### ⚗️ 成品配方")
        
        # 配方模块头部：添加原料按钮和说明
        formula_col1, formula_col2 = st.columns([3, 1])
        with formula_col1:
            st.info("请从原材料库中选择原料并输入用量（单位: g），系统将自动计算总质量和固含")
        
        # 显示原料行
        for i, row in enumerate(st.session_state.ingredient_rows):
            with st.container():
                ing_col1, ing_col2, ing_col3 = st.columns([4, 2, 1])
                
                with ing_col1:
                    # 原料选择
                    current_name = row["name"]
                    selected_material = st.selectbox(
                        f"原料 {i+1}",
                        options=["请选择..."] + material_names,
                        index=material_names.index(current_name) + 1 if current_name in material_names else 0,
                        key=f"ing_material_{form_id}_{i}",
                        label_visibility="collapsed"
                    )
                    
                    if selected_material and selected_material != "请选择...":
                        # 显示原料信息提示
                        material_info = material_options[selected_material]
                        solid_info = material_info.get('solid_content', '未知')
                        st.caption(f"固含: {solid_info}% | 单价: ¥{material_info.get('unit_price', '未知')}/吨")
                
                with ing_col2:
                    # 用量输入
                    amount = st.number_input(
                        "用量 (g)",
                        min_value=0.0,
                        value=row["amount"],
                        step=0.1,
                        key=f"ing_amount_{form_id}_{i}",
                        label_visibility="collapsed"
                    )
                
                with ing_col3:
                    # 删除按钮（第一行除外）
                    if i > 0:
                        delete_key = f"ing_delete_{form_id}_{i}"
                        if st.form_submit_button("🗑️", key=delete_key, use_container_width=True):
                            del st.session_state.ingredient_rows[i]
                            st.rerun()
                
                # 更新session state
                if selected_material != "请选择...":
                    st.session_state.ingredient_rows[i] = {
                        "name": selected_material,
                        "amount": amount
                    }
                else:
                    st.session_state.ingredient_rows[i] = {
                        "name": "",
                        "amount": amount
                    }
            
            if i < len(st.session_state.ingredient_rows) - 1:
                st.divider()
        
        # 在配方模块底部添加"添加原料"按钮
        add_col1, add_col2, add_col3 = st.columns([1, 1, 2])
        with add_col1:
            add_key = f"add_ingredient_{form_id}"
            if st.form_submit_button("➕ 添加原料", key=add_key, use_container_width=True):
                st.session_state.ingredient_rows.append({"name": "", "amount": 0.0})
                st.rerun()
        
        # 计算总质量和固含
        total_mass = 0.0
        total_solid_mass = 0.0
        ingredient_details = []
        valid_ingredients = []
        
        for row in st.session_state.ingredient_rows:
            if row["name"] and row["amount"] > 0:
                material_info = material_options.get(row["name"])
                if material_info:
                    material_solid = material_info.get('solid_content', 100.0)
                    solid_mass = row["amount"] * (material_solid / 100.0)
                    total_mass += row["amount"]
                    total_solid_mass += solid_mass
                    
                    ingredient_details.append({
                        "name": row["name"],
                        "amount": row["amount"],
                        "solid_content": material_solid,
                        "solid_mass": solid_mass
                    })
                    
                    valid_ingredients.append({
                        "name": row["name"],
                        "amount": row["amount"],
                        "material_id": material_info.get('id'),
                        "solid_content": material_solid
                    })
        
        calculated_solid_content = (total_solid_mass / total_mass * 100) if total_mass > 0 else 0
        
        # 显示计算结果
        if ingredient_details:
            st.markdown("### 📊 计算结果")
            
            calc_col1, calc_col2 = st.columns(2)
            
            with calc_col1:
                st.metric("总质量", f"{total_mass:.2f} g")
                st.metric("计算固含", f"{calculated_solid_content:.2f} %")
            
            with calc_col2:
                # 与输入的固含比较
                diff = abs(calculated_solid_content - solid_content)
                if diff > 1.0:
                    st.warning(f"⚠️ 计算固含({calculated_solid_content:.1f}%)与输入固含({solid_content:.1f}%)差异较大")
                else:
                    st.success("✅ 固含计算一致")
            
            # 原料组成详情
            with st.expander("📋 查看原料组成详情", expanded=False):
                if ingredient_details:
                    detail_df = pd.DataFrame(ingredient_details)
                    detail_df["质量占比(%)"] = (detail_df["amount"] / total_mass * 100).round(2)
                    detail_df["固含占比(%)"] = (detail_df["solid_mass"] / total_solid_mass * 100).round(2)
                    
                    # 重命名列
                    detail_df = detail_df.rename(columns={
                        "name": "原料名称",
                        "amount": "用量(g)",
                        "solid_content": "原料固含(%)",
                        "solid_mass": "固体质量(g)"
                    })
                    
                    st.dataframe(detail_df, use_container_width=True)
        
        # 产品描述和存储
        st.markdown("### 📝 产品信息")
        
        desc_col1, desc_col2 = st.columns(2)
        
        with desc_col1:
            description = st.text_area(
                "产品描述",
                placeholder="描述产品特性、用途、注意事项等...",
                height=100,
                key=f"description_{form_id}"
            )
        
        with desc_col2:
            storage_condition = st.selectbox(
                "存储条件",
                ["常温密封", "阴凉干燥", "冷藏", "避光保存", "其他"],
                key=f"storage_condition_{form_id}"
            )
            package_type = st.selectbox(
                "包装类型",
                ["塑料桶", "铁桶", "IBC吨桶", "槽罐车", "其他"],
                key=f"package_type_{form_id}"
            )
        
        # 提交按钮
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            submitted = st.form_submit_button("💾 保存成品", type="primary", use_container_width=True)
        
        with col_btn2:
            reset_key = f"reset_form_{form_id}"
            if st.form_submit_button("🔄 重置表单", type="secondary", key=reset_key, use_container_width=True):
                st.session_state.ingredient_rows = [{"name": "", "amount": 0.0}]
                st.rerun()
        
        if submitted:
            # 验证必填项
            validation_errors = []
            
            if not product_name:
                validation_errors.append("请输入成品名称")
            if not product_code:
                validation_errors.append("请输入产品编号")
            if not batch_number:
                validation_errors.append("请输入生产批号")
            if not solid_content or solid_content <= 0 or solid_content > 100:
                validation_errors.append("请输入有效的固含量(0-100%)")
            
            if not valid_ingredients:
                validation_errors.append("请至少添加一种有效原料")
            
            if validation_errors:
                for error in validation_errors:
                    st.error(error)
            else:
                # 构建成品数据
                new_product = {
                    "product_name": product_name,
                    "product_code": product_code,
                    "batch_number": batch_number,
                    "production_date": production_date.strftime("%Y-%m-%d"),
                    "expiration_date": expiration_date.strftime("%Y-%m-%d"),
                    "solid_content": solid_content,
                    "calculated_solid_content": calculated_solid_content,
                    "density": density,
                    "ph_value": ph_value,
                    "viscosity": viscosity,
                    "water_reduction_rate": water_reduction_rate,
                    "wr_dosage": wr_dosage,
                    "color": color,
                    "odor": odor,
                    "storage_condition": storage_condition,
                    "package_type": package_type,
                    "related_synthesis": related_synthesis if related_synthesis != "无" else "",
                    "ingredients": valid_ingredients,
                    "total_mass": total_mass,
                    "total_solid_mass": total_solid_mass,
                    "description": description,
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "last_modified": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                # 保存到数据库
                try:
                    if data_manager.add_product(new_product):
                        st.success(f"✅ 成品减水剂 '{product_name}' 保存成功！")
                        
                        # 显示保存信息
                        with st.expander("📄 查看保存详情", expanded=False):
                            st.write(f"**产品编号:** {product_code}")
                            st.write(f"**生产批号:** {batch_number}")
                            st.write(f"**总质量:** {total_mass:.2f} g")
                            st.write(f"**总固体质量:** {total_solid_mass:.2f} g")
                            st.write(f"**计算固含:** {calculated_solid_content:.2f} %")
                            st.write(f"**原料数量:** {len(valid_ingredients)} 种")
                        
                        # 重置表单
                        st.session_state.ingredient_rows = [{"name": "", "amount": 0.0}]
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("保存失败，请重试")
                except ValueError as e:
                    st.error(f"保存失败: {e}")

def _render_search_edit_tab(data_manager, products, raw_materials, synthesis_records):
    """渲染查找与编辑标签页"""
    st.markdown("### 🔍 查找与编辑成品")
    
    if not products:
        st.info("暂无成品数据，请先添加成品")
        return
    
    # 搜索功能
    search_col1, search_col2, search_col3 = st.columns([3, 2, 1])
    
    with search_col1:
        search_term = st.text_input(
            "🔍 搜索成品",
            placeholder="输入名称、编号或批号...",
            key="product_search_input"
        )
    
    with search_col2:
        search_field = st.selectbox(
            "搜索字段",
            ["全部", "名称", "编号", "批号", "生产日期"],
            key="product_search_field"
        )
    
    with search_col3:
        search_button = st.button("搜索", use_container_width=True, type="primary", key="product_search_button")
    
    if "product_search_term_applied" not in st.session_state:
        st.session_state.product_search_term_applied = ""
    if "product_search_field_applied" not in st.session_state:
        st.session_state.product_search_field_applied = "全部"

    if search_button:
        st.session_state.product_search_term_applied = search_term.strip()
        st.session_state.product_search_field_applied = search_field

    applied_term = st.session_state.product_search_term_applied
    applied_field = st.session_state.product_search_field_applied

    filtered_products = products
    if applied_term:
        if applied_field == "全部" or applied_field == "名称":
            filtered_products = [p for p in filtered_products if applied_term.lower() in p.get("product_name", "").lower()]
        elif applied_field == "编号":
            filtered_products = [p for p in filtered_products if applied_term.lower() in p.get("product_code", "").lower()]
        elif applied_field == "批号":
            filtered_products = [p for p in filtered_products if applied_term.lower() in p.get("batch_number", "").lower()]
        elif applied_field == "生产日期":
            filtered_products = [p for p in filtered_products if applied_term in p.get("production_date", "")]
    
    if not filtered_products:
        st.warning("未找到匹配的成品")
        return
    
    # 选择要编辑的产品
    st.markdown("### ✏️ 选择要编辑的成品")
    
    product_options = {f"{p['product_name']} ({p['product_code']})": p['id'] for p in filtered_products}
    selected_product_key = st.selectbox(
        "选择成品",
        options=list(product_options.keys()),
        key="edit_product_select"
    )
    
    if selected_product_key:
        selected_product_id = product_options[selected_product_key]
        selected_product = next((p for p in products if p['id'] == selected_product_id), None)
        
        if selected_product:
            _render_edit_product_form(data_manager, selected_product, raw_materials)

def _render_edit_product_form(data_manager, product, raw_materials):
    """渲染编辑成品表单"""
    st.markdown(f"### ✏️ 编辑成品: {product['product_name']}")
    
    # 初始化原料行
    edit_rows_key = f"edit_ingredient_rows_{product['id']}"
    if edit_rows_key not in st.session_state:
        existing_ingredients = product.get('ingredients', [])
        st.session_state[edit_rows_key] = existing_ingredients if existing_ingredients else [{"name": "", "amount": 0.0}]
    
    # 原料选择下拉选项
    material_options = {m['name']: m for m in raw_materials}
    material_names = list(material_options.keys())
    
    form_id = f"edit_{product['id']}"
    with st.form(f"edit_product_form_{product['id']}_{form_id}", clear_on_submit=False):
        # 基本信息
        col1, col2 = st.columns(2)
        
        with col1:
            edit_product_name = st.text_input(
                "成品名称*",
                value=product.get('product_name', ''),
                key=f"edit_name_{product['id']}_{form_id}"
            )
            edit_product_code = st.text_input(
                "产品编号*",
                value=product.get('product_code', ''),
                key=f"edit_code_{product['id']}_{form_id}"
            )
            edit_batch_number = st.text_input(
                "生产批号*",
                value=product.get('batch_number', ''),
                key=f"edit_batch_{product['id']}_{form_id}"
            )
        
        with col2:
            # 生产日期
            prod_date_str = product.get('production_date', '')
            try:
                if prod_date_str:
                    edit_production_date = st.date_input(
                        "生产日期*",
                        value=datetime.strptime(prod_date_str, "%Y-%m-%d"),
                        key=f"edit_date_{product['id']}_{form_id}"
                    )
                else:
                    edit_production_date = st.date_input(
                        "生产日期*",
                        value=datetime.now(),
                        key=f"edit_date_{product['id']}_{form_id}"
                    )
            except:
                edit_production_date = st.date_input(
                    "生产日期*",
                    value=datetime.now(),
                    key=f"edit_date_{product['id']}_{form_id}"
                )
            
            # 有效期
            exp_date_str = product.get('expiration_date', '')
            try:
                if exp_date_str:
                    edit_expiration_date = st.date_input(
                        "有效期至",
                        value=datetime.strptime(exp_date_str, "%Y-%m-%d"),
                        key=f"edit_exp_date_{product['id']}_{form_id}"
                    )
                else:
                    edit_expiration_date = st.date_input(
                        "有效期至",
                        value=datetime.now() + pd.Timedelta(days=180),
                        key=f"edit_exp_date_{product['id']}_{form_id}"
                    )
            except:
                edit_expiration_date = st.date_input(
                    "有效期至",
                    value=datetime.now() + pd.Timedelta(days=180),
                    key=f"edit_exp_date_{product['id']}_{form_id}"
                )
        
        # 物化性质
        st.markdown("### 🔬 匀质性指标")
        
        prop_col1, prop_col2, prop_col3, prop_col4 = st.columns(4)
        
        with prop_col1:
            edit_solid_content = st.number_input(
                "固含(%)*", 
                min_value=0.0, 
                max_value=100.0,
                value=float(product.get('solid_content', 40.0)),
                step=0.1,
                key=f"edit_solid_{product['id']}_{form_id}"
            )
            edit_density = st.number_input(
                "密度 (g/cm³)*", 
                min_value=0.8, 
                max_value=2.0,
                value=float(product.get('density', 1.05)),
                step=0.01,
                key=f"edit_density_{product['id']}_{form_id}"
            )
        
        with prop_col2:
            edit_ph_value = st.number_input(
                "pH值*", 
                min_value=0.0, 
                max_value=14.0,
                value=float(product.get('ph_value', 7.0)),
                step=0.1,
                key=f"edit_ph_{product['id']}_{form_id}"
            )
            edit_viscosity = st.number_input(
                "粘度 (mPa·s)", 
                min_value=0.0,
                value=float(product.get('viscosity', 50.0)),
                step=1.0,
                key=f"edit_viscosity_{product['id']}_{form_id}"
            )
        
        with prop_col3:
            color_options = ["无色透明", "淡黄色", "黄色", "褐色", "其他"]
            current_color = product.get('color', '无色透明')
            color_index = color_options.index(current_color) if current_color in color_options else 0
            edit_color = st.selectbox(
                "外观颜色",
                options=color_options,
                index=color_index,
                key=f"edit_color_{product['id']}_{form_id}"
            )
            
            odor_options = ["无味", "轻微气味", "刺激性气味", "其他"]
            current_odor = product.get('odor', '无味')
            odor_index = odor_options.index(current_odor) if current_odor in odor_options else 0
            edit_odor = st.selectbox(
                "气味",
                options=odor_options,
                index=odor_index,
                key=f"edit_odor_{product['id']}_{form_id}"
            )
        
        with prop_col4:
            edit_water_reduction_rate = st.number_input(
                "减水率 (%)",
                min_value=0.0,
                max_value=100.0,
                value=float(product.get('water_reduction_rate', 0.0)),
                step=0.1,
                key=f"edit_wr_rate_{product['id']}_{form_id}"
            )
            edit_wr_dosage = st.number_input(
                "减水率测试掺量 (%)",
                min_value=0.0,
                value=float(product.get('wr_dosage', 0.0)),
                step=0.01,
                help="测试减水率时的折固掺量或液体掺量",
                key=f"edit_wr_dosage_{product['id']}_{form_id}"
            )

        # ==================== 成品配方模块 ====================
        st.markdown("### ⚗️ 成品配方")
        
        # 配方模块头部：说明
        st.info("编辑原料组成，系统将自动重新计算总质量和固含")
        
        # 动态编辑原料行
        for i, row in enumerate(st.session_state[edit_rows_key]):
            with st.container():
                ing_col1, ing_col2, ing_col3 = st.columns([4, 2, 1])
                
                with ing_col1:
                    # 获取当前原料名称
                    current_name = row.get('name', '')
                    
                    # 原料选择
                    selected_material = st.selectbox(
                        f"原料 {i+1}",
                        options=["请选择..."] + material_names,
                        index=material_names.index(current_name) + 1 if current_name in material_names else 0,
                        key=f"edit_ing_material_{product['id']}_{i}_{form_id}",
                        label_visibility="collapsed"
                    )
                    
                    if selected_material and selected_material != "请选择...":
                        material_info = material_options[selected_material]
                        st.caption(f"固含: {material_info.get('solid_content', '未知')}%")
                
                with ing_col2:
                    # 用量输入
                    amount = st.number_input(
                        "用量 (g)",
                        min_value=0.0,
                        value=float(row.get('amount', 0.0)),
                        step=0.1,
                        key=f"edit_ing_amount_{product['id']}_{i}_{form_id}",
                        label_visibility="collapsed"
                    )
                
                with ing_col3:
                    # 删除按钮（第一行除外）
                    if i > 0:
                        delete_key = f"edit_ing_delete_{product['id']}_{i}_{form_id}"
                        if st.form_submit_button("🗑️", key=delete_key, use_container_width=True):
                            del st.session_state[edit_rows_key][i]
                            st.rerun()
                
                # 更新session state
                if selected_material != "请选择...":
                    st.session_state[edit_rows_key][i] = {
                        "name": selected_material,
                        "amount": amount
                    }
                else:
                    st.session_state[edit_rows_key][i] = {
                        "name": "",
                        "amount": amount
                    }
            
            if i < len(st.session_state[edit_rows_key]) - 1:
                st.divider()
        
        # 在配方模块底部添加"添加原料"按钮
        add_col1, add_col2, add_col3 = st.columns([1, 1, 2])
        with add_col1:
            add_key = f"edit_add_ingredient_{product['id']}_{form_id}"
            if st.form_submit_button("➕ 添加原料", key=add_key, use_container_width=True):
                st.session_state[edit_rows_key].append({"name": "", "amount": 0.0})
                st.rerun()
        
        # 计算总质量和固含
        valid_ingredients = []
        total_mass = 0.0
        total_solid_mass = 0.0
        
        for row in st.session_state[edit_rows_key]:
            if row.get('name') and row.get('amount', 0) > 0:
                material_info = material_options.get(row['name'])
                if material_info:
                    valid_ingredients.append({
                        "name": row['name'],
                        "amount": row['amount'],
                        "material_id": material_info.get('id'),
                        "solid_content": material_info.get('solid_content', 100.0)
                    })
                    total_mass += row['amount']
                    
                    # 计算固体质量
                    material_solid = material_info.get('solid_content', 100.0)
                    solid_mass = row['amount'] * (material_solid / 100.0)
                    total_solid_mass += solid_mass
        
        # 显示计算结果
        if valid_ingredients:
            calculated_solid_content = (total_solid_mass / total_mass * 100) if total_mass > 0 else 0
            
            st.markdown("### 📊 计算结果")
            
            calc_col1, calc_col2 = st.columns(2)
            
            with calc_col1:
                st.metric("总质量", f"{total_mass:.2f} g")
                st.metric("计算固含", f"{calculated_solid_content:.2f} %")
            
            with calc_col2:
                diff = abs(calculated_solid_content - edit_solid_content)
                if diff > 1.0:
                    st.warning(f"⚠️ 计算固含({calculated_solid_content:.1f}%)与输入固含({edit_solid_content:.1f}%)差异较大")
                else:
                    st.success("✅ 固含计算一致")
        
        # 产品描述和存储
        st.markdown("### 📝 产品信息")
        
        desc_col1, desc_col2 = st.columns(2)
        
        with desc_col1:
            edit_description = st.text_area(
                "产品描述",
                value=product.get('description', ''),
                height=100,
                key=f"edit_desc_{product['id']}_{form_id}"
            )
        
        with desc_col2:
            storage_options = ["常温密封", "阴凉干燥", "冷藏", "避光保存", "其他"]
            current_storage = product.get('storage_condition', '常温密封')
            storage_index = storage_options.index(current_storage) if current_storage in storage_options else 0
            edit_storage_condition = st.selectbox(
                "存储条件",
                options=storage_options,
                index=storage_index,
                key=f"edit_storage_{product['id']}_{form_id}"
            )
            
            package_options = ["塑料桶", "铁桶", "IBC吨桶", "槽罐车", "其他"]
            current_package = product.get('package_type', '塑料桶')
            package_index = package_options.index(current_package) if current_package in package_options else 0
            edit_package_type = st.selectbox(
                "包装类型",
                options=package_options,
                index=package_index,
                key=f"edit_package_{product['id']}_{form_id}"
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
            reset_key = f"edit_reset_{product['id']}_{form_id}"
            if st.form_submit_button(
                "🔄 重置表单",
                type="secondary",
                key=reset_key,
                use_container_width=True
            ):
                if edit_rows_key in st.session_state:
                    del st.session_state[edit_rows_key]
                st.rerun()
        
        with col_btn3:
            cancel_key = f"edit_cancel_{product['id']}_{form_id}"
            cancel_submitted = st.form_submit_button(
                "❌ 取消编辑",
                type="secondary",
                key=cancel_key,
                use_container_width=True
            )
        
        # 处理表单提交
        if save_submitted:
            # 验证必填项
            validation_errors = []
            
            if not edit_product_name:
                validation_errors.append("请输入成品名称")
            if not edit_product_code:
                validation_errors.append("请输入产品编号")
            if not edit_batch_number:
                validation_errors.append("请输入生产批号")
            if not edit_solid_content or edit_solid_content <= 0 or edit_solid_content > 100:
                validation_errors.append("请输入有效的固含量(0-100%)")
            
            if not valid_ingredients:
                validation_errors.append("请至少添加一种有效原料")
            
            if validation_errors:
                for error in validation_errors:
                    st.error(error)
            else:
                # 更新成品数据
                calculated_solid_content = (total_solid_mass / total_mass * 100) if total_mass > 0 else 0
                
                updated_product = {
                    "product_name": edit_product_name,
                    "product_code": edit_product_code,
                    "batch_number": edit_batch_number,
                    "production_date": edit_production_date.strftime("%Y-%m-%d"),
                    "expiration_date": edit_expiration_date.strftime("%Y-%m-%d"),
                    "solid_content": edit_solid_content,
                    "calculated_solid_content": calculated_solid_content,
                    "density": edit_density,
                    "ph_value": edit_ph_value,
                    "viscosity": edit_viscosity,
                    "water_reduction_rate": edit_water_reduction_rate,
                    "wr_dosage": edit_wr_dosage,
                    "color": edit_color,
                    "odor": edit_odor,
                    "storage_condition": edit_storage_condition,
                    "package_type": edit_package_type,
                    "ingredients": valid_ingredients,
                    "total_mass": total_mass,
                    "total_solid_mass": total_solid_mass,
                    "description": edit_description,
                    "last_modified": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                # 保存修改
                try:
                    if data_manager.update_product(product['id'], updated_product):
                        st.success(f"✅ 成品 '{edit_product_name}' 更新成功！")
                        
                        # 清除session state
                        if edit_rows_key in st.session_state:
                            del st.session_state[edit_rows_key]
                        
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("更新失败，请重试")
                except ValueError as e:
                    st.error(f"更新失败: {e}")
        
        if cancel_submitted:
            st.info("已取消编辑操作")
            time.sleep(0.5)
            st.rerun()

def _render_products_list_tab(data_manager, products, raw_materials):
    """渲染成品列表标签页"""
    st.markdown("### 📋 成品列表")
    
    # 检查是否处于编辑模式
    if st.session_state.get("product_list_edit_mode", False):
        product_id = st.session_state.get("product_list_edit_id")
        product = next((p for p in products if p['id'] == product_id), None)
        if product:
            if st.button("⬅️ 返回列表", key="back_to_list"):
                st.session_state.product_list_edit_mode = False
                st.rerun()
            _render_edit_product_form(data_manager, product, raw_materials)
        else:
            st.error("未找到要编辑的成品")
            st.session_state.product_list_edit_mode = False
            if st.button("⬅️ 返回列表", key="back_to_list_error"):
                 st.rerun()
        return

    if not products:
        st.info("暂无成品数据")
        return
    
    # 搜索和筛选
    search_col1, search_col2, search_col3 = st.columns([2, 2, 1])
    
    with search_col1:
        list_search_term = st.text_input(
            "快速搜索",
            placeholder="名称/编号/批号...",
            key="product_list_search_input"
        )
    
    with search_col2:
        list_filter_status = st.selectbox(
            "筛选",
            ["全部", "高固含(>40%)", "低固含(<30%)"],
            key="product_list_filter"
        )
    
    with search_col3:
        items_per_page = st.selectbox(
            "每页显示",
            [10, 20, 50],
            index=1,
            key="product_list_page_size"
        )
    
    # 过滤产品
    filtered_products = products
    
    if list_search_term:
        filtered_products = [
            p for p in filtered_products
            if (list_search_term.lower() in p.get('product_name', '').lower() or
                list_search_term.lower() in p.get('product_code', '').lower() or
                list_search_term.lower() in p.get('batch_number', '').lower())
        ]
    
    if list_filter_status != "全部":
        if list_filter_status == "高固含(>40%)":
            filtered_products = [
                p for p in filtered_products
                if float(p.get('solid_content', 0)) > 40
            ]
        elif list_filter_status == "低固含(<30%)":
            filtered_products = [
                p for p in filtered_products
                if float(p.get('solid_content', 0)) < 30
            ]
    
    # 分页
    if "product_list_page" not in st.session_state:
        st.session_state.product_list_page = 1
    
    total_pages = max(1, (len(filtered_products) + items_per_page - 1) // items_per_page)
    start_idx = (st.session_state.product_list_page - 1) * items_per_page
    end_idx = min(start_idx + items_per_page, len(filtered_products))
    current_products = filtered_products[start_idx:end_idx]
    
    # 批量操作栏
    st.markdown("#### 批量操作")
    op_col1, op_col2, op_col3 = st.columns([1, 1, 4])
    
    # 获取当前选中的ID
    selected_ids = []
    for p in products:
        if st.session_state.get(f"select_product_{p['id']}", False):
            selected_ids.append(p['id'])

    with op_col1:
        if st.button("✏️ 编辑选中", disabled=len(selected_ids) != 1, use_container_width=True):
            st.session_state.product_list_edit_mode = True
            st.session_state.product_list_edit_id = selected_ids[0]
            st.rerun()
            
    with op_col2:
        if st.button("🗑️ 删除选中", disabled=len(selected_ids) == 0, use_container_width=True):
            st.session_state.product_list_confirm_delete = True
            st.rerun()

    if st.session_state.get("product_list_confirm_delete", False):
        st.warning(f"确定要删除选中的 {len(selected_ids)} 个成品吗？此操作不可恢复。")
        col_yes, col_no = st.columns(2)
        with col_yes:
            if st.button("✅ 确认删除", key="confirm_bulk_delete"):
                success_count = 0
                for pid in selected_ids:
                    if data_manager.delete_product(pid):
                        success_count += 1
                        # 清除选中状态
                        if f"select_product_{pid}" in st.session_state:
                            del st.session_state[f"select_product_{pid}"]
                
                st.success(f"成功删除 {success_count} 个成品")
                st.session_state.product_list_confirm_delete = False
                time.sleep(1)
                st.rerun()
        with col_no:
            if st.button("❌ 取消", key="cancel_bulk_delete"):
                st.session_state.product_list_confirm_delete = False
                st.rerun()

    st.divider()
    
    # 显示产品列表
    for product in current_products:
        with st.container():
            col_sel, col1, col2 = st.columns([0.5, 3, 2])
            
            with col_sel:
                st.checkbox("", key=f"select_product_{product['id']}")
            
            with col1:
                st.markdown(f"**{product['product_name']}**")
                st.caption(f"编号: {product.get('product_code', '')} | 批号: {product.get('batch_number', '')}")
            
            with col2:
                solid_content = float(product.get('solid_content', 0))
                st.caption(f"固含: {solid_content}% | 密度: {product.get('density', '')} g/cm³")
                st.caption(f"生产日期: {product.get('production_date', '')}")
            
            # 详细信息（可展开）
            with st.expander("详细信息"):
                if st.button("🏭 生成 BOM (草稿)", key=f"gen_bom_prod_{product['id']}"):
                    bom_data = {
                        "bom_code": f"BOM-PD-{product.get('product_code', 'Unknown')}",
                        "bom_name": f"From {product.get('product_name')}",
                        "bom_type": "成品", # 使用中文
                        "status": "draft"
                    }
                    new_bom_id = data_manager.add_bom(bom_data)
                    if new_bom_id:
                        lines = []
                        for ing in product.get('ingredients', []):
                             # 这里需要区分是母液还是原材料，目前 ingredients 里没有 type，
                             # 只有 name。暂时统一当作 raw_material，后续人工修改。
                             lines.append({
                                 "item_type": "raw_material", 
                                 "item_name": ing.get('name'), 
                                 "qty": float(ing.get('amount', 0)), 
                                 "phase": "mix"
                             })
                        
                        total_yield = sum(float(l['qty']) for l in lines)
                        
                        user = st.session_state.get("user", None)
                        ver_data = {
                            "bom_id": new_bom_id,
                            "version": "V1", 
                            "effective_from": datetime.now().strftime("%Y-%m-%d"),
                            "yield_base": total_yield if total_yield > 0 else 1000.0,
                            "lines": lines,
                            "status": "pending",
                        }
                        if user:
                            ver_data["created_by"] = user.get("username")
                            ver_data["created_role"] = user.get("role")
                        data_manager.add_bom_version(ver_data)
                        st.success(f"BOM 已生成: {bom_data['bom_code']}")

                # 基本信息
                info_col1, info_col2 = st.columns(2)
                
                with info_col1:
                    st.markdown("**基本信息**")
                    st.write(f"**产品编号:** {product.get('product_code', '')}")
                    st.write(f"**生产批号:** {product.get('batch_number', '')}")
                    st.write(f"**生产日期:** {product.get('production_date', '')}")
                    st.write(f"**有效期至:** {product.get('expiration_date', '')}")
                
                with info_col2:
                    st.markdown("**匀质性指标**")
                    st.write(f"**固含:** {product.get('solid_content', '')}%")
                    st.write(f"**密度:** {product.get('density', '')} g/cm³")
                    st.write(f"**pH值:** {product.get('ph_value', '')}")
                    st.write(f"**粘度:** {product.get('viscosity', '')} mPa·s")
                    st.write(f"**外观:** {product.get('color', '')}")
                    st.write(f"**气味:** {product.get('odor', '')}")
                
                # 原料组成
                if product.get('ingredients'):
                    st.markdown("**原料组成**")
                    ingredients = product['ingredients']
                    total_mass = sum(ing.get('amount', 0) for ing in ingredients)
                    
                    ing_data = []
                    for ing in ingredients:
                        amount = ing.get('amount', 0)
                        solid_content_val = ing.get('solid_content', 100.0)
                        solid_mass = amount * (solid_content_val / 100.0)
                        
                        ing_data.append({
                            "原料名称": ing.get('name', ''),
                            "用量(g)": f"{amount:.2f}",
                            "原料固含(%)": solid_content_val,
                            "固体质量(g)": f"{solid_mass:.2f}",
                            "质量占比(%)": f"{(amount/total_mass*100):.2f}" if total_mass > 0 else "0.00"
                        })
                    
                    ing_df = pd.DataFrame(ing_data)
                    st.dataframe(ing_df, use_container_width=True, hide_index=True)
                
                # 产品描述
                if product.get('description'):
                    st.markdown("**产品描述**")
                    st.info(product['description'])
            
            st.divider()
    
    # 分页控制
    if total_pages > 1:
        pag_col1, pag_col2, pag_col3 = st.columns([1, 2, 1])
        
        with pag_col1:
            if st.button("⬅️ 上一页", disabled=st.session_state.product_list_page <= 1, key="product_list_prev_page"):
                st.session_state.product_list_page -= 1
                st.rerun()
        
        with pag_col2:
            page_num = st.number_input(
                "页码",
                min_value=1,
                max_value=total_pages,
                value=st.session_state.product_list_page,
                key="product_list_page_input",
                label_visibility="collapsed"
            )
            if page_num != st.session_state.product_list_page:
                st.session_state.product_list_page = page_num
                st.rerun()
        
        with pag_col3:
            if st.button("下一页 ➡️", disabled=st.session_state.product_list_page >= total_pages, key="product_list_next_page"):
                st.session_state.product_list_page += 1
                st.rerun()

# ==================== 数据记录页-实验记录管理通用组件 ====================
def _dr_safe_parse_datetime(value):
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

def _dr_safe_parse_date(value):
    if not value:
        return None
    if hasattr(value, "year") and hasattr(value, "month") and hasattr(value, "day"):
        return value
    dt = _dr_safe_parse_datetime(value)
    if dt:
        return dt.date()
    return None

def _render_recording_experiment_manager(title, type_key, records, update_record, delete_record):
    st.divider()
    st.subheader(title)
    
    normalized_records = [r for r in (records or []) if isinstance(r, dict)]
    st.caption(f"共 {len(normalized_records)} 条记录")
    
    if "recording_mgmt_id" not in st.session_state:
        st.session_state.recording_mgmt_id = str(uuid.uuid4())[:8]
    mgmt_id = st.session_state.recording_mgmt_id
    data_manager = getattr(update_record, "__self__", None)
    
    formula_options = sorted({str(r.get("formula_name", "")).strip() for r in normalized_records if str(r.get("formula_name", "")).strip()})
    formula_options = ["全部"] + formula_options
    
    default_start = (datetime.now() - timedelta(days=30)).date()
    default_end = datetime.now().date()
    
    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns([2, 2, 2, 1])
    with filter_col1:
        keyword = st.text_input("关键词", key=f"{type_key}_rec_kw_{mgmt_id}")
    with filter_col2:
        formula_filter = st.selectbox("关联配方", options=formula_options, key=f"{type_key}_rec_formula_{mgmt_id}")
    with filter_col3:
        start_date, end_date = st.date_input(
            "创建时间范围",
            value=[default_start, default_end],
            key=f"{type_key}_rec_date_{mgmt_id}",
        )
    with filter_col4:
        page_size = st.selectbox("每页", options=[10, 20, 50], index=0, key=f"{type_key}_rec_ps_{mgmt_id}")
    
    keyword_value = (keyword or "").strip().lower()
    filtered = []
    for r in normalized_records:
        if formula_filter and formula_filter != "全部":
            if str(r.get("formula_name", "")) != formula_filter:
                continue
        created_at_dt = _dr_safe_parse_datetime(r.get("created_at"))
        if created_at_dt and start_date and end_date:
            if created_at_dt.date() < start_date or created_at_dt.date() > end_date:
                continue
        if keyword_value:
            haystack = " ".join([
                str(r.get("id", "")),
                str(r.get("formula_name", "")),
                str(r.get("operator", "")),
                str(r.get("notes", "")),
            ]).lower()
            if keyword_value not in haystack:
                continue
        filtered.append(r)
    
    filtered.sort(key=lambda x: (_dr_safe_parse_datetime(x.get("created_at")) or datetime.min), reverse=True)
    st.caption(f"筛选后 {len(filtered)} 条")
    
    selected_key = f"{type_key}_rec_selected_ids"
    selected_ids = set(st.session_state.get(selected_key, []))
    
    page_key = f"{type_key}_rec_page"
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
        if st.button("⬅️ 上一页", disabled=(page <= 1), key=f"{type_key}_rec_prev_{mgmt_id}"):
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
            key=f"{type_key}_rec_jump_{mgmt_id}",
            label_visibility="collapsed",
        )
        if int(jump_page) != int(page):
            st.session_state[page_key] = int(jump_page)
            st.rerun()
    with nav_col4:
        if st.button("下一页 ➡️", disabled=(page >= total_pages), key=f"{type_key}_rec_next_{mgmt_id}"):
            st.session_state[page_key] += 1
            st.rerun()
    
    if f"{type_key}_rec_select_all" not in st.session_state:
        st.session_state[f"{type_key}_rec_select_all"] = False
    
    action_col1, action_col2, action_col3, action_col4 = st.columns([1.2, 1.2, 2, 1.4])
    with action_col1:
        select_all = st.checkbox("全选本页", value=False, key=f"{type_key}_rec_select_all_{mgmt_id}")
    with action_col2:
        if st.button("清空选择", key=f"{type_key}_rec_clear_sel_{mgmt_id}"):
            st.session_state[selected_key] = []
            st.rerun()
    with action_col3:
        confirm_batch_delete = st.checkbox("确认删除选中记录", value=False, key=f"{type_key}_rec_confirm_del_{mgmt_id}")
        confirm_text = st.text_input(
            "请输入 '确认删除'",
            placeholder="确认删除",
            key=f"{type_key}_rec_confirm_text_{mgmt_id}",
        )
    with action_col4:
        if st.button(
            "删除选中",
            type="primary",
            disabled=(not selected_ids or not confirm_batch_delete or confirm_text != "确认删除"),
            key=f"{type_key}_rec_batch_del_{mgmt_id}",
        ):
            deleted = 0
            failed = 0
            failed_ids = []
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
                    failed_ids.append(record_id)
            st.session_state[selected_key] = []
            if deleted:
                st.success(f"已删除 {deleted} 条记录")
            if failed:
                st.error(f"删除失败 {failed} 条：{failed_ids[:20]}")
            time.sleep(0.4)
            st.rerun()
    
    edit_id_key = f"{type_key}_rec_edit_id"
    if edit_id_key not in st.session_state:
        st.session_state[edit_id_key] = None
    
    show_detail_key = f"{type_key}_rec_show_detail_ids"
    if show_detail_key not in st.session_state:
        st.session_state[show_detail_key] = {}
    
    if not page_records:
        st.info("暂无记录")
        return
    
    headers = ["选择", "ID", "关联配方", "创建时间", "操作人", "操作"]
    header_cols = st.columns([1, 1, 2.6, 2.2, 1.6, 2.4])
    for i, h in enumerate(headers):
        header_cols[i].markdown(f"**{h}**")
    st.divider()
    
    def _apply_select(record_id, checkbox_key):
        current = set(st.session_state.get(selected_key, []))
        if st.session_state.get(checkbox_key, False):
            current.add(record_id)
        else:
            current.discard(record_id)
        st.session_state[selected_key] = sorted(current)
    
    if select_all:
        for r in page_records:
            rid = r.get("id")
            if rid is None:
                continue
            ck = f"{type_key}_rec_ck_{rid}_{mgmt_id}"
            st.session_state[ck] = True
            selected_ids.add(rid)
        st.session_state[selected_key] = sorted(selected_ids)
    
    for r in page_records:
        rid = r.get("id")
        if rid is None:
            continue
        ck = f"{type_key}_rec_ck_{rid}_{mgmt_id}"
        if ck not in st.session_state:
            st.session_state[ck] = (rid in selected_ids)
        
        created_at = r.get("created_at", "")
        created_at_dt = _dr_safe_parse_datetime(created_at)
        created_at_show = created_at_dt.strftime("%Y-%m-%d %H:%M:%S") if created_at_dt else str(created_at or "")
        
        row_cols = st.columns([1, 1, 2.6, 2.2, 1.6, 2.4])
        with row_cols[0]:
            st.checkbox(
                "",
                value=bool(st.session_state.get(ck, False)),
                key=ck,
                label_visibility="collapsed",
                on_change=lambda record_id=rid, checkbox_key=ck: _apply_select(record_id, checkbox_key),
            )
        with row_cols[1]:
            st.write(rid)
        with row_cols[2]:
            st.write(str(r.get("formula_name", "")))
        with row_cols[3]:
            st.write(created_at_show)
        with row_cols[4]:
            st.write(str(r.get("operator", "")))
        with row_cols[5]:
            b1, b2, b3 = st.columns(3)
            with b1:
                if st.button("编辑", key=f"{type_key}_rec_edit_btn_{rid}_{mgmt_id}", use_container_width=True):
                    st.session_state[edit_id_key] = rid
                    st.rerun()
            with b2:
                detail_state = bool(st.session_state[show_detail_key].get(rid, False))
                label = "收起" if detail_state else "详情"
                if st.button(label, key=f"{type_key}_rec_detail_btn_{rid}_{mgmt_id}", use_container_width=True):
                    st.session_state[show_detail_key][rid] = not detail_state
                    st.rerun()
            with b3:
                if data_manager and type_key in ("mortar", "concrete"):
                    export_key = f"{type_key}_rec_export_btn_{rid}_{mgmt_id}"
                    if st.button("导出", key=export_key, use_container_width=True):
                        y_max_key = f"{type_key}_chart_y_max"
                        strength_y_max = st.session_state.get(y_max_key)
                        chart_type_key = f"{type_key}_chart_type"
                        chart_type = st.session_state.get(chart_type_key, "line")
                        link = data_manager.export_experiment_report(
                            experiment_type=type_key,
                            experiment_id=rid,
                            strength_y_max=strength_y_max,
                            strength_chart_type=chart_type,
                        )
                        if link:
                            st.success("实验报告导出成功")
                            st.markdown(link, unsafe_allow_html=True)
        
        if st.session_state[show_detail_key].get(rid, False):
            with st.expander(f"记录详情 (ID: {rid})", expanded=True):
                st.json(r)
        st.divider()
    
    editing_id = st.session_state.get(edit_id_key)
    if editing_id is None:
        return
    
    current = next((x for x in normalized_records if x.get("id") == editing_id), None)
    if not current:
        st.session_state[edit_id_key] = None
        st.rerun()
    
    form_key = f"{type_key}_rec_edit_{editing_id}_{mgmt_id}"
    with st.expander(f"✏️ 编辑记录 (ID: {editing_id})", expanded=True):
        with st.form(form_key, clear_on_submit=False):
            base1_col1, base1_col2 = st.columns(2)
            with base1_col1:
                formula_name = st.text_input("关联配方*", value=str(current.get("formula_name", "") or ""), key=f"{form_key}_formula")
            with base1_col2:
                operator = st.text_input("操作人", value=str(current.get("operator", "") or ""), key=f"{form_key}_operator")
            
            test_date_default = _dr_safe_parse_date(current.get("test_date")) or datetime.now().date()
            test_date = st.date_input("测试日期", value=test_date_default, key=f"{form_key}_test_date")
            
            notes = str(current.get("notes", "") or "")
            materials = current.get("materials") if isinstance(current.get("materials"), dict) else {}
            performance = current.get("performance") if isinstance(current.get("performance"), dict) else {}
            
            if type_key == "paste":
                p_col1, p_col2, p_col3 = st.columns(3)
                with p_col1:
                    water_cement_ratio = st.number_input("水胶比", min_value=0.0, value=float(current.get("water_cement_ratio", 0.0) or 0.0), step=0.01, key=f"{form_key}_wc")
                    cement_amount_g = st.number_input("水泥用量 (g)", min_value=0.0, value=float(current.get("cement_amount_g", 0.0) or 0.0), step=1.0, key=f"{form_key}_cement_g")
                with p_col2:
                    water_amount_g = st.number_input("用水量 (g)", min_value=0.0, value=float(current.get("water_amount_g", 0.0) or 0.0), step=0.1, key=f"{form_key}_water_g")
                    admixture_dosage_g = st.number_input("减水剂掺量 (g)", min_value=0.0, value=float(current.get("admixture_dosage_g", 0.0) or 0.0), step=0.01, key=f"{form_key}_dosage_g")
                with p_col3:
                    pass
                
                st.markdown("#### 性能指标（流动度）")
                perf_col1, perf_col2, perf_col3 = st.columns(3)
                with perf_col1:
                    flow_initial_mm = st.number_input("初始流动度(mm)", min_value=0.0, value=float(performance.get("flow_initial_mm", 0.0) or 0.0), step=1.0, key=f"{form_key}_flow_initial")
                    flow_10min_mm = st.number_input("10min流动度(mm)", min_value=0.0, value=float(performance.get("flow_10min_mm", 0.0) or 0.0), step=1.0, key=f"{form_key}_flow_10min")
                with perf_col2:
                    flow_30min_mm = st.number_input("30min流动度(mm)", min_value=0.0, value=float(performance.get("flow_30min_mm", 0.0) or 0.0), step=1.0, key=f"{form_key}_flow_30min")
                    flow_1h_mm = st.number_input("1h流动度(mm)", min_value=0.0, value=float(performance.get("flow_1h_mm", 0.0) or 0.0), step=1.0, key=f"{form_key}_flow_1h")
                with perf_col3:
                    flow_1_5h_mm = st.number_input("1.5h流动度(mm)", min_value=0.0, value=float(performance.get("flow_1_5h_mm", 0.0) or 0.0), step=1.0, key=f"{form_key}_flow_1_5h")
                    flow_2h_mm = st.number_input("2h流动度(mm)", min_value=0.0, value=float(performance.get("flow_2h_mm", 0.0) or 0.0), step=1.0, key=f"{form_key}_flow_2h")
                
                notes_val = st.text_area("实验备注", value=notes, height=120, key=f"{form_key}_notes")
                
                save, cancel = st.columns(2)
                with save:
                    submitted = st.form_submit_button("💾 保存修改", type="primary", use_container_width=True)
                with cancel:
                    cancel_btn = st.form_submit_button("❌ 取消", use_container_width=True)
                
                if submitted:
                    if not str(formula_name).strip():
                        st.error("关联配方不能为空")
                    else:
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
                            "notes": str(notes_val),
                        }
                        ok = bool(update_record(editing_id, updated_fields))
                        if ok:
                            st.success("保存成功")
                            st.session_state[edit_id_key] = None
                            time.sleep(0.3)
                            st.rerun()
                        else:
                            st.error("保存失败")
                
                if cancel_btn:
                    st.session_state[edit_id_key] = None
                    st.rerun()
            
            if type_key == "mortar":
                m_col1, m_col2, m_col3 = st.columns(3)
                with m_col1:
                    water_cement_ratio = st.number_input("水胶比", min_value=0.0, value=float(current.get("water_cement_ratio", 0.0) or 0.0), step=0.01, key=f"{form_key}_wc")
                    unit_weight = st.number_input("设计容重 (kg/m³)", min_value=0.0, value=float(current.get("unit_weight", 0.0) or 0.0), step=10.0, key=f"{form_key}_unit_weight")
                with m_col2:
                    admixture_dosage = st.number_input("减水剂掺量 (%)", min_value=0.0, value=float(current.get("admixture_dosage", 0.0) or 0.0), step=0.05, key=f"{form_key}_dosage")
                    sand_moisture = st.number_input("砂含水率 (%)", min_value=0.0, value=float(current.get("sand_moisture", 0.0) or 0.0), step=0.1, key=f"{form_key}_sand_moisture")
                with m_col3:
                    pass
                
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
                with mp_col2:
                    air_content = st.number_input("含气量 (%)", min_value=0.0, value=float(performance.get("air_content", 0.0) or 0.0), step=0.1, key=f"{form_key}_air")
                with mp_col3:
                    pass
                
                # 动态强度输入
                st.markdown("#### 抗压强度 (MPa)")
                existing_strengths = performance.get("compressive_strengths", {})
                if not existing_strengths:
                    if performance.get("strength_7d"): existing_strengths["7d"] = performance.get("strength_7d")
                    if performance.get("strength_28d"): existing_strengths["28d"] = performance.get("strength_28d")
                
                compressive_strengths = _render_strength_inputs(st, current_strengths=existing_strengths, key_prefix=f"{form_key}_edit")
                
                notes_val = st.text_area("实验备注", value=notes, height=120, key=f"{form_key}_notes")
                
                save, cancel = st.columns(2)
                with save:
                    submitted = st.form_submit_button("💾 保存修改", type="primary", use_container_width=True)
                with cancel:
                    cancel_btn = st.form_submit_button("❌ 取消", use_container_width=True)
                
                if submitted:
                    if not str(formula_name).strip():
                        st.error("关联配方不能为空")
                    else:
                        updated_fields = {
                            "formula_name": str(formula_name).strip(),
                            "operator": str(operator).strip(),
                            "test_date": test_date.strftime("%Y-%m-%d"),
                            "water_cement_ratio": float(water_cement_ratio),
                            "unit_weight": float(unit_weight),
                            "admixture_dosage": float(admixture_dosage),
                            "sand_moisture": float(sand_moisture),
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
                                "strength_7d": float(compressive_strengths.get("7d", 0.0)),
                                "strength_28d": float(compressive_strengths.get("28d", 0.0)),
                                "compressive_strengths": compressive_strengths
                            },
                            "notes": str(notes_val),
                        }
                        ok = bool(update_record(editing_id, updated_fields))
                        if ok:
                            st.success("保存成功")
                            st.session_state[edit_id_key] = None
                            time.sleep(0.3)
                            st.rerun()
                        else:
                            st.error("保存失败")
                
                if cancel_btn:
                    st.session_state[edit_id_key] = None
                    st.rerun()
            
            if type_key == "concrete":
                c_col1, c_col2, c_col3 = st.columns(3)
                with c_col1:
                    water_cement_ratio = st.number_input("水胶比", min_value=0.0, value=float(current.get("water_cement_ratio", 0.0) or 0.0), step=0.01, key=f"{form_key}_wc")
                    sand_ratio = st.number_input("砂率 (%)", min_value=0.0, value=float(current.get("sand_ratio", 0.0) or 0.0), step=0.1, key=f"{form_key}_sand_ratio")
                with c_col2:
                    unit_weight = st.number_input("设计容重 (kg/m³)", min_value=0.0, value=float(current.get("unit_weight", 0.0) or 0.0), step=10.0, key=f"{form_key}_unit_weight")
                    admixture_dosage = st.number_input("减水剂掺量 (%)", min_value=0.0, value=float(current.get("admixture_dosage", 0.0) or 0.0), step=0.05, key=f"{form_key}_dosage")
                with c_col3:
                    sand_moisture = st.number_input("砂含水率 (%)", min_value=0.0, value=float(current.get("sand_moisture", 0.0) or 0.0), step=0.1, key=f"{form_key}_sand_moisture")
                    stone_moisture = st.number_input("石含水率 (%)", min_value=0.0, value=float(current.get("stone_moisture", 0.0) or 0.0), step=0.1, key=f"{form_key}_stone_moisture")
                
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
                
                agg_col1, agg_col2, agg_col3 = st.columns(3)
                with agg_col1:
                    stone1 = st.number_input("石1", min_value=0.0, value=float(materials.get("stone1", 0.0) or 0.0), step=10.0, key=f"{form_key}_stone1")
                with agg_col2:
                    stone2 = st.number_input("石2", min_value=0.0, value=float(materials.get("stone2", 0.0) or 0.0), step=10.0, key=f"{form_key}_stone2")
                with agg_col3:
                    stone3 = st.number_input("石3", min_value=0.0, value=float(materials.get("stone3", 0.0) or 0.0), step=10.0, key=f"{form_key}_stone3")
                
                st.markdown("#### 性能指标")
                st.markdown("##### 初始性能")
                cp_col1, cp_col2, cp_col3, cp_col4 = st.columns(4)
                with cp_col1:
                    slump_mm = st.number_input("坍落度 (mm)", min_value=0.0, value=float(performance.get("slump_mm", 0.0) or 0.0), step=5.0, key=f"{form_key}_slump")
                with cp_col2:
                    slump_flow_mm = st.number_input("扩展度 (mm)", min_value=0.0, value=float(performance.get("slump_flow_mm", 0.0) or 0.0), step=10.0, key=f"{form_key}_slump_flow")
                with cp_col3:
                    air_content_percent = st.number_input("含气量 (%)", min_value=0.0, value=float(performance.get("air_content_percent", 0.0) or 0.0), step=0.1, key=f"{form_key}_air")
                with cp_col4:
                    chloride_content_percent = st.number_input("氯离子含量 (%)", min_value=0.0, value=float(performance.get("chloride_content_percent", 0.0) or 0.0), step=0.001, key=f"{form_key}_cl")
                
                cp_col5, cp_col6, cp_col7 = st.columns(3)
                with cp_col5:
                    inverted_slump_time = st.number_input("倒坍时间 (s)", min_value=0.0, value=float(performance.get("inverted_slump_time", 0.0) or 0.0), step=0.1, key=f"{form_key}_inv_slump_time")
                with cp_col6:
                    bleeding_amount = st.number_input("泌水量 (g)", min_value=0.0, value=float(performance.get("bleeding_amount", 0.0) or 0.0), step=1.0, key=f"{form_key}_bleeding")
                
                # 经时损失数据
                st.markdown("##### ⏱️ 经时损失数据")
                
                time_points = ["1h", "2h", "3h"]
                existing_loss = performance.get("time_dependent_loss", {})
                loss_data = {}
                
                # 创建表格布局
                cols = st.columns([1, 2, 2])
                cols[0].markdown("**时间点**")
                cols[1].markdown("**坍落度 (mm)**")
                cols[2].markdown("**扩展度 (mm)**")
                
                for tp in time_points:
                    tp_data = existing_loss.get(tp, {})
                    row_cols = st.columns([1, 2, 2])
                    row_cols[0].markdown(f"**{tp}**")
                    loss_slump = row_cols[1].number_input(f"{tp} 坍落度", min_value=0.0, value=float(tp_data.get("slump", 0.0) or 0.0), step=5.0, key=f"{form_key}_loss_slump_{tp}", label_visibility="collapsed")
                    loss_flow = row_cols[2].number_input(f"{tp} 扩展度", min_value=0.0, value=float(tp_data.get("flow", 0.0) or 0.0), step=10.0, key=f"{form_key}_loss_flow_{tp}", label_visibility="collapsed")
                    
                    if loss_slump > 0 or loss_flow > 0:
                        loss_data[tp] = {
                            "slump": loss_slump,
                            "flow": loss_flow
                        }
                
                # 动态强度输入
                st.markdown("#### 抗压强度 (MPa)")
                existing_strengths = performance.get("compressive_strengths", {})
                if not existing_strengths:
                    if performance.get("strength_7d_mpa"): existing_strengths["7d"] = performance.get("strength_7d_mpa")
                    if performance.get("strength_28d_mpa"): existing_strengths["28d"] = performance.get("strength_28d_mpa")
                
                compressive_strengths = _render_strength_inputs(st, current_strengths=existing_strengths, key_prefix=f"{form_key}_edit")
                
                notes_val = st.text_area("实验备注", value=notes, height=120, key=f"{form_key}_notes")
                
                save, cancel = st.columns(2)
                with save:
                    submitted = st.form_submit_button("💾 保存修改", type="primary", use_container_width=True)
                with cancel:
                    cancel_btn = st.form_submit_button("❌ 取消", use_container_width=True)
                
                if submitted:
                    if not str(formula_name).strip():
                        st.error("关联配方不能为空")
                    else:
                        updated_fields = {
                            "formula_name": str(formula_name).strip(),
                            "operator": str(operator).strip(),
                            "test_date": test_date.strftime("%Y-%m-%d"),
                            "water_cement_ratio": float(water_cement_ratio),
                            "sand_ratio": float(sand_ratio),
                            "unit_weight": float(unit_weight),
                            "admixture_dosage": float(admixture_dosage),
                            "sand_moisture": float(sand_moisture),
                            "stone_moisture": float(stone_moisture),
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
                                "actual_water": float(materials.get("actual_water", 0.0) or 0.0),
                            },
                            "performance": {
                                "slump_mm": float(slump_mm),
                                "slump_flow_mm": float(slump_flow_mm),
                                "inverted_slump_time": float(inverted_slump_time),
                                "bleeding_amount": float(bleeding_amount),
                                "time_dependent_loss": loss_data,
                                "air_content_percent": float(air_content_percent),
                                "chloride_content_percent": float(chloride_content_percent),
                                "strength_7d_mpa": float(compressive_strengths.get("7d", 0.0)),
                                "strength_28d_mpa": float(compressive_strengths.get("28d", 0.0)),
                                "compressive_strengths": compressive_strengths
                            },
                            "notes": str(notes_val),
                        }
                        ok = bool(update_record(editing_id, updated_fields))
                        if ok:
                            st.success("保存成功")
                            st.session_state[edit_id_key] = None
                            time.sleep(0.3)
                            st.rerun()
                        else:
                            st.error("保存失败")
                
                if cancel_btn:
                    st.session_state[edit_id_key] = None
                    st.rerun()

# ==================== 净浆实验模块函数 ====================
def _render_paste_experiments_tab(data_manager):
    """渲染净浆实验标签页"""
    st.subheader("🧫 净浆实验记录")
    
    # 获取数据
    synthesis_records = data_manager.get_all_synthesis_records()
    products = data_manager.get_all_products()
    # 获取所有母液
    mother_liquors = []
    if hasattr(data_manager, 'get_all_mother_liquors'):
        mother_liquors = data_manager.get_all_mother_liquors()
    
    # 获取历史净浆实验数据（用于导入标准样品数据）
    paste_experiments = []
    if hasattr(data_manager, 'get_all_paste_experiments'):
        paste_experiments = data_manager.get_all_paste_experiments()
    
    # 获取可关联的配方选项
    paste_formula_options = []
    
    # 1. 母液选项
    if mother_liquors:
        for ml in mother_liquors:
            label = ml['name']
            source = ml.get('source_type', '')
            if source == 'production':
                batch = ml.get('batch_number', '')
                if batch:
                    label += f" (批号:{batch})"
            # Include ID for robust matching
            paste_formula_options.append(f"母液: {label} (ID:{ml['id']})")

    # 2. 合成实验选项 (保留以兼容旧数据，或者如果用户仍想直接关联合成记录)
    if synthesis_records:
        paste_formula_options.extend([
            f"合成实验: {r['formula_id']}" for r in synthesis_records
        ])
    
    # 3. 成品选项
    if products:
        for p in products:
            label = p['product_name']
            batch = p.get('batch_number', '')
            if batch:
                label += f" (批号:{batch})"
            paste_formula_options.append(f"成品: {label}")
    
    if "paste_form_id" not in st.session_state:
        st.session_state.paste_form_id = str(uuid.uuid4())[:8]
    
    reset_col1, reset_col2 = st.columns([1, 5])
    with reset_col1:
        if st.button("重置表单", key="paste_reset_form", type="secondary"):
            st.session_state.paste_form_id = str(uuid.uuid4())[:8]
            st.rerun()
    
    form_id = st.session_state.paste_form_id
    
    st.markdown("### 实验设置")
    
    # 第一排：实验目的 和 测试日期
    row1_col1, row1_col2 = st.columns(2)
    with row1_col1:
        experiment_purpose = st.radio("实验目的", ["性能对比测试", "生产检测"], horizontal=True, key=f"paste_purpose_{form_id}")
    with row1_col2:
        test_date = st.date_input("测试日期", datetime.now(), key=f"paste_date_{form_id}")
        
    # 第二排：关联配方 和 关联实验
    row2_col1, row2_col2 = st.columns(2)
    with row2_col1:
        if paste_formula_options:
            formula_name = st.selectbox("关联配方/母液*", 
                                      options=paste_formula_options,
                                      key=f"paste_formula_{form_id}")
        else:
            st.warning("请先创建母液、合成实验或成品减水剂")
            formula_name = None
    
    with row2_col2:
        # 获取所有实验用于关联 (来自实验管理)
        all_experiments = []
        if hasattr(data_manager, 'get_all_experiments'):
            all_experiments = data_manager.get_all_experiments()
        
        exp_options = ["无"] + [f"{exp['name']} - {exp.get('description', '')}" for exp in all_experiments]
        related_experiment_str = st.selectbox("关联实验",
                                            options=exp_options,
                                            key=f"paste_related_exp_{form_id}")
    
    # 第三排：水胶比 和 用水量
    row3_col1, row3_col2 = st.columns(2)
    with row3_col1:
        water_cement_ratio = st.number_input("水胶比*", 
                                            min_value=0.1, 
                                            max_value=1.0,
                                            value=0.29,
                                            step=0.01,
                                            key=f"paste_wc_ratio_{form_id}")
    with row3_col2:
        water_amount = st.number_input("用水量 (g)*", 
                                      min_value=0.0,
                                      value=87.0,
                                      step=0.1,
                                      key=f"paste_water_{form_id}")
        
    # 第四排：水泥用量 和 减水剂掺量
    row4_col1, row4_col2 = st.columns(2)
    with row4_col1:
        cement_amount = st.number_input("水泥用量 (g)*", 
                                       min_value=100.0,
                                       value=300.0,
                                       step=1.0,
                                       key=f"paste_cement_{form_id}")
    with row4_col2:
        admixture_dosage = st.number_input("减水剂掺量 (g)*", 
                                          min_value=0.0,
                                          max_value=10.0,
                                          value=0.2,
                                          step=0.01,
                                          key=f"paste_dosage_{form_id}")
    
    # 🧪 匀质性检测 (仅当选择了母液时显示更有意义，但Form内无法动态隐藏，除非用rerun，这里常驻显示)
    st.markdown("### 🧪 匀质性检测")
    st.caption("填写此部分将自动更新关联母液的属性")
    ml_prop_col1, ml_prop_col2, ml_prop_col3 = st.columns(3)
    ml_verify_solid = ml_prop_col1.number_input("固含 (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.1, key=f"paste_ml_solid_{form_id}")
    ml_verify_ph = ml_prop_col2.number_input("pH值", min_value=0.0, max_value=14.0, value=0.0, step=0.1, key=f"paste_ml_ph_{form_id}")
    ml_verify_density = ml_prop_col3.number_input("密度 (g/cm³)", min_value=0.0, value=0.0, step=0.01, key=f"paste_ml_density_{form_id}")

    # 实例化流动度组件
    fluidity_widget = PasteFluidityWidget(f"paste_fluidity_{form_id}")
    
    with st.expander("📊 性能指标（流动度）", expanded=False):
        
        # 准备标准样品数据默认值
        std_defaults = None
        
        # 如果是生产检测，处理标准样品选择
        if experiment_purpose == "生产检测":
            # 选择标准样品（来自母液管理）
            std_sample_list = ["自定义/无"]
            if mother_liquors:
                for ml in mother_liquors:
                    label = ml['name']
                    source = ml.get('source_type', '')
                    if source == 'production':
                        batch = ml.get('batch_number', '')
                        if batch:
                            label += f" (批号:{batch})"
                    std_sample_list.append(f"{label}")
            
            std_sample_str = st.selectbox("选择标准样品 (来自母液管理)", std_sample_list, key=f"paste_std_sample_select_{form_id}")
            
            if std_sample_str != "自定义/无":
                # 根据名称查找 ID (因为去掉了 ID 显示，需要反查)
                selected_std_id = None
                for ml in mother_liquors:
                     # 重建 label 逻辑来匹配
                    label = ml['name']
                    source = ml.get('source_type', '')
                    if source == 'production':
                        batch = ml.get('batch_number', '')
                        if batch:
                            label += f" (批号:{batch})"
                    
                    if label == std_sample_str:
                        selected_std_id = ml['id']
                        break
                
                if selected_std_id:
                    # 查找最近一次使用该母液的净浆实验数据
                    relevant_exps = []
                    for e in paste_experiments:
                         # 这里原来的逻辑是匹配 ID，现在 formula_name 可能也没有 ID 了
                         # 但如果 formula_name 之前存的是带 ID 的字符串，我们需要兼容
                         # 或者如果新存的 formula_name 只有 label，我们需要按 label 匹配
                         
                         # 情况1: 旧数据带 ID "(ID:123)"
                         # 情况2: 新数据只有 label
                         
                         e_formula = e.get("formula_name", "")
                         if not e_formula: continue
                         
                         # 尝试从 e_formula 提取 ID 匹配
                         import re
                         match = re.search(r"\(ID:(\d+)\)", e_formula)
                         if match:
                             if int(match.group(1)) == int(selected_std_id):
                                 relevant_exps.append(e)
                         else:
                             # 尝试按名称匹配 (去掉前缀 "母液: ")
                             clean_name = e_formula.replace("母液: ", "").strip()
                             if clean_name == std_sample_str:
                                 relevant_exps.append(e)

                    if relevant_exps:
                        # 按日期降序排序
                        relevant_exps.sort(key=lambda x: x.get("test_date", ""), reverse=True)
                        latest = relevant_exps[0]
                        perf = latest.get("performance", {}) 
                        if not perf and "performance_data" in latest:
                            perf = latest["performance_data"]
                        
                        if perf:
                            # 传递所有历史数据，让 Widget 决定如何解析
                            std_defaults = perf
                            st.info(f"已自动加载标准样品 ({std_sample_str}) 最近一次实验数据 ({latest.get('test_date')})")
                            
                            # 检查是否需要重新加载（避免覆盖用户的手动修改）
                            last_loaded_key = f"paste_last_std_{form_id}"
                            if st.session_state.get(last_loaded_key) != selected_std_id:
                                fluidity_widget.load_defaults(std_defaults)
                                st.session_state.last_loaded_key = selected_std_id
                                
                        else:
                            st.caption("未找到该标准样品的历史流动度数据")
                    else:
                        st.caption("未找到该标准样品的历史实验记录")
        
        # 渲染输入界面
        fluidity_widget.render_input_section(experiment_purpose, std_defaults)
    
    notes = st.text_area("实验备注", height=80, key=f"paste_notes_{form_id}")
    
    # 使用表单提交按钮
    submitted = st.button("保存净浆实验", type="primary")
    if submitted:
            if formula_name and water_cement_ratio > 0:
                # 组合日期时间
                current_time = datetime.now().time()
                test_datetime_str = datetime.combine(test_date, current_time).strftime("%Y-%m-%d %H:%M")
                
                # 获取流动度数据
                fluidity_data = fluidity_widget.get_data()
                performance_data = fluidity_data.copy()
                
                # 如果是生产检测，保存选中的标准样品名称
                if experiment_purpose == "生产检测":
                    std_key = f"paste_std_sample_select_{form_id}"
                    if std_key in st.session_state:
                         performance_data["standard_sample_name"] = st.session_state[std_key]

                experiment_data = {
                    "formula_name": formula_name,
                    "related_experiment": related_experiment_str if related_experiment_str != "无" else None,
                    "experiment_purpose": experiment_purpose,
                    "test_date": test_datetime_str,
                    "water_cement_ratio": water_cement_ratio,
                    "cement_amount_g": cement_amount,
                    "water_amount_g": water_amount,
                    "admixture_dosage_g": admixture_dosage,
                    "performance": performance_data,
                    "notes": notes,
                    "operator": st.session_state.get("username", "Unknown"),
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                # 1. 保存净浆实验
                if data_manager.add_paste_experiment(experiment_data):
                    st.success("净浆实验数据保存成功！")
                    
                    # Reset form ID to clear inputs
                    st.session_state.paste_form_id = str(uuid.uuid4())[:8]
                    
                    # 2. 检查并更新母液属性 (反馈机制)
                    # formula_name 格式: "母液: {name}" (原来带 ID，现在可能不带)
                    if formula_name.startswith("母液:"):
                        try:
                            # 尝试解析 ID (如果字符串里还有 ID)
                            ml_id = None
                            import re
                            match = re.search(r"\(ID:(\d+)\)", formula_name)
                            if match:
                                ml_id = int(match.group(1))
                            else:
                                # 按名称反查 ID
                                ml_name_to_find = formula_name.replace("母液: ", "").strip()
                                # 再次加载母液列表以查找
                                all_mls = data_manager.get_all_mother_liquors()
                                for ml in all_mls:
                                    label = ml['name']
                                    source = ml.get('source_type', '')
                                    if source == 'production':
                                        batch = ml.get('batch_number', '')
                                        if batch:
                                            label += f" (批号:{batch})"
                                    if label == ml_name_to_find:
                                        ml_id = ml['id']
                                        break
                            
                            if ml_id:
                                # 构建更新数据 (仅当输入值大于0时才更新)
                                ml_updates = {}
                                update_msg = []
                                
                                if ml_verify_solid > 0:
                                    ml_updates["solid_content"] = ml_verify_solid
                                    update_msg.append(f"固含->{ml_verify_solid}%")
                                if ml_verify_ph > 0:
                                    ml_updates["ph_value"] = ml_verify_ph
                                    update_msg.append(f"pH->{ml_verify_ph}")
                                if ml_verify_density > 0:
                                    ml_updates["density"] = ml_verify_density
                                    update_msg.append(f"密度->{ml_verify_density}")
                                
                                if ml_updates and hasattr(data_manager, 'update_mother_liquor'):
                                    if data_manager.update_mother_liquor(ml_id, ml_updates):
                                        st.info(f"🔄 已同步更新母液({ml_name_to_find if not match else ''})属性: {', '.join(update_msg)}")
                                    else:
                                        st.warning("⚠️ 母液属性更新失败")
                            else:
                                pass # 找不到 ID，忽略更新
                        except Exception as e:
                            st.warning(f"⚠️ 解析母液ID或更新时出错: {e}")

                    time.sleep(1.0) # 稍作延迟以便用户看到提示
                    
                    # 成功后重置表单ID以清空内容
                    st.session_state.paste_form_id = str(uuid.uuid4())[:8]
                    st.rerun()
                else:
                    st.error("净浆实验数据保存失败，请重试")
    
    _render_recording_experiment_manager(
        title="📋 已保存净浆实验（查看 / 查询 / 编辑 / 删除）",
        type_key="paste",
        records=data_manager.get_all_paste_experiments(),
        update_record=data_manager.update_paste_experiment,
        delete_record=data_manager.delete_paste_experiment,
    )

# ==================== 砂浆实验模块函数 ====================
def _render_mortar_experiments_tab(data_manager):
    """渲染砂浆实验标签页"""
    st.subheader("🏗️ 砂浆实验记录")
    
    synthesis_records = data_manager.get_all_synthesis_records()
    products = data_manager.get_all_products()
    mother_liquors = data_manager.get_all_mother_liquors()
    raw_materials = data_manager.get_all_raw_materials()
    
    mortar_formula_options = []
    if synthesis_records:
        mortar_formula_options.extend([f"合成实验: {r['formula_id']}" for r in synthesis_records])
    if products:
        for p in products:
            label = p['product_name']
            batch = p.get('batch_number', '')
            if batch:
                label += f" (批号:{batch})"
            mortar_formula_options.append(f"成品: {label}")
    if mother_liquors:
        for m in mother_liquors:
            label = m.get('mother_liquor_name', '未命名')
            batch = m.get('batch_number', '')
            if batch:
                label += f" (批号:{batch})"
            mortar_formula_options.append(f"母液: {label}")
    
    if "mortar_form_id" not in st.session_state:
        st.session_state.mortar_form_id = str(uuid.uuid4())[:8]
    
    reset_col1, reset_col2 = st.columns([1, 5])
    with reset_col1:
        if st.button("重置表单", key="mortar_reset_form", type="secondary"):
            st.session_state.mortar_form_id = str(uuid.uuid4())[:8]
            st.rerun()
    
    form_id = st.session_state.mortar_form_id
    # Form removed to allow dynamic test recipes
    if True:
        st.markdown("### 配合比设计")
        
        if mortar_formula_options:
            selected_formulas = st.multiselect(
                "关联减水剂配方*",
                options=mortar_formula_options,
                key=f"mortar_formula_{form_id}"
            )
            formula_name = ", ".join(selected_formulas) if selected_formulas else None
        else:
            st.warning("请先创建合成实验或成品减水剂")
            formula_name = None
        
        # 成型时间 (精确到分钟)
        dt_col1, dt_col2 = st.columns(2)
        with dt_col1:
            test_date_input = st.date_input("实验日期*", datetime.now(), key=f"mortar_date_{form_id}")
        with dt_col2:
            test_time_input = st.time_input("成型时间*", datetime.now(), key=f"mortar_time_{form_id}")
        
        # 初始化材料数据 (如果不存在)
        binders_key = f"binders_df_{form_id}"
        aggregates_key = f"aggregates_df_{form_id}"
        
        if binders_key not in st.session_state:
            st.session_state[binders_key] = pd.DataFrame([
                {"删除": False, "材料名称": "水泥", "用量(g)": 450.0},
                {"删除": False, "材料名称": "矿物外加剂1", "用量(g)": 0.0},
                {"删除": False, "材料名称": "矿物外加剂2", "用量(g)": 0.0},
            ])
            
        if aggregates_key not in st.session_state:
            st.session_state[aggregates_key] = pd.DataFrame([
                {"删除": False, "材料名称": "砂1", "用量(g)": 1350.0},
                {"删除": False, "材料名称": "砂2", "用量(g)": 0.0},
            ])

        # 预先计算总用量以便在上方显示
        current_binders = st.session_state[binders_key]
        current_aggregates = st.session_state[aggregates_key]
        
        # 兼容旧数据结构，如果没有"删除"列则添加
        if "删除" not in current_binders.columns:
            current_binders.insert(0, "删除", False)
            st.session_state[binders_key] = current_binders
            
        if "删除" not in current_aggregates.columns:
            current_aggregates.insert(0, "删除", False)
            st.session_state[aggregates_key] = current_aggregates
        
        # 过滤掉已标记删除的行进行计算（虽然UI上可能还没反应，但为了逻辑严谨）
        # 实际上 data_editor 会直接修改 session_state，我们只需要在这里处理删除逻辑
        
        # (已移除自动删除逻辑，改为手动点击按钮删除)
            
        total_binder_calc = current_binders["用量(g)"].sum() if not current_binders.empty else 0.0
        total_sand_calc = current_aggregates["用量(g)"].sum() if not current_aggregates.empty else 0.0

        col1, col2 = st.columns(2)
        with col1:
            water_cement_ratio = st.number_input(
                "水胶比*",
                min_value=0.1,
                max_value=1.0,
                value=0.4,
                step=0.01,
                key=f"mortar_wc_ratio_{form_id}"
            )
            
            sand_moisture = st.number_input(
                "砂含水率 (%)",
                min_value=0.0,
                max_value=20.0,
                value=3.0,
                step=0.1,
                key=f"mortar_sand_moisture_{form_id}"
            )

        with col2:
            admixture_dosage = st.number_input(
                "减水剂掺量 (%)*",
                min_value=0.0,
                max_value=5.0,
                value=1.0,
                step=0.05,
                key=f"mortar_dosage_{form_id}"
            )
        
        with st.expander("📦 材料用量 (g)", expanded=True):
            b_col, a_col = st.columns(2)
            
            with b_col:
                st.markdown("#### 胶凝材料")
                # 自动重置序号从1开始
                if not st.session_state[binders_key].empty:
                    st.session_state[binders_key] = st.session_state[binders_key].reset_index(drop=True)
                    st.session_state[binders_key].index = st.session_state[binders_key].index + 1

                # 移动端优化：增加删除列，通过勾选+按钮删除
                edited_binders = st.data_editor(
                    st.session_state[binders_key],
                    num_rows="dynamic",
                    column_config={
                        "_index": st.column_config.Column("序号"),
                        "删除": st.column_config.CheckboxColumn("选择", width="small", help="勾选后点击下方按钮删除"),
                        "材料名称": st.column_config.TextColumn("名称", required=True),
                        "用量(g)": st.column_config.NumberColumn("用量(g)", min_value=0.0, step=10.0, format="%.1f")
                    },
                    use_container_width=True,
                    key=f"editor_binders_{form_id}"
                )
                st.session_state[binders_key] = edited_binders
                
                if st.button("🗑️ 删除选中材料", key=f"btn_del_binders_{form_id}"):
                    if "删除" in st.session_state[binders_key].columns:
                        st.session_state[binders_key] = st.session_state[binders_key][
                            ~st.session_state[binders_key]["删除"].fillna(False)
                        ]
                        st.rerun()

            with a_col:
                st.markdown("#### 骨料")
                # 自动重置序号从1开始
                if not st.session_state[aggregates_key].empty:
                    st.session_state[aggregates_key] = st.session_state[aggregates_key].reset_index(drop=True)
                    st.session_state[aggregates_key].index = st.session_state[aggregates_key].index + 1

                edited_aggregates = st.data_editor(
                    st.session_state[aggregates_key],
                    num_rows="dynamic",
                    column_config={
                        "_index": st.column_config.Column("序号"),
                        "删除": st.column_config.CheckboxColumn("选择", width="small", help="勾选后点击下方按钮删除"),
                        "材料名称": st.column_config.TextColumn("名称", required=True),
                        "用量(g)": st.column_config.NumberColumn("用量(g)", min_value=0.0, step=10.0, format="%.1f")
                    },
                    use_container_width=True,
                    key=f"editor_aggregates_{form_id}"
                )
                st.session_state[aggregates_key] = edited_aggregates

                if st.button("🗑️ 删除选中骨料", key=f"btn_del_aggregates_{form_id}"):
                    if "删除" in st.session_state[aggregates_key].columns:
                        st.session_state[aggregates_key] = st.session_state[aggregates_key][
                            ~st.session_state[aggregates_key]["删除"].fillna(False)
                        ]
                        st.rerun()
            
            st.markdown("#### 自动计算")
            calc_cols = st.columns(3)
            
            # 重新获取最新值进行下方展示
            total_binder = edited_binders["用量(g)"].sum() if not edited_binders.empty else 0.0
            total_sand = edited_aggregates["用量(g)"].sum() if not edited_aggregates.empty else 0.0
            
            water_amount = total_binder * water_cement_ratio
            water_from_sand = total_sand * sand_moisture / 100
            actual_water = water_amount - water_from_sand
            
            total_materials = total_binder + total_sand + water_amount + (total_binder * admixture_dosage / 100)
            
            with calc_cols[0]:
                st.metric("总胶凝材料", f"{total_binder:.1f} g")
                st.metric("计算用水量", f"{water_amount:.1f} g")
            with calc_cols[1]:
                st.metric("实际用水量", f"{actual_water:.1f} g")
                st.metric("砂含水引入", f"{water_from_sand:.1f} g")
            with calc_cols[2]:
                st.metric("总材料量", f"{total_materials:.1f} g")
        
        # ----------------- 测试配方模块 (新增) -----------------
        st.markdown("### 🧪 测试配方与性能")
        
        # 初始化配方列表状态
        recipes_key = f"mortar_test_recipes_{form_id}"
        if recipes_key not in st.session_state:
            st.session_state[recipes_key] = []
            
        # --- 1. 全局指标配置 ---
        with st.expander("⚙️ 性能指标配置", expanded=True):
            st.caption("选择需要记录的性能指标，表格将自动更新列")
            conf_c1, conf_c2, conf_c3 = st.columns(3)
            with conf_c1:
                target_ages = st.multiselect(
                    "力学性能龄期",
                    options=["1d", "3d", "7d", "14d", "28d", "56d"],
                    default=["7d", "28d"],
                    key=f"cfg_ages_{form_id}"
                )
            with conf_c2:
                target_flows = st.multiselect(
                    "流动度测试点",
                    options=["初始", "10min", "30min", "60min", "90min", "120min"],
                    default=["初始", "30min", "60min"],
                    key=f"cfg_flows_{form_id}"
                )
            with conf_c3:
                record_setting_time = st.checkbox("记录凝结时间 (初凝/终凝)", value=True, key=f"cfg_set_time_{form_id}")

        # --- 2. 配方管理 ---
        # 操作栏：添加配方 | 删除选中
        op_col1, op_col2 = st.columns([1, 5])
        with op_col1:
            if st.button("➕ 添加测试配方", key=f"add_test_recipe_{form_id}"):
                new_idx = len(st.session_state[recipes_key]) + 1
                st.session_state[recipes_key].append({
                    "id": str(uuid.uuid4()),
                    "name": f"测试配方 {new_idx}",
                    "components": [],
                    "selected": False
                })
                st.rerun()
        with op_col2:
            # 检查是否有选中的配方
            has_selected = any(r.get("selected", False) for r in st.session_state[recipes_key])
            if has_selected:
                if st.button("🗑️ 删除选中配方", key=f"del_selected_recipes_{form_id}", type="secondary"):
                    st.session_state[recipes_key] = [r for r in st.session_state[recipes_key] if not r.get("selected", False)]
                    st.rerun()
            
        # 准备选项列表
        comp_options = ["请选择..."]
        comp_options.extend([f"母液: {ml['name']}" for ml in mother_liquors])
        comp_options.extend([f"原料: {rm['name']}" for rm in raw_materials])
            
        # --- 3. 配方组分定义 (列式布局) ---
        if st.session_state[recipes_key]:
            st.markdown("#### 配方组分定义")
            
            # 设置每行最大显示配方数 (调整为4以增加单个卡片宽度)
            MAX_COLS = 4
            recipes = st.session_state[recipes_key]
            total_recipes = len(recipes)
            
            # 按 MAX_COLS 分组
            for i in range(0, total_recipes, MAX_COLS):
                # 当前行的配方子集
                row_recipes = recipes[i : i + MAX_COLS]
                # 创建列 (即使当前行只有1个配方，也创建 MAX_COLS 个列，确保宽度一致且不占满全屏)
                cols = st.columns(MAX_COLS)
                
                for idx, recipe in enumerate(row_recipes):
                    recipe_id = recipe["id"]
                    # 真正的配方索引
                    r_idx = i + idx
                    
                    with cols[idx]:
                        # 外层容器
                        with st.container(border=True):
                            # 选择框 + 名称
                            h_col1, h_col2 = st.columns([0.2, 0.8])
                            with h_col1:
                                is_selected = st.checkbox(
                                    "选择", 
                                    value=recipe.get("selected", False),
                                    key=f"select_recipe_{recipe_id}",
                                    label_visibility="collapsed"
                                )
                                recipe["selected"] = is_selected
                            with h_col2:
                                recipe_name = st.text_input(
                                    "配方名称",
                                    value=recipe.get("name", f"测试配方 {r_idx + 1}"),
                                    key=f"recipe_name_{recipe_id}",
                                    label_visibility="collapsed"
                                )
                                recipe["name"] = recipe_name
                            
                            st.markdown("---")
                            # 组分展示
                            if recipe["components"]:
                                for comp in recipe["components"]:
                                    # 优化显示：名称单独一行以完整显示，勾选和用量在第二行
                                    
                                    # 第一行：组分名称
                                    curr_val = comp.get("name", "请选择...")
                                    if curr_val not in comp_options: curr_val = "请选择..."
                                    comp["name"] = st.selectbox(
                                        "组分", comp_options,
                                        index=comp_options.index(curr_val),
                                        key=f"n_{recipe_id}_{comp['id']}",
                                        label_visibility="collapsed"
                                    )
                                    
                                    # 第二行：勾选 | 用量
                                    r2_c1, r2_c2 = st.columns([0.2, 0.8])
                                    with r2_c1:
                                        # 垂直居中稍微hack一下，或者直接放checkbox
                                        st.write("") # 占位让checkbox下沉一点点（可选）
                                        comp["selected"] = st.checkbox(
                                            "选择",
                                            value=comp.get("selected", False),
                                            key=f"sel_c_{recipe_id}_{comp['id']}",
                                            label_visibility="collapsed"
                                        )
                                    with r2_c2:
                                        comp["dosage"] = st.number_input(
                                            "用量 (g)", value=float(comp.get("dosage", 0.0)), step=0.1,
                                            key=f"d_{recipe_id}_{comp['id']}",
                                            label_visibility="collapsed",
                                            placeholder="用量"
                                        )
                                    
                                    # 加个分隔线或者间距，让不同组分区分开（因为现在变成了两行）
                                    st.markdown("<hr style='margin: 5px 0; border: none; border-top: 1px dashed rgba(49, 51, 63, 0.2);'>", unsafe_allow_html=True)
                            
                            # 操作按钮
                            btn_c1, btn_c2 = st.columns(2)
                            with btn_c1:
                                if st.button("➕ 组分", key=f"add_comp_{recipe_id}", use_container_width=True):
                                    recipe["components"].append({
                                        "id": str(uuid.uuid4()),
                                        "name": "请选择...",
                                        "dosage": 0.0,
                                        "selected": False
                                    })
                                    st.rerun()
                            with btn_c2:
                                has_sel_c = any(c.get("selected", False) for c in recipe["components"])
                                if st.button("🗑️ 组分", key=f"del_c_{recipe_id}", type="secondary", disabled=not has_sel_c, use_container_width=True):
                                    recipe["components"] = [c for c in recipe["components"] if not c.get("selected", False)]
                                    st.rerun()

            # --- 4. 性能数据总表 (Matrix) ---
            st.markdown("#### 📊 性能数据汇总表")
            
            # 构建 DataFrame 数据结构
            # 1. 初始化列结构
            data_cols = {"序号": [], "配方名称": [], "配方ID": []}
            
            # 凝结时间列
            if record_setting_time:
                data_cols["初凝时间(min)"] = []
                data_cols["终凝时间(min)"] = []
            
            # 流动度列
            for fp in target_flows:
                data_cols[f"流动度_{fp}(mm)"] = []
            
            # 强度列
            for age in target_ages:
                data_cols[f"抗压_{age}(MPa)"] = []
                
            # 2. 填充现有数据 (如果有)
            # 我们需要一个 session_state key 来存储这个表格的数据，以防 rerun 丢失编辑
            # 但是 st.data_editor 可以直接绑定 session_state
            
            perf_matrix_key = f"perf_matrix_{form_id}"
            
            # 从 recipes 同步基础信息到表格数据
            # 注意：这里采用了"每次重绘都重建基础结构，但尝试保留用户输入"的策略
            # 或者更简单：直接从 session_state 读取上次的 editor 数据，如果 recipe 变了则调整行
            
            current_df = pd.DataFrame(data_cols)
            
            # 尝试获取旧数据用于保留输入值
            old_df = st.session_state.get(perf_matrix_key)
            old_data_map = {}
            
            # 安全检查：确保 old_df 是 DataFrame
            if old_df is not None:
                if isinstance(old_df, pd.DataFrame) and not old_df.empty:
                    # 建立 ID -> Row 映射
                    if "配方ID" in old_df.columns:
                        for _, row in old_df.iterrows():
                            old_data_map[row["配方ID"]] = row.to_dict()
                elif isinstance(old_df, (dict, list)):
                    # 如果意外得到了 dict 或 list (可能是由于重置或其他原因)，尝试解析或直接忽略
                    # 只有当它是 list 且包含 dict 时才有意义，但通常 data_editor 返回 DataFrame
                    pass
            
            # 构建新行数据
            new_rows = []
            for r_idx, r in enumerate(st.session_state[recipes_key]):
                r_id = r["id"]
                row_data = {
                    "序号": r_idx + 1,
                    "配方ID": r_id,
                    "配方名称": r.get("name", "未命名")
                }
                
                # 尝试从旧数据恢复值，否则默认 0
                prev_row = old_data_map.get(r_id, {})
                
                if record_setting_time:
                    row_data["初凝时间(min)"] = prev_row.get("初凝时间(min)", 0)
                    row_data["终凝时间(min)"] = prev_row.get("终凝时间(min)", 0)
                
                for fp in target_flows:
                    col_name = f"流动度_{fp}(mm)"
                    row_data[col_name] = prev_row.get(col_name, 0.0)
                    
                for age in target_ages:
                    col_name = f"抗压_{age}(MPa)"
                    row_data[col_name] = prev_row.get(col_name, 0.0)
                
                new_rows.append(row_data)
            
            if new_rows:
                current_df = pd.DataFrame(new_rows)
            
            # 准备显示的列顺序 (隐藏配方ID)
            display_cols = ["序号", "配方名称"]
            if record_setting_time:
                display_cols.extend(["初凝时间(min)", "终凝时间(min)"])
            for fp in target_flows:
                display_cols.append(f"流动度_{fp}(mm)")
            for age in target_ages:
                display_cols.append(f"抗压_{age}(MPa)")
            
            # 配置列编辑器
            column_config = {
                "序号": st.column_config.NumberColumn(disabled=True, width="small", format="%d"),
                "配方名称": st.column_config.Column(disabled=True, width="medium"), # 名称在上方编辑
            }
            
            if record_setting_time:
                column_config["初凝时间(min)"] = st.column_config.NumberColumn(min_value=0, step=5)
                column_config["终凝时间(min)"] = st.column_config.NumberColumn(min_value=0, step=5)
            
            for fp in target_flows:
                column_config[f"流动度_{fp}(mm)"] = st.column_config.NumberColumn(min_value=0, step=5.0, format="%.1f")
            
            for age in target_ages:
                column_config[f"抗压_{age}(MPa)"] = st.column_config.NumberColumn(min_value=0.0, step=0.1, format="%.1f")

            # 渲染编辑器
            edited_df = st.data_editor(
                current_df,
                key=perf_matrix_key,
                column_config=column_config,
                column_order=display_cols,
                hide_index=True,
                use_container_width=True,
                disabled=["序号", "配方名称"] 
            )

        else:
            st.info("请点击上方按钮添加测试配方")

        # ----------------- 结束测试配方模块 -----------------

        notes = st.text_area("实验备注", height=100, key=f"mortar_notes_{form_id}")
        
        submitted = st.button("保存砂浆实验", type="primary", key=f"mortar_save_btn_{form_id}")
        if submitted:
            # 获取测试配方数据
            current_recipes = st.session_state.get(recipes_key, [])
            
            # 获取性能表格数据
            perf_df = st.session_state.get(perf_matrix_key)
            
            if not current_recipes:
                st.error("请至少添加一个测试配方")
            elif formula_name and water_cement_ratio > 0:
                # 组合日期时间
                test_datetime = datetime.combine(test_date_input, test_time_input)
                
                # 建立 ID -> Performance 映射
                perf_map = {}
                if perf_df is not None:
                    if isinstance(perf_df, pd.DataFrame) and not perf_df.empty:
                        for _, row in perf_df.iterrows():
                            rid = row.get("配方ID")
                            if rid:
                                perf_map[rid] = row
                    # 如果是 dict (虽然不应该发生，但在异常状态下可能)，尝试兼容
                    elif isinstance(perf_df, dict):
                        pass
                
                # 处理每个配方的性能数据
                final_recipes = []
                for recipe in current_recipes:
                    r_id = recipe["id"]
                    row_data = perf_map.get(r_id, {})
                    
                    # 1. 提取流动度
                    current_flows = []
                    initial_flow = 0.0
                    for fp in target_flows:
                        val = row_data.get(f"流动度_{fp}(mm)", 0.0)
                        if val > 0:
                            current_flows.append({"time": fp, "value": float(val)})
                            if fp == "初始":
                                initial_flow = float(val)
                    
                    # 2. 提取凝结时间
                    st_i = 0
                    st_f = 0
                    if record_setting_time:
                        st_i = int(row_data.get("初凝时间(min)", 0))
                        st_f = int(row_data.get("终凝时间(min)", 0))

                    # 3. 提取力学性能
                    compressive_strengths = {}
                    for age in target_ages:
                        val = row_data.get(f"抗压_{age}(MPa)", 0.0)
                        if val > 0:
                            compressive_strengths[age] = float(val)
                    
                    # 为了兼容性，填充常用字段
                    s_7d = compressive_strengths.get("7d", 0.0)
                    s_28d = compressive_strengths.get("28d", 0.0)
                    
                    # 构建配方性能数据对象
                    recipe_performance = {
                        "flow": initial_flow,
                        "flows": current_flows,
                        "setting_time": {
                            "initial": st_i,
                            "final": st_f
                        },
                        "compressive_strengths": compressive_strengths,
                        "strength_7d": s_7d,
                        "strength_28d": s_28d
                    }
                    
                    # 更新配方对象
                    recipe_with_perf = recipe.copy()
                    recipe_with_perf["performance"] = recipe_performance
                    final_recipes.append(recipe_with_perf)
                
                # 获取材料数据
                binders_df = st.session_state.get(f"binders_df_{form_id}")
                aggregates_df = st.session_state.get(f"aggregates_df_{form_id}")
                
                binders_list = []
                if binders_df is not None and not binders_df.empty:
                    # 转换 DataFrame 为 list of dicts
                    # 假设列名是 "材料名称" 和 "用量(g)"
                    # 为了数据存储的规范性，我们转为英文 key
                    for _, row in binders_df.iterrows():
                        binders_list.append({
                            "name": row.get("材料名称", "未知"),
                            "dosage": float(row.get("用量(g)", 0.0))
                        })
                
                aggregates_list = []
                if aggregates_df is not None and not aggregates_df.empty:
                    for _, row in aggregates_df.iterrows():
                        aggregates_list.append({
                            "name": row.get("材料名称", "未知"),
                            "dosage": float(row.get("用量(g)", 0.0))
                        })
                
                # 重新计算一次总水量，确保数据一致性
                total_binder_val = sum([b["dosage"] for b in binders_list])
                total_sand_val = sum([a["dosage"] for a in aggregates_list])
                
                calc_water = total_binder_val * water_cement_ratio
                water_from_sand_val = total_sand_val * sand_moisture / 100
                calc_actual_water = calc_water - water_from_sand_val

                experiment_data = {
                    "formula_name": formula_name,
                    "test_date": test_datetime.strftime("%Y-%m-%d %H:%M"),
                    "water_cement_ratio": water_cement_ratio,
                    # "unit_weight": unit_weight, # 已移除
                    "admixture_dosage": admixture_dosage,
                    "sand_moisture": sand_moisture,
                    "materials": {
                        "binders": binders_list,
                        "aggregates": aggregates_list,
                        "water": calc_water,
                        "actual_water": calc_actual_water,
                        # 保留总量数据方便快速查询
                        "total_binder": total_binder_val,
                        "total_aggregate": total_sand_val
                    },
                    "test_recipes": final_recipes,
                    "notes": notes,
                    "operator": st.session_state.get("username", "Unknown")
                }
                
                if data_manager.add_mortar_experiment(experiment_data):
                    st.success("砂浆实验数据保存成功！")
                    
                    # 清理表单状态
                    st.session_state.mortar_form_id = str(uuid.uuid4())[:8]
                    if recipes_key in st.session_state:
                        del st.session_state[recipes_key]
                    if perf_matrix_key in st.session_state:
                        del st.session_state[perf_matrix_key]
                    
                    # 清理每个配方的动态 key
                    for r in current_recipes:
                        rid = r["id"]
                        keys_to_del = [
                            f"recipe_name_{rid}", f"add_comp_{rid}", f"del_c_{rid}"
                        ]
                        for k in keys_to_del:
                            if k in st.session_state:
                                del st.session_state[k]
                    
                    time.sleep(0.5)
                    st.rerun()
    
    st.markdown("### 导出选项")
    col_exp1, col_exp2 = st.columns(2)
    with col_exp1:
        default_y = float(st.session_state.get("mortar_chart_y_max", 0.0) or 0.0)
        y_max = st.number_input(
            "强度曲线Y轴上限(MPa)",
            min_value=0.0,
            value=default_y,
            step=5.0,
            key="mortar_chart_y_max_input"
        )
        st.session_state["mortar_chart_y_max"] = y_max if y_max > 0 else None
    with col_exp2:
        default_type = st.session_state.get("mortar_chart_type", "line")
        default_index = 0 if default_type == "line" else 1
        chart_label = st.selectbox(
            "强度图表类型",
            options=["折线图", "柱状图"],
            index=default_index,
            key="mortar_chart_type_select"
        )
        st.session_state["mortar_chart_type"] = "line" if chart_label == "折线图" else "bar"
    
    _render_recording_experiment_manager(
        title="📋 砂浆实验数据列表",
        type_key="mortar",
        records=data_manager.get_all_mortar_experiments(),
        update_record=data_manager.update_mortar_experiment,
        delete_record=data_manager.delete_mortar_experiment,
    )

# ==================== 混凝土实验模块函数 ====================
def _render_concrete_experiments_tab(data_manager):
    """渲染混凝土实验标签页"""
    
    # 获取数据
    synthesis_records = data_manager.get_all_synthesis_records()
    products = data_manager.get_all_products()
    mother_liquors = data_manager.get_all_mother_liquors()
    raw_materials = data_manager.get_all_raw_materials()
    
    # 获取可关联的配方选项
    concrete_formula_options = []
    if synthesis_records:
        concrete_formula_options.extend([
            f"合成实验: {r['formula_id']}" for r in synthesis_records
        ])
    if products:
        for p in products:
            label = p['product_name']
            batch = p.get('batch_number', '')
            if batch:
                label += f" (批号:{batch})"
            concrete_formula_options.append(f"成品: {label}")
    if mother_liquors:
        for m in mother_liquors:
            label = m.get('mother_liquor_name', '未命名')
            batch = m.get('batch_number', '')
            if batch:
                label += f" (批号:{batch})"
            concrete_formula_options.append(f"母液: {label}")
    
    if "concrete_form_id" not in st.session_state:
        st.session_state.concrete_form_id = str(uuid.uuid4())[:8]
    
    with st.expander("🏢 混凝土实验记录 (点击展开/收起)", expanded=True):
        reset_col1, reset_col2 = st.columns([1, 5])
        with reset_col1:
            if st.button("重置表单", key="concrete_reset_form", type="secondary"):
                st.session_state.concrete_form_id = str(uuid.uuid4())[:8]
                # 清除相关 session state
                form_id = st.session_state.concrete_form_id
                keys_to_clear = [
                    f"concrete_binders_df_{form_id}", 
                    f"concrete_aggregates_df_{form_id}",
                    f"concrete_test_recipes_{form_id}"
                ]
                for k in keys_to_clear:
                    if k in st.session_state:
                        del st.session_state[k]
                st.rerun()
        
        form_id = st.session_state.concrete_form_id
        # Form removed to allow dynamic test recipes
        if True:
            st.markdown("### 配合比设计")
            
            if concrete_formula_options:
                selected_formulas = st.multiselect("关联减水剂配方*", 
                                          options=concrete_formula_options,
                                          key=f"concrete_formula_{form_id}")
                formula_name = ", ".join(selected_formulas) if selected_formulas else None
            else:
                st.warning("请先创建合成实验或成品减水剂")
                formula_name = None
            
            # 成型时间 (精确到分钟)
        dt_col1, dt_col2 = st.columns(2)
        with dt_col1:
            test_date_input = st.date_input("实验日期*", datetime.now(), key=f"concrete_date_{form_id}")
        with dt_col2:
            test_time_input = st.time_input("成型时间*", datetime.now(), key=f"concrete_time_{form_id}")
            
        # Wrapper to maintain indentation of the original form content
        if True:
            # 基础参数
            col1, col2 = st.columns(2)
            with col1:
                water_cement_ratio = st.number_input("水胶比*", 
                                                    min_value=0.1, 
                                                    max_value=1.0,
                                                    value=0.4,
                                                    step=0.01,
                                                    key=f"concrete_wc_ratio_{form_id}")
                
                sand_ratio = st.number_input("砂率 (%)*", 
                                            min_value=0.0,
                                            max_value=100.0,
                                            value=42.0,
                                            step=0.1,
                                            key=f"concrete_sand_ratio_{form_id}")
                
                unit_weight = st.number_input("设计容重 (kg/m³)", 
                                            min_value=2000.0,
                                            max_value=3000.0,
                                            value=2400.0,
                                            step=10.0,
                                            key=f"concrete_weight_{form_id}")
            
            with col2:
                admixture_dosage = st.number_input("减水剂掺量 (%)*", 
                                                  min_value=0.0,
                                                  max_value=5.0,
                                                  value=1.0,
                                                  step=0.05,
                                                  key=f"concrete_dosage_{form_id}")
                
                sand_moisture = st.number_input("砂含水率 (%)", 
                                               min_value=0.0,
                                               max_value=20.0,
                                               value=3.0,
                                               step=0.1,
                                               key=f"concrete_sand_moisture_{form_id}")
                
                stone_moisture = st.number_input("石含水率 (%)", 
                                                min_value=0.0,
                                                max_value=20.0,
                                                value=1.0,
                                                step=0.1,
                                                key=f"concrete_stone_moisture_{form_id}")
            
            # 初始化材料数据
            binders_key = f"concrete_binders_df_{form_id}"
            aggregates_key = f"concrete_aggregates_df_{form_id}"
            
            if binders_key not in st.session_state:
                st.session_state[binders_key] = pd.DataFrame([
                    {"材料名称": "水泥", "用量(kg/m³)": 300.0},
                    {"材料名称": "矿粉", "用量(kg/m³)": 60.0},
                    {"材料名称": "粉煤灰", "用量(kg/m³)": 40.0},
                ])
            
            if aggregates_key not in st.session_state:
                st.session_state[aggregates_key] = pd.DataFrame([
                    {"材料名称": "机制砂", "用量(kg/m³)": 750.0},
                    {"材料名称": "河砂", "用量(kg/m³)": 0.0},
                    {"材料名称": "5-10mm石子", "用量(kg/m³)": 400.0},
                    {"材料名称": "10-20mm石子", "用量(kg/m³)": 600.0},
                ])

            # 预先计算总用量以便在上方显示
            current_binders = st.session_state[binders_key]
            current_aggregates = st.session_state[aggregates_key]
            
            total_binder_calc = current_binders["用量(kg/m³)"].sum() if not current_binders.empty else 0.0
            total_aggregate_calc = current_aggregates["用量(kg/m³)"].sum() if not current_aggregates.empty else 0.0
            
            # 材料用量 (动态表格)
            with st.expander("📦 材料用量 (kg/m³)", expanded=True):
                b_col, a_col = st.columns(2)
                
                with b_col:
                    st.markdown("#### 胶凝材料")
                    # 自动重置序号从1开始
                    if not st.session_state[binders_key].empty:
                        st.session_state[binders_key] = st.session_state[binders_key].reset_index(drop=True)
                        st.session_state[binders_key].index = st.session_state[binders_key].index + 1

                    edited_binders = st.data_editor(
                        st.session_state[binders_key],
                        num_rows="dynamic",
                        column_config={
                            "_index": st.column_config.Column("序号"),
                            "删除": st.column_config.CheckboxColumn("选择", width="small", help="勾选后点击下方按钮删除"),
                            "材料名称": st.column_config.TextColumn("名称", required=True),
                            "用量(kg/m³)": st.column_config.NumberColumn("用量", min_value=0.0, step=5.0, format="%.1f")
                        },
                        use_container_width=True,
                        key=f"editor_conc_binders_{form_id}"
                    )
                    st.session_state[binders_key] = edited_binders
                    
                    if st.button("🗑️ 删除选中材料", key=f"btn_del_conc_binders_{form_id}"):
                        if "删除" in st.session_state[binders_key].columns:
                            st.session_state[binders_key] = st.session_state[binders_key][
                                ~st.session_state[binders_key]["删除"].fillna(False)
                            ]
                            st.rerun()

                with a_col:
                    st.markdown("#### 骨料")
                    # 自动重置序号从1开始
                    if not st.session_state[aggregates_key].empty:
                        st.session_state[aggregates_key] = st.session_state[aggregates_key].reset_index(drop=True)
                        st.session_state[aggregates_key].index = st.session_state[aggregates_key].index + 1

                    edited_aggregates = st.data_editor(
                        st.session_state[aggregates_key],
                        num_rows="dynamic",
                        column_config={
                            "_index": st.column_config.Column("序号"),
                            "删除": st.column_config.CheckboxColumn("选择", width="small", help="勾选后点击下方按钮删除"),
                            "材料名称": st.column_config.TextColumn("名称", required=True),
                            "用量(kg/m³)": st.column_config.NumberColumn("用量", min_value=0.0, step=5.0, format="%.1f")
                        },
                        use_container_width=True,
                        key=f"editor_conc_aggregates_{form_id}"
                    )
                    st.session_state[aggregates_key] = edited_aggregates

                    if st.button("🗑️ 删除选中骨料", key=f"btn_del_conc_aggregates_{form_id}"):
                        if "删除" in st.session_state[aggregates_key].columns:
                            st.session_state[aggregates_key] = st.session_state[aggregates_key][
                                ~st.session_state[aggregates_key]["删除"].fillna(False)
                            ]
                            st.rerun()
                
                # 自动计算
                st.markdown("#### 自动计算")
                calc_cols = st.columns(3)
                
                # 重新获取最新值
                total_binder = edited_binders["用量(kg/m³)"].sum() if not edited_binders.empty else 0.0
                total_aggregate = edited_aggregates["用量(kg/m³)"].sum() if not edited_aggregates.empty else 0.0
                
                # 计算用水量
                water_amount = total_binder * water_cement_ratio
                
                # 估算砂和石的用量 (这里其实无法区分砂和石，只能算出总骨料含水)
                # 假设用户在骨料表中自己区分了砂和石，我们这里只能简单计算总骨料含水引入
                # 为了更精确，我们假设骨料表里包含"砂"字的为砂，包含"石"字的为石
                total_sand_est = 0.0
                total_stone_est = 0.0
                
                if not edited_aggregates.empty:
                    for _, row in edited_aggregates.iterrows():
                        name = row.get("材料名称", "")
                        dosage = row.get("用量(kg/m³)", 0.0)
                        if "砂" in name:
                            total_sand_est += dosage
                        else:
                            # 默认为石
                            total_stone_est += dosage
                
                water_from_sand = total_sand_est * sand_moisture / 100
                water_from_stone = total_stone_est * stone_moisture / 100
                actual_water = water_amount - water_from_sand - water_from_stone
                
                total_materials = (
                    total_binder + 
                    total_aggregate + 
                    water_amount + 
                    (total_binder * admixture_dosage / 100)
                )
                
                with calc_cols[0]:
                    st.metric("总胶凝材料", f"{total_binder:.1f} kg")
                    st.metric("计算用水量", f"{water_amount:.1f} kg")
                
                with calc_cols[1]:
                    st.metric("实际用水量", f"{actual_water:.1f} kg")
                    st.metric("砂含水引入", f"{water_from_sand:.1f} kg")
                
                with calc_cols[2]:
                    st.metric("石含水引入", f"{water_from_stone:.1f} kg")
                    st.metric("总材料量", f"{total_materials:.1f} kg")

            # ----------------- 测试配方与性能模块 -----------------
            st.markdown("### 🧪 测试配方与性能")
            
            # 初始化配方列表状态
            recipes_key = f"concrete_test_recipes_{form_id}"
            if recipes_key not in st.session_state:
                st.session_state[recipes_key] = []
                
            # --- 1. 全局指标配置 ---
            with st.expander("⚙️ 性能指标配置", expanded=True):
                st.caption("选择需要记录的性能指标，表格将自动更新列")
                conf_c1, conf_c2, conf_c3 = st.columns(3)
                with conf_c1:
                    target_ages = st.multiselect(
                        "力学性能龄期",
                        options=["1d", "3d", "7d", "14d", "28d", "56d"],
                        default=["3d", "7d", "28d"],
                        key=f"conc_cfg_ages_{form_id}"
                    )
                with conf_c2:
                    target_points = st.multiselect(
                        "工作性测试点",
                        options=["初始", "1h", "2h", "3h"],
                        default=["初始", "1h"],
                        key=f"conc_cfg_points_{form_id}"
                    )
                with conf_c3:
                    record_setting_time = st.checkbox("记录凝结时间", value=False, key=f"conc_cfg_set_time_{form_id}")
                    record_air_content = st.checkbox("记录含气量", value=True, key=f"conc_cfg_air_{form_id}")

            # --- 2. 配方管理 ---
            op_col1, op_col2 = st.columns([1, 5])
            with op_col1:
                if st.button("➕ 添加测试配方", key=f"add_conc_recipe_{form_id}"):
                    new_idx = len(st.session_state[recipes_key]) + 1
                    st.session_state[recipes_key].append({
                        "id": str(uuid.uuid4()),
                        "name": f"测试配方 {new_idx}",
                        "components": [],
                        "selected": False
                    })
                    st.rerun()
            with op_col2:
                has_selected = any(r.get("selected", False) for r in st.session_state[recipes_key])
                if has_selected:
                    if st.button("🗑️ 删除选中配方", key=f"del_sel_conc_recipes_{form_id}", type="secondary"):
                        st.session_state[recipes_key] = [r for r in st.session_state[recipes_key] if not r.get("selected", False)]
                        st.rerun()
                
            # 准备选项列表
            comp_options = ["请选择..."]
            comp_options.extend([f"母液: {ml['name']}" for ml in mother_liquors])
            comp_options.extend([f"原料: {rm['name']}" for rm in raw_materials])
            
            # --- 3. 配方组分 (列式布局) ---
            if st.session_state[recipes_key]:
                st.markdown("#### 配方组分定义")
                
                MAX_COLS = 3 # 混凝土内容较多，改为3列
                recipes = st.session_state[recipes_key]
                total_recipes = len(recipes)
                
                for i in range(0, total_recipes, MAX_COLS):
                    row_recipes = recipes[i : i + MAX_COLS]
                    cols = st.columns(MAX_COLS)
                    
                    for idx, recipe in enumerate(row_recipes):
                        recipe_id = recipe["id"]
                        r_idx = i + idx
                        
                        with cols[idx]:
                            with st.container(border=True):
                                # 头部
                                h_col1, h_col2 = st.columns([0.2, 0.8])
                                with h_col1:
                                    recipe["selected"] = st.checkbox("选", value=recipe.get("selected", False), key=f"sel_r_{recipe_id}", label_visibility="collapsed")
                                with h_col2:
                                    recipe["name"] = st.text_input("名称", value=recipe.get("name", f"配方 {r_idx+1}"), key=f"nm_{recipe_id}", label_visibility="collapsed")
                                
                                st.markdown("---")
                                # 组分
                                if recipe["components"]:
                                    for comp in recipe["components"]:
                                        curr_val = comp.get("name", "请选择...")
                                        if curr_val not in comp_options: curr_val = "请选择..."
                                        comp["name"] = st.selectbox("组分", comp_options, index=comp_options.index(curr_val), key=f"cn_{recipe_id}_{comp['id']}", label_visibility="collapsed")
                                        
                                        c_row = st.columns([0.2, 0.8])
                                        with c_row[0]:
                                            comp["selected"] = st.checkbox("选", value=comp.get("selected", False), key=f"c_sel_{recipe_id}_{comp['id']}", label_visibility="collapsed")
                                        with c_row[1]:
                                            comp["dosage"] = st.number_input("用量", value=float(comp.get("dosage", 0.0)), step=0.1, key=f"cd_{recipe_id}_{comp['id']}", label_visibility="collapsed")
                                
                                # 组分操作
                                c_op1, c_op2 = st.columns(2)
                                with c_op1:
                                    if st.button("➕ 组分", key=f"add_c_{recipe_id}"):
                                        recipe["components"].append({"id": str(uuid.uuid4()), "name": "请选择...", "dosage": 0.0, "selected": False})
                                        st.rerun()
                                with c_op2:
                                    if any(c.get("selected", False) for c in recipe["components"]):
                                        if st.button("🗑️ 删除", key=f"del_c_{recipe_id}"):
                                            recipe["components"] = [c for c in recipe["components"] if not c.get("selected", False)]
                                            st.rerun()

                # --- 4. 性能数据总表 (Matrix) ---
                st.markdown("#### 📊 性能数据汇总表")
                
                # 构建 DataFrame 数据结构
                data_cols = {"序号": [], "配方名称": [], "配方ID": []}
                
                if record_air_content:
                    data_cols["含气量(%)"] = []
                
                if record_setting_time:
                    data_cols["初凝时间(min)"] = []
                    data_cols["终凝时间(min)"] = []
                
                for tp in target_points:
                    data_cols[f"坍落度_{tp}(mm)"] = []
                    data_cols[f"扩展度_{tp}(mm)"] = []
                
                for age in target_ages:
                    data_cols[f"抗压_{age}(MPa)"] = []
                
                # 准备数据
                perf_matrix_key = f"concrete_perf_matrix_{form_id}"
                current_df = pd.DataFrame(data_cols)
                
                # 尝试保留旧输入
                old_df = st.session_state.get(perf_matrix_key)
                old_data_map = {}
                if old_df is not None and isinstance(old_df, pd.DataFrame) and not old_df.empty:
                    if "配方ID" in old_df.columns:
                        for _, row in old_df.iterrows():
                            old_data_map[row["配方ID"]] = row.to_dict()
                
                new_rows = []
                for r_idx, r in enumerate(st.session_state[recipes_key]):
                    r_id = r["id"]
                    row_data = {
                        "序号": r_idx + 1,
                        "配方ID": r_id,
                        "配方名称": r.get("name", "未命名")
                    }
                    
                    prev_row = old_data_map.get(r_id, {})
                    
                    # 尝试从配方对象本身恢复 (如果是首次切换视图)
                    perf = r.get("performance", {})
                    
                    if record_air_content:
                        val = prev_row.get("含气量(%)") if "含气量(%)" in prev_row else perf.get("air_content", 0.0)
                        row_data["含气量(%)"] = float(val or 0.0)
                    
                    if record_setting_time:
                        val_i = prev_row.get("初凝时间(min)") if "初凝时间(min)" in prev_row else perf.get("setting_initial", 0)
                        row_data["初凝时间(min)"] = int(val_i or 0)
                        val_f = prev_row.get("终凝时间(min)") if "终凝时间(min)" in prev_row else perf.get("setting_final", 0)
                        row_data["终凝时间(min)"] = int(val_f or 0)
                    
                    for tp in target_points:
                        tp_key = f"p_{tp}"
                        perf_tp = perf.get(tp_key, {})
                        
                        col_sl = f"坍落度_{tp}(mm)"
                        val_sl = prev_row.get(col_sl) if col_sl in prev_row else perf_tp.get("slump", 0.0)
                        row_data[col_sl] = float(val_sl or 0.0)
                        
                        col_sp = f"扩展度_{tp}(mm)"
                        val_sp = prev_row.get(col_sp) if col_sp in prev_row else perf_tp.get("spread", 0.0)
                        row_data[col_sp] = float(val_sp or 0.0)
                    
                    for age in target_ages:
                        col_str = f"抗压_{age}(MPa)"
                        perf_str = perf.get("strengths", {})
                        val_str = prev_row.get(col_str) if col_str in prev_row else perf_str.get(age, 0.0)
                        row_data[col_str] = float(val_str or 0.0)
                        
                    new_rows.append(row_data)
                
                if new_rows:
                    current_df = pd.DataFrame(new_rows)
                
                # 配置显示列
                display_cols = ["序号", "配方名称"]
                if record_air_content: display_cols.append("含气量(%)")
                if record_setting_time: display_cols.extend(["初凝时间(min)", "终凝时间(min)"])
                for tp in target_points:
                    display_cols.extend([f"坍落度_{tp}(mm)", f"扩展度_{tp}(mm)"])
                for age in target_ages:
                    display_cols.append(f"抗压_{age}(MPa)")
                
                # 配置编辑器
                column_config = {
                    "序号": st.column_config.NumberColumn(disabled=True, width="small", format="%d"),
                    "配方名称": st.column_config.Column(disabled=True, width="medium"),
                }
                
                if record_air_content:
                    column_config["含气量(%)"] = st.column_config.NumberColumn(min_value=0.0, step=0.1, format="%.1f")
                
                if record_setting_time:
                    column_config["初凝时间(min)"] = st.column_config.NumberColumn(min_value=0, step=5)
                    column_config["终凝时间(min)"] = st.column_config.NumberColumn(min_value=0, step=5)
                
                for tp in target_points:
                    column_config[f"坍落度_{tp}(mm)"] = st.column_config.NumberColumn(min_value=0.0, step=5.0, format="%.0f")
                    column_config[f"扩展度_{tp}(mm)"] = st.column_config.NumberColumn(min_value=0.0, step=5.0, format="%.0f")
                
                for age in target_ages:
                    column_config[f"抗压_{age}(MPa)"] = st.column_config.NumberColumn(min_value=0.0, step=0.1, format="%.1f")
                
                edited_df = st.data_editor(
                    current_df,
                    key=perf_matrix_key,
                    column_config=column_config,
                    column_order=display_cols,
                    hide_index=True,
                    use_container_width=True,
                    disabled=["序号", "配方名称"]
                )


            notes = st.text_area("实验备注", height=100, key=f"concrete_notes_{form_id}")
            
            # 使用表单提交按钮
            submitted = st.button("保存混凝土实验", type="primary", key=f"btn_save_concrete_{form_id}")
            if submitted:
                if not st.session_state.get(recipes_key):
                    st.error("请至少添加一个测试配方")
                elif formula_name and water_cement_ratio > 0:
                    # 组合日期时间
                    test_datetime = datetime.combine(test_date_input, test_time_input)
                    
                    # 收集材料数据
                    binders_df = st.session_state[binders_key]
                    aggregates_df = st.session_state[aggregates_key]
                    
                    binders_list = []
                    if not binders_df.empty:
                        for _, row in binders_df.iterrows():
                            binders_list.append({
                                "name": row.get("材料名称", "未知"),
                                "dosage": float(row.get("用量(kg/m³)", 0.0))
                            })
                            
                    aggregates_list = []
                    if not aggregates_df.empty:
                        for _, row in aggregates_df.iterrows():
                            aggregates_list.append({
                                "name": row.get("材料名称", "未知"),
                                "dosage": float(row.get("用量(kg/m³)", 0.0))
                            })

                    # 获取性能表格数据
                    perf_df = st.session_state.get(perf_matrix_key)
                    
                    # 建立 ID -> Performance 映射
                    perf_map = {}
                    if perf_df is not None:
                        if isinstance(perf_df, pd.DataFrame) and not perf_df.empty:
                            for _, row in perf_df.iterrows():
                                rid = row.get("配方ID")
                                if rid:
                                    perf_map[rid] = row
                    
                    # 处理配方数据
                    final_recipes = []
                    for r in st.session_state[recipes_key]:
                        r_id = r["id"]
                        
                        # 从矩阵中获取最新性能数据
                        row_data = perf_map.get(r_id, {})
                        
                        # 构建性能对象
                        perf_obj = {}
                        
                        # 1. 含气量
                        if record_air_content:
                            perf_obj["air_content"] = float(row_data.get("含气量(%)", 0.0))
                            
                        # 2. 凝结时间
                        if record_setting_time:
                            perf_obj["setting_initial"] = int(row_data.get("初凝时间(min)", 0))
                            perf_obj["setting_final"] = int(row_data.get("终凝时间(min)", 0))
                            
                        # 3. 工作性 (坍落度/扩展度)
                        for tp in target_points:
                            tp_key = f"p_{tp}"
                            perf_tp = {
                                "slump": float(row_data.get(f"坍落度_{tp}(mm)", 0.0)),
                                "spread": float(row_data.get(f"扩展度_{tp}(mm)", 0.0))
                            }
                            perf_obj[tp_key] = perf_tp
                            
                        # 4. 力学性能
                        strengths = {}
                        for age in target_ages:
                            val = row_data.get(f"抗压_{age}(MPa)", 0.0)
                            if val > 0:
                                strengths[age] = float(val)
                        perf_obj["strengths"] = strengths
                        
                        # 清理 key (只保留数据)并更新性能
                        clean_recipe = {
                            "id": r["id"],
                            "name": r["name"],
                            "components": r["components"],
                            "performance": perf_obj
                        }
                        final_recipes.append(clean_recipe)

                    experiment_data = {
                        "formula_name": formula_name,
                        "test_date": test_datetime.strftime("%Y-%m-%d %H:%M"),
                        "water_cement_ratio": water_cement_ratio,
                        "sand_ratio": sand_ratio,
                        "unit_weight": unit_weight,
                        "admixture_dosage": admixture_dosage,
                        "sand_moisture": sand_moisture,
                        "stone_moisture": stone_moisture,
                        "materials": {
                            "binders": binders_list,
                            "aggregates": aggregates_list,
                            "water": water_amount,
                            "actual_water": actual_water,
                            "total_binder": total_binder,
                            "total_aggregate": total_aggregate
                        },
                        "test_recipes": final_recipes,
                        "notes": notes,
                        "operator": st.session_state.get("username", "Unknown")
                    }
                    
                    if data_manager.add_concrete_experiment(experiment_data):
                        st.success("混凝土实验数据保存成功！")
                        # 清除状态
                        st.session_state.concrete_form_id = str(uuid.uuid4())[:8]
                        if recipes_key in st.session_state: del st.session_state[recipes_key]
                        if binders_key in st.session_state: del st.session_state[binders_key]
                        if aggregates_key in st.session_state: del st.session_state[aggregates_key]
                        
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("混凝土实验数据保存失败，请重试")
    
    st.markdown("### 导出选项")
    col_exp1, col_exp2 = st.columns(2)
    with col_exp1:
        default_y = float(st.session_state.get("concrete_chart_y_max", 0.0) or 0.0)
        y_max = st.number_input(
            "强度曲线Y轴上限(MPa)",
            min_value=0.0,
            value=default_y,
            step=5.0,
            key="concrete_chart_y_max_input"
        )
        st.session_state["concrete_chart_y_max"] = y_max if y_max > 0 else None
    with col_exp2:
        default_type = st.session_state.get("concrete_chart_type", "line")
        default_index = 0 if default_type == "line" else 1
        chart_label = st.selectbox(
            "强度图表类型",
            options=["折线图", "柱状图"],
            index=default_index,
            key="concrete_chart_type_select"
        )
        st.session_state["concrete_chart_type"] = "line" if chart_label == "折线图" else "bar"
    
    _render_recording_experiment_manager(
        title="📋 混凝土实验数据列表",
        type_key="concrete",
        records=data_manager.get_all_concrete_experiments(),
        update_record=data_manager.update_concrete_experiment,
        delete_record=data_manager.delete_concrete_experiment,
    )

# ==================== 数据维护模块函数 ====================
def _render_data_maintenance_tab(data_manager):
    """渲染数据维护标签页"""
    st.subheader("🛠️ 数据维护")
    st.info("在此页面进行数据的备份、恢复、导入与导出操作。")
    
    tab_backup, tab_export, tab_import = st.tabs(["📦 数据备份与恢复", "📤 导出数据", "📥 导入数据"])
    
    with tab_backup:
        st.markdown("### JSON 数据备份")
        st.write("JSON 备份包含系统的完整数据状态，是**最安全**的备份方式。建议定期下载 JSON 备份。")
        
        # Backup status
        if st.session_state.get("last_backup_time"):
            st.caption(f"上次自动备份时间: {st.session_state.last_backup_time}")
        
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            json_str = data_manager.get_json_content()
            st.download_button(
                label="⬇️ 下载 JSON 完整备份",
                data=json_str,
                file_name=f"polycarb_data_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                use_container_width=True,
                type="primary"
            )
        
        st.divider()
        st.markdown("### JSON 数据恢复")
        st.warning("⚠️ 警告：恢复备份将**完全覆盖**当前所有数据！请谨慎操作。")
        
        uploaded_json = st.file_uploader("上传 JSON 备份文件进行恢复", type=["json"], key="json_restore_uploader")
        if uploaded_json is not None:
            if st.button("🚨 确认恢复数据", type="secondary", use_container_width=True):
                string_data = uploaded_json.getvalue().decode("utf-8")
                success, msg = data_manager.import_from_json(string_data)
                if success:
                    st.success(f"✅ {msg}")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")

    with tab_export:
        st.markdown("### Excel 数据导出")
        st.write("导出为 Excel 格式，便于查看和制作报表。")
        
        if st.button("生成 Excel 导出链接", key="btn_export_excel"):
             with st.spinner("正在生成 Excel 文件..."):
                href = data_manager.export_to_excel()
                if href:
                    st.markdown(href, unsafe_allow_html=True)
                    st.success("✅ Excel 文件已生成，请点击上方链接下载。")
                else:
                    st.error("生成失败。")

    with tab_import:
        st.markdown("### Excel 数据导入")
        st.write("从 Excel 文件导入数据。支持增量导入（合并）或更新现有记录。")
        st.info("注意：Excel 导入可能无法完全还原复杂的数据结构（如配方详情），建议仅用于数据迁移或批量录入。")
        
        uploaded_excel = st.file_uploader("上传 Excel 文件", type=["xlsx", "xls"], key="excel_import_uploader")
        if uploaded_excel is not None:
             if st.button("📥 开始导入", key="btn_import_excel"):
                with st.spinner("正在导入..."):
                    success, msg = data_manager.import_from_excel(uploaded_excel)
                    if success:
                        st.success(f"✅ 导入成功: {msg}")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")

