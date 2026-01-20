import streamlit as st
from datetime import datetime
import time
import uuid
import pandas as pd
import io
from utils.unit_helper import convert_quantity, normalize_unit

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
                    # 新增评估字段
                    supplier_rating = st.slider("供应商评分 (1-5)", 1, 5, 3, key=f"raw_supplier_rating_{form_id}")
                    qc_status = st.selectbox("QC 状态", ["合格", "待检", "不合格", "冻结"], key=f"raw_qc_status_{form_id}")
                
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
                                    "supplier_rating": supplier_rating,
                                    "qc_status": qc_status,
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
                
                # 预先获取选中的原材料ID (为了获取单位)
                # 由于是在 form 内部，我们只能获取当前的 selection，
                # 但 st.selectbox 在 form 提交前不会更新 session_state 中的值给 Python 变量
                # 除非我们把它放在 form 外面。
                # 为了简化，我们在提交时处理单位。
                # 但为了显示正确的单位选项，我们需要 access 到当前的 mat options。
                
                mat_options = {f"{m['name']} ({m.get('material_number', '-')})": m['id'] for m in raw_materials}
                
                with op_col1:
                    selected_mat_label = st.selectbox("选择原材料*", list(mat_options.keys()))
                
                # 尝试解析当前选中的原材料 (注意：在 form 未提交时，这里可能拿不到最新选择，
                # 但通常 streamlit 会重跑脚本，如果是用户交互触发的)
                # 这是一个局限性。为了更好的体验，我们将单位选择做得通用一些。
                
                with op_col2:
                    c2_1, c2_2 = st.columns(2)
                    with c2_1:
                        op_type = st.selectbox("操作类型*", ["入库", "出库"])
                    with c2_2:
                        # 提供常用单位
                        common_units = ["kg", "ton", "g", "L", "mL", "吨", "公斤", "克"]
                        op_unit = st.selectbox("单位", common_units, index=0) # 默认 kg
                    
                with op_col3:
                    op_qty = st.number_input("数量*", min_value=0.0, step=0.00001, format="%g")
                
                op_reason = st.text_input("备注/原因 (e.g. 采购入库, 生产领用)")
                
                op_submit = st.form_submit_button("提交库存变动", type="primary")
                
                if op_submit:
                    selected_mat_id = mat_options[selected_mat_label]
                    selected_material = next((m for m in raw_materials if m['id'] == selected_mat_id), None)
                    stock_unit = selected_material.get('unit', 'kg') if selected_material else 'kg'
                    
                    if op_qty > 0:
                        # 单位转换
                        # 核心逻辑：
                        # 1. 界面输入 op_qty 和 op_unit
                        # 2. 获取原材料库存主单位 stock_unit
                        # 3. 将 op_qty 转换为 stock_unit 单位下的 final_qty
                        # 4. data_manager.add_inventory_record 接收 final_qty，
                        #    它会直接将此值加减到原材料的 stock_quantity 上（假设该字段单位即为 stock_unit）。
                        
                        final_qty, success = convert_quantity(op_qty, op_unit, stock_unit)
                        
                        conversion_note = ""
                        if success and normalize_unit(op_unit) != normalize_unit(stock_unit):
                            conversion_note = f" (转换: {op_qty}{op_unit} -> {final_qty:g}{stock_unit})"
                            st.info(f"单位已自动转换: {op_qty} {op_unit} = {final_qty:g} {stock_unit}")
                        elif not success and normalize_unit(op_unit) != normalize_unit(stock_unit):
                            st.warning(f"⚠️ 无法从 {op_unit} 转换为 {stock_unit}，将按 1:1 处理。请检查单位是否正确。")
                            final_qty = op_qty
                            conversion_note = f" (单位不匹配: {op_unit} vs {stock_unit})"
                        
                        record_data = {
                            "material_id": selected_mat_id,
                            "type": "in" if op_type == "入库" else "out",
                            "quantity": final_qty, # 这里传递的是转换后的数量 (主单位)
                            "reason": f"{op_reason} [原始: {op_qty}{op_unit}]{conversion_note}",
                            "operator": "User", 
                            "date": datetime.now().strftime("%Y-%m-%d")
                        }
                        success, msg = data_manager.add_inventory_record(record_data)
                        if success:
                            st.success(msg)
                            time.sleep(1.5) # 增加延迟以便用户看到转换信息
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        st.warning("数量必须大于0")

    st.divider()
    st.subheader("📊 库存核对与原材料列表")
    if raw_materials:
        with st.expander("🔎 原材料库存核对 (以流水为准)", expanded=False):
            # 1. 基准日期选择
            col_date, col_desc = st.columns([1, 3])
            with col_date:
                # 默认为当月1号
                today = datetime.now()
                default_date = datetime(today.year, today.month, 1)
                benchmark_date = st.date_input("选择基准日期", value=default_date, key="raw_chk_date")
            with col_desc:
                st.info(f"系统将计算 {benchmark_date} 之前的累计库存作为**期初库存**，并核算该日期之后的流水变动。")

            records = data_manager.get_inventory_records()
            rows = []
            
            # 定义类型分类
            # 初始/采购: 基准增加
            initial_types = ["in", "return_in"]
            
            # 生产消耗: 基准减少
            consume_types = ["consume_out", "out"]
            
            # 人工调整
            adjust_in_types = ["adjust_in"]
            adjust_out_types = ["adjust_out"]
            
            calibration_candidates = []
            
            # 将 benchmark_date 转为字符串比较 (YYYY-MM-DD)
            bench_str = benchmark_date.strftime("%Y-%m-%d")
            
            # 用于存储详情数据供后续展示
            detail_data_map = {}
            
            for m in raw_materials:
                mid = m.get("id")
                name = m.get("name", "")
                cur_qty = float(m.get("stock_quantity", 0.0) or 0.0)
                unit = str(m.get("unit", "kg") or "kg")
                
                # 分段累计
                stock_opening = 0.0 # 期初 ( < bench_str )
                period_in = 0.0     # 期间采购 ( >= bench_str )
                period_consume = 0.0 # 期间消耗 ( >= bench_str )
                period_adjust = 0.0 # 期间调整 ( >= bench_str )
                
                # 详情记录
                period_logs = []
                
                for r in records:
                    if r.get("material_id") != mid:
                        continue
                        
                    qty = float(r.get("quantity", 0.0) or 0.0)
                    rtype = r.get("type", "")
                    r_date = r.get("date", "")
                    
                    # 判断时间段
                    is_period = r_date >= bench_str
                    
                    if not is_period:
                        # 期初计算 (所有类型的净值)
                        if rtype in initial_types + adjust_in_types:
                            stock_opening += qty
                        elif rtype in consume_types + adjust_out_types:
                            stock_opening -= qty
                    else:
                        # 期间计算 (分类统计)
                        if rtype in initial_types:
                            period_in += qty
                            period_logs.append({"date": r_date, "type": "采购/入库", "qty": qty, "impact": qty})
                        elif rtype in consume_types:
                            period_consume += qty
                            period_logs.append({"date": r_date, "type": "生产消耗", "qty": qty, "impact": -qty})
                        elif rtype in adjust_in_types:
                            period_adjust += qty
                            period_logs.append({"date": r_date, "type": "调整入库", "qty": qty, "impact": qty})
                        elif rtype in adjust_out_types:
                            period_adjust -= qty
                            period_logs.append({"date": r_date, "type": "调整出库", "qty": qty, "impact": -qty})
                
                # 理论库存 = 期初 + 期间采购 - 期间消耗 + 期间调整
                calculated_stock = stock_opening + period_in - period_consume + period_adjust
                
                # 差异 = 当前 - 理论
                diff = cur_qty - calculated_stock
                
                # 转换为显示单位 (吨)
                def to_ton(v):
                    val, ok = convert_quantity(v, unit, "ton")
                    return val if ok else v
                
                rows.append({
                    "名称": name,
                    f"期初库存({bench_str}前)": round(to_ton(stock_opening), 4),
                    "期间采购(吨)": round(to_ton(period_in), 4),
                    "期间消耗(吨)": round(to_ton(period_consume), 4),
                    "期间调整(吨)": round(to_ton(period_adjust), 4),
                    "理论库存(吨)": round(to_ton(calculated_stock), 4),
                    "当前库存(吨)": round(to_ton(cur_qty), 4),
                    "差额(当前-理论)": round(to_ton(diff), 4),
                    "单位": "吨"
                })
                
                # 记录详情数据 (注意：详情数据使用原始单位，展示时需转换或说明)
                # 为简化，这里我们在详情里直接展示吨 (如果单位不是吨，可能需要逐行转换，比较麻烦，暂展示原始单位或尽量转)
                # 实际上 detail_data_map 最好存储原始值，展示时转换
                detail_data_map[name] = {
                    "opening": stock_opening,
                    "logs": sorted(period_logs, key=lambda x: x["date"]),
                    "final": calculated_stock,
                    "unit": unit
                }
                
                # 记录校准候选 (绝对差额 > 0.0001吨)
                diff_ton = to_ton(diff)
                if abs(diff_ton) > 0.0001:
                    calibration_candidates.append({
                        "id": mid,
                        "name": name,
                        "calculated_stock": calculated_stock, # 原始单位
                        "diff_disp": round(diff_ton, 4)
                    })
                
            if rows:
                df_chk = pd.DataFrame(rows)
                df_chk = df_chk.sort_values(by="差额(当前-理论)", key=lambda s: s.abs(), ascending=False)
                st.dataframe(df_chk, use_container_width=True)
                
                # --- 计算明细查询 ---
                st.markdown("##### 🧾 计算明细查询")
                all_options = sorted(detail_data_map.keys())
                if all_options:
                    sel_detail = st.selectbox("选择原材料查看计算过程", all_options, key="raw_chk_detail_sel")
                    if sel_detail:
                        det = detail_data_map[sel_detail]
                        d_unit = det["unit"]
                        
                        st.write(f"**{sel_detail} 计算过程 (基准日: {bench_str})** - 原始单位: {d_unit}")
                        
                        detail_rows = []
                        run_bal = det["opening"]
                        
                        # Helper for conversion in detail view
                        def fmt_val(v):
                            val_ton, ok = convert_quantity(v, d_unit, "ton")
                            return f"{val_ton:+.4f}" if ok else f"{v:+.4f}"
                            
                        # Period Opening Row
                        val_ton_open, ok_open = convert_quantity(run_bal, d_unit, "ton")
                        open_disp = f"{val_ton_open:.4f}" if ok_open else f"{run_bal:.4f}"
                        
                        detail_rows.append({
                            "日期": f"{bench_str} (期初)",
                            "类型": "期初库存",
                            "变动数量(吨)" if ok_open else f"变动数量({d_unit})": "-",
                            "结存(吨)" if ok_open else f"结存({d_unit})": open_disp
                        })
                        
                        for log in det["logs"]:
                            run_bal += log["impact"]
                            
                            val_ton_imp, _ = convert_quantity(log['impact'], d_unit, "ton")
                            val_ton_bal, _ = convert_quantity(run_bal, d_unit, "ton")
                            
                            imp_disp = f"{val_ton_imp:+.4f}" if ok_open else f"{log['impact']:+.4f}"
                            bal_disp = f"{val_ton_bal:.4f}" if ok_open else f"{run_bal:.4f}"
                            
                            detail_rows.append({
                                "日期": log["date"],
                                "类型": log["type"],
                                "变动数量(吨)" if ok_open else f"变动数量({d_unit})": imp_disp,
                                "结存(吨)" if ok_open else f"结存({d_unit})": bal_disp
                            })
                            
                        st.table(pd.DataFrame(detail_rows))
                        
                        final_ton, _ = convert_quantity(det['final'], d_unit, "ton")
                        final_disp = f"{final_ton:.4f}" if ok_open else f"{det['final']:.4f}"
                        st.caption(f"注：理论库存 {final_disp} = 期初 + 期间变动累计")

                if calibration_candidates:
                    st.divider()
                    st.write("🔧 **一键校准**")
                    st.info("以下列表显示了当前库存与基于流水的理论库存存在差异的原材料。点击“校准”将把**当前库存**更新为**理论库存**。")
                    
                    options = {f"{c['name']} (差额: {c['diff_disp']}吨)": c['id'] for c in calibration_candidates}
                    selected_ids = st.multiselect("选择要校准的原材料", options=list(options.keys()), default=list(options.keys()))
                    
                    if st.button("🛠️ 更新当前库存 (以流水为准)"):
                        success_count = 0
                        with st.status("正在执行校准...", expanded=True) as status:
                            for label in selected_ids:
                                mid = options[label]
                                cand = next(c for c in calibration_candidates if c['id'] == mid)
                                target_balance = cand['calculated_stock']
                                
                                # 直接更新主数据库存
                                success, msg = data_manager.update_inventory_item(mid, {
                                    "stock_quantity": target_balance,
                                    "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                })
                                
                                if success:
                                    success_count += 1
                                    status.write(f"✅ {cand['name']}: 库存已更新")
                                else:
                                    status.write(f"❌ {cand['name']}: {msg}")
                            
                            if success_count > 0:
                                status.update(label=f"校准完成！成功更新 {success_count} 个原材料的库存。", state="complete", expanded=False)
                                import time
                                time.sleep(1)
                                st.rerun()
            else:
                st.info("暂无可核对的库存数据")
        st.subheader("📋 原材料列表")
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
            
            # 将库存统一转换为吨用于展示
            if "stock_quantity" in df_display.columns:
                def _to_ton(row):
                    qty = float(row.get("stock_quantity") or 0.0)
                    unit = str(row.get("unit") or "kg")
                    val, ok = convert_quantity(qty, unit, "ton")
                    return round(val, 4) if ok else round(qty, 4)
                df_display["stock_quantity"] = df_display.apply(_to_ton, axis=1)
            
            # 整理列名和显示顺序
            # 必须包含 ID 用于操作，但不需要显示
            # 添加 Select 列用于操作
            df_display["选择"] = False
            
            # 映射列名
            column_map = {
                "name": "名称",
                "material_number": "物料号",
                "stock_quantity": "库存(吨)",
                "unit": "单位",
                "abbreviation": "缩写",
                "supplier": "供应商",
                "qc_status": "QC状态",
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
                            e_rating = st.slider("供应商评分", 1, 5, int(editing_mat.get("supplier_rating", 3)), key=f"raw_e_rating_{form_uid}")
                            curr_qc = editing_mat.get("qc_status", "合格")
                            qc_opts = ["合格", "待检", "不合格", "冻结"]
                            e_qc = st.selectbox("QC 状态", qc_opts, index=qc_opts.index(curr_qc) if curr_qc in qc_opts else 0, key=f"raw_e_qc_{form_uid}")
                        
                        e_inv_col1, e_inv_col2 = st.columns(2)
                        
                        e_name_val = editing_mat.get("name", "") or ""
                        water_names = ["水", "自来水", "纯水", "去离子水", "工业用水", "生产用水"]
                        is_water_edit = e_name_val.strip() in water_names
                        
                        base_stock_qty = float(editing_mat.get("stock_quantity") or 0.0)
                        base_unit = str(editing_mat.get("unit", "kg") or "kg")
                        stock_ton_val, stock_ton_ok = convert_quantity(base_stock_qty, base_unit, "ton")
                        display_stock = stock_ton_val if stock_ton_ok else base_stock_qty
                        
                        with e_inv_col1:
                            e_stock_ton = st.number_input(
                                "当前库存 (吨)",
                                min_value=0.0,
                                step=0.00001,
                                format="%g",
                                value=display_stock,
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
                                        target_unit = e_unit.strip() or base_unit
                                        stock_base, stock_ok = convert_quantity(float(e_stock_ton), "ton", target_unit)
                                        if not stock_ok:
                                            stock_base = float(e_stock_ton)
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
                                            "supplier_rating": e_rating,
                                            "qc_status": e_qc,
                                            "stock_quantity": stock_base,
                                            "unit": target_unit,
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
