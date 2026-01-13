import streamlit as st
from datetime import datetime
import time
import uuid
import pandas as pd
import io

def _render_batch_import(data_manager):
    st.markdown("### 📂 批量导入原材料")
    st.info("请下载模板，按照格式填写后上传。支持 Excel 文件 (.xlsx, .xls)")
    
    col_dl, col_up = st.columns([1, 2])
    
    with col_dl:
        # 1. 下载模板
        template_data = {
            "原材料名称*": ["示例原料A"],
            "物料号*": ["M1001"],
            "缩写": ["MatA"],
            "化学式": ["H2O"],
            "分子量": [18.02],
            "固含(%)": [100],
            "单价(元/吨)": [500],
            "气味": ["无"], # 无, 轻微, 中等, 强烈, 刺激性
            "存储条件": ["常温"],
            "供应商": ["示例供应商"],
            "用途*": ["母液合成,复配和助剂"], # 用逗号分隔
            "初始库存": [1000],
            "单位": ["kg"],
            "详细描述": ["这是一个示例"]
        }
        df_template = pd.DataFrame(template_data)
        
        # Create Excel in memory
        output = io.BytesIO()
        try:
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_template.to_excel(writer, index=False, sheet_name='Sheet1')
        except:
             # Fallback if xlsxwriter is missing
             with pd.ExcelWriter(output) as writer:
                df_template.to_excel(writer, index=False, sheet_name='Sheet1')
                
        excel_data = output.getvalue()
        
        st.download_button(
            label="📥 下载 Excel 模板",
            data=excel_data,
            file_name="raw_material_template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
    # 2. 上传文件
    uploaded_file = st.file_uploader("上传填写好的 Excel 文件", type=['xlsx', 'xls'])
    
    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file)
            
            # 3. 数据预览与编辑
            st.divider()
            st.markdown("### 📝 数据预览与确认")
            st.markdown("请检查并修正数据，确认无误后点击下方按钮导入。")
            
            edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)
            
            # 4. 导入逻辑
            if st.button("🚀 确认导入", type="primary"):
                success_count = 0
                fail_count = 0
                errors = []
                
                for index, row in edited_df.iterrows():
                    # Extract data
                    try:
                        # Helper to safely get value
                        def get_val(col_name, default=""):
                            if col_name in row:
                                val = row[col_name]
                                if pd.isna(val): return default
                                return val
                            return default
                            
                        name = str(get_val("原材料名称*", "")).strip()
                        mat_num = str(get_val("物料号*", "")).strip()
                        usage_str = str(get_val("用途*", "")).strip()
                        
                        if not name or not mat_num or not usage_str:
                            fail_count += 1
                            errors.append(f"第 {index+1} 行：缺少必填项 (名称、物料号或用途)")
                            continue
                            
                        # Parse usage categories (replace Chinese comma if any)
                        usage_str = usage_str.replace("，", ",")
                        
                        # Construct material dict
                        try:
                            mw = float(get_val("分子量", 0))
                        except: mw = 0.0
                        
                        try:
                            sc = float(get_val("固含(%)", 0))
                        except: sc = 0.0
                        
                        try:
                            price = float(get_val("单价(元/吨)", 0))
                        except: price = 0.0
                        
                        try:
                            stock = float(get_val("初始库存", 0))
                        except: stock = 0.0

                        new_material = {
                            "name": name,
                            "material_number": mat_num,
                            "abbreviation": str(get_val("缩写", "")),
                            "chemical_formula": str(get_val("化学式", "")),
                            "molecular_weight": mw,
                            "solid_content": sc,
                            "unit_price": price,
                            "odor": str(get_val("气味", "无")),
                            "storage_condition": str(get_val("存储条件", "")),
                            "supplier": str(get_val("供应商", "")),
                            "usage_category": usage_str,
                            "main_usage": str(get_val("详细描述", "")),
                            "stock_quantity": stock,
                            "unit": str(get_val("单位", "ton")),
                            "created_date": datetime.now().strftime("%Y-%m-%d")
                        }
                        
                        success, msg = data_manager.add_raw_material(new_material)
                        if success:
                            success_count += 1
                        else:
                            fail_count += 1
                            errors.append(f"第 {index+1} 行 ({name}): {msg}")
                            
                    except Exception as e:
                        fail_count += 1
                        errors.append(f"第 {index+1} 行：处理异常 - {str(e)}")
                
                if success_count > 0:
                    st.success(f"成功导入 {success_count} 条数据！")
                
                if fail_count > 0:
                    st.error(f"导入失败 {fail_count} 条数据")
                    with st.expander("查看失败详情", expanded=True):
                        for err in errors:
                            st.write(err)
                            
                if success_count > 0:
                    time.sleep(2)
                    st.rerun()

        except Exception as e:
            st.error(f"文件读取失败: {e}")

def render_raw_material_management(data_manager):
    """渲染原材料管理页面"""
    st.header("📦 原材料管理")
    
    # 获取原材料数据
    raw_materials = data_manager.get_all_raw_materials()
    
    form_id = "raw_add_material"
    
    with st.expander("➕ 单个添加 | 📂 批量导入 (Excel)", expanded=False):
        tab_single, tab_batch = st.tabs(["➕ 单个添加", "📂 批量导入 (Excel)"])
        
        with tab_single:
            with st.form(f"add_raw_material_form_{form_id}", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    material_name = st.text_input("原材料名称*", key=f"raw_material_name_{form_id}")
                    material_number = st.text_input("物料号*", key=f"raw_material_number_{form_id}")
                    chemical_formula = st.text_input("化学式", key=f"raw_chemical_formula_{form_id}")
                    molecular_weight = st.number_input("分子量 (g/mol)", 
                                                      min_value=0.0, 
                                                      step=0.01,
                                                      key=f"raw_molecular_weight_{form_id}")
                    solid_content = st.number_input("固含 (%)", 
                                                   min_value=0.0, 
                                                   max_value=100.0,
                                                   step=0.1,
                                                   key=f"raw_solid_content_{form_id}")
                with col2:
                    abbreviation = st.text_input("缩写", key=f"raw_abbreviation_{form_id}")
                    unit_price = st.number_input("单价 (元/吨)", 
                                                min_value=0.0,
                                                step=0.1,
                                                key=f"raw_unit_price_{form_id}")
                    odor = st.selectbox("气味", 
                                       ["无", "轻微", "中等", "强烈", "刺激性"],
                                       key=f"raw_odor_{form_id}")
                    storage_condition = st.text_input("存储条件", key=f"raw_storage_condition_{form_id}")
                    supplier = st.text_input("供应商", key=f"raw_supplier_{form_id}")
                
                usage_category_options = ["母液合成", "复配和助剂", "速凝剂"]
                usage_categories = st.multiselect("用途*", usage_category_options, key=f"raw_usage_category_{form_id}")
                
                col_inv1, col_inv2 = st.columns(2)
                
                # Check if water
                is_water_add = material_name and "水" in material_name and "减水" not in material_name
                
                with col_inv1:
                    if is_water_add:
                        st.text_input("初始库存", value="N/A (不追踪库存)", disabled=True, key=f"raw_init_stock_disp_{form_id}")
                        initial_stock = 0.0
                    else:
                        initial_stock = st.number_input("初始库存", min_value=0.0, step=0.00001, format="%g", key=f"raw_init_stock_{form_id}")
                
                with col_inv2:
                    stock_unit = st.text_input("单位 (e.g., kg, ton)", value="ton", key=f"raw_unit_{form_id}")

                main_usage = st.text_area("详细用途描述", height=60, key=f"raw_main_usage_{form_id}")
                
                # 使用表单提交按钮
                submitted = st.form_submit_button("添加原材料", type="primary")
                if submitted:
                    if material_name and material_number and usage_categories:
                        # 检查物料号是否重复
                        existing_numbers = [m.get("material_number") for m in raw_materials if m.get("material_number")]
                        if material_number in existing_numbers:
                            st.error(f"物料号 '{material_number}' 已存在！")
                        else:
                            # 检查名称+供应商是否重复
                            duplicate_exists = False
                            for m in raw_materials:
                                if m.get("name") == material_name and m.get("supplier") == supplier:
                                    duplicate_exists = True
                                    break
                            
                            if duplicate_exists:
                                st.error(f"原材料 '{material_name}' (供应商: {supplier}) 已存在！")
                            else:
                                new_material = {
                                    "name": material_name,
                                    "material_number": material_number,
                                    "abbreviation": abbreviation,
                                    "chemical_formula": chemical_formula,
                                    "molecular_weight": molecular_weight,
                                    "solid_content": solid_content,
                                    "unit_price": unit_price,
                                    "odor": odor,
                                    "storage_condition": storage_condition,
                                    "supplier": supplier,
                                    "usage_category": ",".join(usage_categories),
                                    "main_usage": main_usage,
                                    "stock_quantity": initial_stock,
                                    "unit": stock_unit,
                                    "created_date": datetime.now().strftime("%Y-%m-%d")
                                }
                                success, msg = data_manager.add_raw_material(new_material)
                                if success:
                                    # If initial stock > 0, add an inventory record too
                                    if initial_stock > 0:
                                        # We need the ID of the newly added material. 
                                        pass
                                    
                                    st.success(f"原材料 '{material_name}' 添加成功！")
                                    time.sleep(0.5)
                                    st.rerun()
                                else:
                                    st.error(f"添加失败: {msg}")
                    else:
                        st.error("请填写带*的必填项 (名称、物料号、用途)")
        
        with tab_batch:
            _render_batch_import(data_manager)
    
    # 库存操作区域
    with st.expander("🏭 库存操作 (入库/出库)", expanded=False):
        if not raw_materials:
            st.info("暂无原材料，请先添加原材料。")
        else:
            with st.form("inventory_op_form", clear_on_submit=True):
                op_col1, op_col2, op_col3 = st.columns([2, 1, 1])
                with op_col1:
                    # Create options list with ID
                    mat_options = {f"{m['name']} ({m.get('material_number', '-')})": m['id'] for m in raw_materials}
                    selected_mat_label = st.selectbox("选择原材料*", list(mat_options.keys()))
                    selected_mat_id = mat_options[selected_mat_label]
                
                with op_col2:
                    op_type = st.selectbox("操作类型*", ["入库", "出库"])
                    
                with op_col3:
                    op_qty = st.number_input("数量*", min_value=0.0, step=0.00001, format="%g")
                
                op_reason = st.text_input("备注/原因 (e.g. 采购入库, 生产领用)")
                
                op_submit = st.form_submit_button("提交库存变动", type="primary")
                
                if op_submit:
                    if op_qty > 0:
                        record_data = {
                            "material_id": selected_mat_id,
                            "type": "in" if op_type == "入库" else "out",
                            "quantity": op_qty,
                            "reason": op_reason,
                            "operator": "User", 
                            "date": datetime.now().strftime("%Y-%m-%d")
                        }
                        success, msg = data_manager.add_inventory_record(record_data)
                        if success:
                            st.success(msg)
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        st.warning("数量必须大于0")

    # 原材料列表
    st.divider()
    st.subheader("📋 原材料列表")
    
    if raw_materials:
        if "raw_material_edit_id" not in st.session_state:
            st.session_state.raw_material_edit_id = None
        if "raw_material_edit_form_id" not in st.session_state:
            st.session_state.raw_material_edit_form_id = None
        if "raw_material_delete_id" not in st.session_state:
            st.session_state.raw_material_delete_id = None
        
        # 1. 筛选与搜索
        with st.expander("🔍 筛选与搜索", expanded=True):
            f_col1, f_col2, f_col3 = st.columns([2, 1, 1])
            with f_col1:
                search_term = st.text_input("关键词搜索", 
                                          placeholder="输入名称、物料号、缩写或化学式",
                                          key="raw_material_search_input")
            
            # 获取所有供应商和用途供筛选
            all_suppliers = sorted(list(set([m.get("supplier", "") for m in raw_materials if m.get("supplier")])))
            all_usages = sorted(list(set([u.strip() for m in raw_materials for u in m.get("usage_category", "").split(",") if u.strip()])))
            
            with f_col2:
                filter_suppliers = st.multiselect("供应商", all_suppliers, key="raw_filter_suppliers")
            
            with f_col3:
                filter_usages = st.multiselect("用途", all_usages, key="raw_filter_usages")
        
        # 2. 数据过滤
        filtered_materials = raw_materials
        if search_term:
            filtered_materials = [
                m for m in filtered_materials
                if search_term.lower() in m.get("name", "").lower() or 
                search_term.lower() in m.get("chemical_formula", "").lower() or
                search_term.lower() in m.get("material_number", "").lower() or
                search_term.lower() in m.get("abbreviation", "").lower()
            ]
        
        if filter_suppliers:
            filtered_materials = [m for m in filtered_materials if m.get("supplier") in filter_suppliers]
            
        if filter_usages:
            # Check if any selected usage matches any usage of the material
            filtered_materials = [
                m for m in filtered_materials 
                if any(u in m.get("usage_category", "") for u in filter_usages)
            ]
            
        # 3. 显示表格 (使用 st.dataframe/data_editor 以适应移动端)
        if filtered_materials:
            # 构造 DataFrame
            df_display = pd.DataFrame(filtered_materials)
            
            # 整理列名和显示顺序
            # 必须包含 ID 用于操作，但不需要显示
            # 添加 Select 列用于操作
            df_display["选择"] = False
            
            # 映射列名
            column_map = {
                "name": "名称",
                "material_number": "物料号",
                "stock_quantity": "库存",
                "unit": "单位",
                "abbreviation": "缩写",
                "supplier": "供应商",
                "usage_category": "用途",
                "chemical_formula": "化学式",
                "molecular_weight": "分子量",
                "solid_content": "固含(%)",
                "unit_price": "单价"
            }
            
            # 保留需要的列
            cols_to_show = ["选择", "id"] + [c for c in column_map.keys() if c in df_display.columns]
            df_display = df_display[cols_to_show]
            
            # 重命名
            df_display = df_display.rename(columns=column_map)
            
            # 配置列
            column_config = {
                "id": None, # 隐藏 ID
                "选择": st.column_config.CheckboxColumn("选择", help="勾选以进行编辑或删除", width="small"),
                "名称": st.column_config.TextColumn("名称", width="medium", required=True),
                "物料号": st.column_config.TextColumn("物料号", width="small"),
                "库存": st.column_config.NumberColumn("库存"),
                "固含(%)": st.column_config.NumberColumn("固含(%)", format="%.1f%%"),
                "单价": st.column_config.NumberColumn("单价", format="¥%.2f"),
            }
            
            st.caption(f"共找到 {len(filtered_materials)} 条记录。勾选左侧选框进行操作。")
            
            # 显示可编辑表格 (仅 Checkbox 可编辑)
            edited_df = st.data_editor(
                df_display,
                column_config=column_config,
                disabled=[c for c in df_display.columns if c != "选择"],
                hide_index=True,
                use_container_width=True,
                key=f"raw_mat_editor_{st.session_state.get('raw_material_query_signature', 0)}" # Reset on filter change
            )
            
            # 4. 操作栏 (当有选中项时显示)
            selected_rows = edited_df[edited_df["选择"] == True]
            
            if not selected_rows.empty:
                st.info(f"已选择 {len(selected_rows)} 项")
                action_col1, action_col2, action_col3, _ = st.columns([1, 1, 1.2, 2.8])
                
                with action_col1:
                    # 编辑按钮 (仅当选中1项时可用)
                    if len(selected_rows) == 1:
                        if st.button("✏️ 编辑选中项", type="primary", use_container_width=True):
                            selected_id = int(selected_rows.iloc[0]["id"])
                            st.session_state.raw_material_edit_id = selected_id
                            st.session_state.raw_material_edit_form_id = str(uuid.uuid4())[:8]
                            st.rerun()
                    else:
                        st.button("✏️ 编辑选中项", disabled=True, help="请仅选择一项进行编辑", use_container_width=True)
                
                with action_col2:
                    # 删除按钮
                    if st.button("🗑️ 删除选中项", type="secondary", use_container_width=True):
                        # 目前仅支持单删，如果要批量删除需要循环
                        if len(selected_rows) == 1:
                            selected_id = int(selected_rows.iloc[0]["id"])
                            st.session_state.raw_material_delete_id = selected_id
                            st.rerun()
                        else:
                            st.warning("目前仅支持单项删除，请只选择一项。")

                with action_col3:
                    # 复制添加按钮
                    if st.button("📋 复制添加选中项", type="secondary", use_container_width=True):
                        success_count = 0
                        fail_count = 0
                        
                        for idx, row in selected_rows.iterrows():
                            original_id = int(row["id"])
                            original_mat = next((m for m in raw_materials if m["id"] == original_id), None)
                            
                            if original_mat:
                                new_mat = original_mat.copy()
                                if "id" in new_mat: del new_mat["id"]
                                
                                # 生成唯一后缀
                                suffix = datetime.now().strftime("%H%M%S") + str(uuid.uuid4())[:4]
                                
                                new_mat["name"] = f"{new_mat['name']}_copy"
                                if new_mat.get("material_number"):
                                    new_mat["material_number"] = f"{new_mat['material_number']}_{suffix}"
                                
                                new_mat["created_date"] = datetime.now().strftime("%Y-%m-%d")
                                new_mat["stock_quantity"] = 0 # 复制时不复制库存
                                
                                success, msg = data_manager.add_raw_material(new_mat)
                                if success:
                                    success_count += 1
                                else:
                                    fail_count += 1
                                    st.error(f"复制 {row.get('名称', '')} 失败: {msg}")
                        
                        if success_count > 0:
                            st.success(f"成功复制 {success_count} 项")
                            time.sleep(1)
                            st.rerun()

            # --------------------------------------------------------
            # 以下是原有的弹窗和编辑表单逻辑 (保持不变)
            # --------------------------------------------------------
            
            delete_id = st.session_state.get("raw_material_delete_id")
            if delete_id is not None:
                deleting_mat = next((m for m in raw_materials if m.get("id") == delete_id), None)
                if not deleting_mat:
                    st.session_state.raw_material_delete_id = None
                    st.rerun()
                
                delete_raw_material_dialog(delete_id, deleting_mat.get('name', ''), data_manager)
            
            edit_id = st.session_state.get("raw_material_edit_id")
            if edit_id is not None:
                editing_mat = next((m for m in raw_materials if m.get("id") == edit_id), None)
                if not editing_mat:
                    st.session_state.raw_material_edit_id = None
                    st.session_state.raw_material_edit_form_id = None
                    st.rerun()
                
                form_uid = st.session_state.get("raw_material_edit_form_id") or str(uuid.uuid4())[:8]
                st.session_state.raw_material_edit_form_id = form_uid
                
                with st.expander(f"✏️ 编辑原材料：{editing_mat.get('name', '')} (ID: {edit_id})", expanded=True):
                    with st.form(f"edit_raw_material_form_{form_uid}"):
                        e_col1, e_col2 = st.columns(2)
                        with e_col1:
                            e_name = st.text_input("原材料名称*", value=str(editing_mat.get("name", "")), key=f"raw_e_name_{form_uid}")
                            e_material_number = st.text_input("物料号", value=str(editing_mat.get("material_number", "")), key=f"raw_e_material_number_{form_uid}")
                            e_chemical = st.text_input("化学式", value=str(editing_mat.get("chemical_formula", "")), key=f"raw_e_chem_{form_uid}")
                            e_mw = st.number_input(
                                "分子量 (g/mol)",
                                min_value=0.0,
                                step=0.01,
                                value=float(editing_mat.get("molecular_weight") or 0.0),
                                key=f"raw_e_mw_{form_uid}",
                            )
                            e_solid = st.number_input(
                                "固含 (%)",
                                min_value=0.0,
                                max_value=100.0,
                                step=0.1,
                                value=float(editing_mat.get("solid_content") or 0.0),
                                key=f"raw_e_solid_{form_uid}",
                            )
                        with e_col2:
                            e_abbreviation = st.text_input("缩写", value=str(editing_mat.get("abbreviation", "")), key=f"raw_e_abbreviation_{form_uid}")
                            e_price = st.number_input(
                                "单价 (元/吨)",
                                min_value=0.0,
                                step=0.1,
                                value=float(editing_mat.get("unit_price") or 0.0),
                                key=f"raw_e_price_{form_uid}",
                            )
                            odor_options = ["无", "轻微", "中等", "强烈", "刺激性"]
                            current_odor = editing_mat.get("odor", "无")
                            e_odor = st.selectbox(
                                "气味",
                                options=odor_options,
                                index=odor_options.index(current_odor) if current_odor in odor_options else 0,
                                key=f"raw_e_odor_{form_uid}",
                            )
                            e_storage = st.text_input("存储条件", value=str(editing_mat.get("storage_condition", "")), key=f"raw_e_storage_{form_uid}")
                            e_supplier = st.text_input("供应商", value=str(editing_mat.get("supplier", "")), key=f"raw_e_supplier_{form_uid}")
                        
                        e_inv_col1, e_inv_col2 = st.columns(2)
                        
                        e_name_val = editing_mat.get("name", "") or ""
                        water_names = ["水", "自来水", "纯水", "去离子水", "工业用水", "生产用水"]
                        is_water_edit = e_name_val.strip() in water_names
                        
                        with e_inv_col1:
                            e_stock = st.number_input(
                                "当前库存",
                                min_value=0.0,
                                step=0.00001,
                                format="%g",
                                value=float(editing_mat.get("stock_quantity") or 0.0),
                                key=f"raw_e_stock_{form_uid}"
                            )
                        with e_inv_col2:
                            if editing_mat.get("name") and "水" in editing_mat.get("name") and "减水" not in editing_mat.get("name"):
                                e_unit = st.text_input("单位", value=str(editing_mat.get("unit", "ton")), key=f"raw_e_unit_{form_uid}")
                            else:
                                e_unit = st.text_input("单位", value=str(editing_mat.get("unit", "kg")), key=f"raw_e_unit_{form_uid}")

                        e_usage_category_options = ["母液合成", "复配和助剂", "速凝剂"]
                        current_usage_category_str = editing_mat.get("usage_category", "")
                        current_usage_categories = []
                        if current_usage_category_str:
                            current_usage_categories = [c.strip() for c in current_usage_category_str.split(",")]
                        
                        # Filter out invalid options just in case
                        current_usage_categories = [c for c in current_usage_categories if c in e_usage_category_options]
                        
                        e_usage_categories = st.multiselect(
                            "用途*", 
                            options=e_usage_category_options,
                            default=current_usage_categories,
                            key=f"raw_e_usage_category_{form_uid}"
                        )
                        e_usage = st.text_area("详细用途描述", value=str(editing_mat.get("main_usage", "")), height=60, key=f"raw_e_usage_{form_uid}")
                        
                        b1, b2, b3 = st.columns(3)
                        with b1:
                            save = st.form_submit_button("💾 保存修改", type="primary", use_container_width=True)
                        with b2:
                            cancel = st.form_submit_button("❌ 取消", use_container_width=True)
                        with b3:
                            reset = st.form_submit_button("🔄 重置", use_container_width=True)
                        
                        if save:
                            if not e_name.strip() or not e_material_number.strip() or not e_usage_categories:
                                st.error("请填写带*的必填项 (名称、物料号、用途)")
                            else:
                                # 检查物料号是否重复 (排除自己)
                                other_numbers = [m.get("material_number") for m in raw_materials if m.get("id") != edit_id and m.get("material_number")]
                                if e_material_number.strip() in other_numbers:
                                     st.error(f"物料号 '{e_material_number.strip()}' 已存在！")
                                else:
                                     # 检查名称+供应商是否重复 (排除自己)
                                     duplicate_exists = False
                                     for m in raw_materials:
                                         if m.get("id") != edit_id:
                                             if m.get("name") == e_name.strip() and m.get("supplier") == e_supplier.strip():
                                                 duplicate_exists = True
                                                 break
                                     
                                     if duplicate_exists:
                                         st.error(f"原材料 '{e_name.strip()}' (供应商: {e_supplier.strip()}) 已存在！")
                                     else:
                                        updated_fields = {
                                            "name": e_name.strip(),
                                            "material_number": e_material_number.strip(),
                                            "abbreviation": e_abbreviation.strip(),
                                            "chemical_formula": e_chemical.strip(),
                                            "molecular_weight": float(e_mw),
                                            "solid_content": float(e_solid),
                                            "unit_price": float(e_price),
                                            "odor": e_odor,
                                            "storage_condition": e_storage.strip(),
                                            "supplier": e_supplier.strip(),
                                            "stock_quantity": float(e_stock),
                                            "unit": e_unit.strip(),
                                            "usage_category": ",".join(e_usage_categories),
                                            "main_usage": e_usage.strip(),
                                        }
                                        success, msg = data_manager.update_raw_material(edit_id, updated_fields)
                                        if success:
                                            st.success("保存成功")
                                            st.session_state.raw_material_edit_id = None
                                            st.session_state.raw_material_edit_form_id = None
                                            time.sleep(0.5)
                                            st.rerun()
                                        else:
                                            st.error(f"保存失败: {msg}")
                        
                        if cancel:
                            st.session_state.raw_material_edit_id = None
                            st.session_state.raw_material_edit_form_id = None
                            time.sleep(0.2)
                            st.rerun()
                        
                        if reset:
                            st.session_state.raw_material_edit_form_id = str(uuid.uuid4())[:8]
                            st.rerun()
        else:
            st.info("没有找到匹配的原材料")
    else:
        st.info("暂无原材料数据，请添加第一个原材料")

@st.dialog("删除原材料确认")
def delete_raw_material_dialog(material_id, material_name, data_manager):
    st.markdown("#### ⚠️ 确认删除")
    st.error("此操作将永久删除该原材料，不可恢复！")
    st.markdown(f"- 名称：**{material_name}**")
    st.markdown(f"- ID：`{material_id}`")
    
    confirm_text = st.text_input(
        "请输入 '确认删除' 以继续：",
        key=f"raw_delete_confirm_text_{material_id}",
        placeholder="请输入 '确认删除'",
    )
    
    c1, c2 = st.columns(2)
    with c1:
        if st.button(
            "✅ 确认删除",
            type="primary",
            use_container_width=True,
            disabled=(confirm_text != "确认删除"),
            key=f"raw_delete_confirm_btn_{material_id}",
        ):
            ok, msg = data_manager.delete_raw_material(material_id)
            
            if ok:
                st.session_state.raw_material_delete_id = None
                st.success(msg)
                time.sleep(0.6)
                st.rerun()
            else:
                st.error(f"删除失败: {msg}")
    with c2:
        if st.button(
            "❌ 取消",
            use_container_width=True,
            key=f"raw_delete_cancel_btn_{material_id}",
        ):
            st.session_state.raw_material_delete_id = None
            st.rerun()
