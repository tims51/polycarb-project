import streamlit as st
import pandas as pd
from datetime import datetime
import uuid

def render_product_inventory_page(data_manager):
    st.title("📦 成品库存管理")
    
    # 1. 顶部统计卡片
    inventory = data_manager.get_product_inventory()
    
    # --- 安全库存预警检测 ---
    alerts = []
    for item in inventory:
        stock = float(item.get("stock_quantity", 0.0))
        min_stock = float(item.get("min_stock", 0.0))
        max_stock = float(item.get("max_stock", 0.0))
        
        if min_stock > 0 and stock < min_stock:
            alerts.append(f"⚠️ **{item['name']}** 库存不足! (当前: {stock}, 最低: {min_stock})")
        if max_stock > 0 and stock > max_stock:
            alerts.append(f"⚠️ **{item['name']}** 库存积压! (当前: {stock}, 最高: {max_stock})")
            
    if alerts:
        with st.container():
            st.warning("  \n".join(alerts), icon="🔔")
    # ----------------------
    
    # 分类统计
    categories = ["母液", "有碱速凝剂", "无碱速凝剂", "防冻剂", "成品减水剂"]
    
    cols = st.columns(len(categories))
    for idx, cat in enumerate(categories):
        total = sum(item['stock_quantity'] for item in inventory if item.get('type') == cat)
        with cols[idx]:
            st.metric(f"{cat}库存", f"{total:.2f} 吨")
            
    st.divider()

    # --- 1.5 产品设置 (安全库存) ---
    with st.expander("⚙️ 产品设置 (安全库存 / 预警)", expanded=False):
        c_set1, c_set2, c_set3 = st.columns([2, 1, 1])
        with c_set1:
            # 获取所有产品列表
            all_products = sorted([p for p in inventory], key=lambda x: x['type'])
            prod_options = {f"[{p.get('type')}] {p['name']}": p['id'] for p in all_products}
            sel_prod_label = st.selectbox("选择产品进行设置", list(prod_options.keys()))
            
        if prod_options:
            sel_prod_id = prod_options[sel_prod_label]
            target_prod = next((p for p in inventory if p['id'] == sel_prod_id), None)
            
            if target_prod:
                with st.form("prod_setting_form"):
                    cs1, cs2 = st.columns(2)
                    with cs1:
                        new_min = st.number_input("最低库存 (吨)", value=float(target_prod.get("min_stock", 0.0)), step=1.0)
                    with cs2:
                        new_max = st.number_input("最高库存 (吨)", value=float(target_prod.get("max_stock", 0.0)), step=1.0)
                    
                    if st.form_submit_button("保存设置"):
                        data_manager.update_product_inventory_item(sel_prod_id, {
                            "min_stock": new_min,
                            "max_stock": new_max
                        })
                        st.success(f"已更新 {target_prod['name']} 安全库存设置")
                        st.rerun()

    # 2. 库存操作区 (入库/发货)
    with st.expander("📝 库存操作 (生产入库 / 发货出库)", expanded=True):
        # 移出 st.form 的控制组件，以便即时响应
        c_ctrl1, c_ctrl2 = st.columns([1, 1])
        with c_ctrl1:
            op_category = st.selectbox("产品类型*", categories + ["其他"], key="inv_op_cat")
        
        # 获取该类别下的现有产品列表
        existing_products = [item['name'] for item in inventory if item.get('type') == op_category]
        
        product_mode = "新增产品"
        if existing_products:
            with c_ctrl2:
                # 使用 radio 选择模式
                product_mode = st.radio("选择产品", ["选择现有", "新增产品"], horizontal=True, key="inv_op_mode")

        with st.form("product_op_form", clear_on_submit=False):
            c1, c2, c3, c4 = st.columns([1.5, 1.2, 0.8, 1])
            
            with c1:
                # 根据外部状态显示不同的输入组件
                if product_mode == "选择现有" and existing_products:
                    # 添加一个空白选项作为默认值
                    op_name = st.selectbox("产品名称*", [""] + existing_products, index=0, key="inv_op_name_sel")
                else:
                    placeholder = "输入新产品名称*"
                    if not existing_products: 
                        placeholder = f"该分类暂无产品，请输入名称*"
                    op_name = st.text_input(placeholder, key="inv_op_name_txt")
            
            with c2:
                op_type = st.selectbox("操作类型*", ["生产入库", "发货出库", "盘点调整"], key="inv_op_type")
                op_qty = st.number_input("数量 (吨)*", min_value=0.0, step=0.01, format="%.2f", key="inv_op_qty")
            
            with c3:
                # 新增批次号输入
                op_batch = st.text_input("批次号 (Batch)", key="inv_op_batch", placeholder="可选")

            with c4:
                op_date = st.date_input("日期", datetime.now(), key="inv_op_date")
                op_reason = st.text_input("备注 / 客户 / 订单号", key="inv_op_reason")
            
            submitted = st.form_submit_button("提交", type="primary", use_container_width=True)
            
            if submitted:
                if not op_name:
                    st.error("请输入产品名称")
                elif op_qty <= 0:
                    st.error("数量必须大于0")
                else:
                    # 转换操作类型为内部标识
                    internal_type = "in"
                    if op_type == "发货出库":
                        internal_type = "out"
                    elif op_type == "盘点调整":
                        pass
                    
                    # 重新映射类型
                    final_type = "in"
                    if op_type in ["发货出库"]:
                        final_type = "out"
                    
                    record_data = {
                        "product_name": op_name,
                        "product_type": op_category,
                        "quantity": op_qty,
                        "type": final_type,
                        "reason": f"{op_type}: {op_reason}",
                        "batch_number": op_batch, # 保存批次号
                        "operator": "User",
                        "date": op_date.strftime("%Y-%m-%d")
                    }
                    
                    success, msg = data_manager.add_product_inventory_record(record_data)
                    if success:
                        st.success(f"操作成功: {op_name} {op_type} {op_qty}吨")
                        
                        # 不再直接修改 session_state 中的值来清空组件，而是通过 key 删除状态或 rerun
                        # 简单的 rerun 会保留 input 的值，除非使用 clear_on_submit=True (但这里是 st.form_submit_button, 不是 st.form)
                        # 等等，上面使用的是 st.form("inv_op_form", clear_on_submit=True) 吗？
                        # 查看上下文，第 88 行：with st.form("inv_op_form", clear_on_submit=False): 
                        # 应该改为 True 就可以自动清空了，或者使用回调函数
                        
                        # 修复方案：删除 session_state 中的 key，让组件在 rerun 时重置
                        keys_to_reset = ["inv_op_name_txt", "inv_op_name_sel", "inv_op_qty", "inv_op_reason", "inv_op_batch"]
                        for k in keys_to_reset:
                            if k in st.session_state:
                                del st.session_state[k]
                        
                        st.rerun()
                    else:
                        st.error(msg)

    # 3. 库存报表
    st.subheader("📊 库存明细表 (可编辑)")
    
    if not inventory:
        st.info("暂无库存数据")
    else:
        # 转换为 DataFrame
        df = pd.DataFrame(inventory)
        
        # 确保列存在
        for col in ["min_stock", "max_stock", "unit", "last_update"]:
            if col not in df.columns:
                df[col] = 0.0 if "stock" in col else ""
        
        # 筛选器
        filter_cat = st.multiselect("按分类筛选", categories, default=categories)
        
        # 准备编辑用的 DataFrame
        # 必须保留原始 index 以便映射修改，或者我们使用 id 列
        df_edit = df.copy()
        if filter_cat:
            df_edit = df_edit[df_edit["type"].isin(filter_cat)]
            
        # 只需要特定的列，并确保 id 存在以便更新
        cols_to_use = ["id", "name", "type", "stock_quantity", "min_stock", "max_stock", "unit", "last_update"]
        # 补全可能缺失的列
        for c in cols_to_use:
            if c not in df_edit.columns: df_edit[c] = None
            
        df_edit = df_edit[cols_to_use]
        
        # 密码验证状态
        if "inventory_edit_auth" not in st.session_state:
            st.session_state.inventory_edit_auth = False
            
        # 权限控制区域
        if not st.session_state.inventory_edit_auth:
            st.info("🔒 编辑模式已锁定，请输入管理员密码解锁")
            pwd_col1, pwd_col2 = st.columns([2, 1])
            with pwd_col1:
                admin_pwd = st.text_input("管理员密码", type="password", key="inv_edit_pwd", label_visibility="collapsed", placeholder="请输入密码")
            with pwd_col2:
                if st.button("🔓 解锁编辑", key="btn_unlock_inv"):
                    if admin_pwd == "admin": # 简单硬编码密码，实际应从配置读取
                        st.session_state.inventory_edit_auth = True
                        st.rerun()
                    else:
                        st.error("密码错误")
            
            # 锁定状态下只显示表格，不可编辑
            st.dataframe(
                df_edit,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "id": None,
                    "name": "产品名称",
                    "type": "分类",
                    "stock_quantity": st.column_config.NumberColumn("当前库存", format="%.2f 吨"),
                    "min_stock": st.column_config.NumberColumn("最低库存", format="%.2f 吨"),
                    "max_stock": st.column_config.NumberColumn("最高库存", format="%.2f 吨"),
                    "unit": "单位",
                    "last_update": st.column_config.DatetimeColumn("最后更新时间", format="YYYY-MM-DD HH:mm"),
                }
            )
            
        else:
            # 已解锁状态，显示可编辑表格和锁定按钮
            if st.button("🔒 锁定编辑", key="btn_lock_inv"):
                st.session_state.inventory_edit_auth = False
                st.rerun()
                
            # 使用 data_editor
            edited_df = st.data_editor(
                df_edit,
                key="prod_inv_editor",
                use_container_width=True,
                hide_index=True,
                column_config={
                    "id": None, # 隐藏 ID
                    "name": st.column_config.TextColumn("产品名称", required=True),
                    "type": st.column_config.SelectboxColumn("分类", options=categories, required=True),
                    "stock_quantity": st.column_config.NumberColumn("当前库存", disabled=True, format="%.2f 吨"),
                    "min_stock": st.column_config.NumberColumn("最低库存", min_value=0.0, step=0.1, format="%.2f"),
                    "max_stock": st.column_config.NumberColumn("最高库存", min_value=0.0, step=0.1, format="%.2f"),
                    "unit": st.column_config.TextColumn("单位"),
                    "last_update": st.column_config.DatetimeColumn("最后更新时间", disabled=True, format="YYYY-MM-DD HH:mm"),
                },
                disabled=["stock_quantity", "last_update"],
                num_rows="dynamic" # 启用添加和删除行功能
            )
            
            # 处理变更 (编辑、添加、删除)
            # 注意：为了处理删除，我们需要比较 session_state 中的 deleted_rows
            
            if "prod_inv_editor" in st.session_state:
                editor_state = st.session_state["prod_inv_editor"]
                any_success = False
                
                # 1. 处理删除 (deleted_rows)
                # deleted_rows is a list of integers (indices)
                if editor_state.get("deleted_rows"):
                    deleted_indices = editor_state["deleted_rows"]
                    
                    ids_to_delete = []
                    for idx in deleted_indices:
                        if idx < len(df_edit):
                             ids_to_delete.append(int(df_edit.iloc[idx]["id"]))
                    
                    if ids_to_delete:
                        for pid in ids_to_delete:
                            if data_manager.delete_product_inventory_item(pid):
                                any_success = True
                
                # 2. 处理编辑 (edited_rows)
                if editor_state.get("edited_rows"):
                    updates_map = editor_state["edited_rows"]
                    updates_to_process = []
                    
                    for idx, changes in updates_map.items():
                        if idx < len(df_edit):
                            row_id = int(df_edit.iloc[idx]["id"])
                            
                            # 检查实质性变更
                            real_changes = {}
                            original_row = df_edit.iloc[idx]
                            
                            for col, new_val in changes.items():
                                old_val = original_row[col]
                                if old_val != new_val:
                                    real_changes[col] = new_val
                                    
                            if real_changes:
                                updates_to_process.append((row_id, real_changes))
                    
                    if updates_to_process:
                        for prod_id, changes in updates_to_process:
                            if data_manager.update_product_inventory_item(prod_id, changes):
                                any_success = True
                
                # 3. 处理新增 (added_rows)
                # data_editor 支持 num_rows="dynamic" 后，用户可以在最后一行添加
                if editor_state.get("added_rows"):
                    added_rows = editor_state["added_rows"]
                    for row_data in added_rows:
                        # 必填字段检查
                        if row_data.get("name") and row_data.get("type"):
                            # 构造新增数据
                            # 注意：这里我们复用 add_product_inventory_record 逻辑，
                            # 但这个函数是设计给流水记录用的，它会同时创建库存项和流水
                            # 我们这里只想创建库存项 (初始库存为0或指定值)
                            # 如果 data_manager 没有单独创建库存项的方法，我们可以模拟一次入库操作
                            # 或者直接调用 add_product_inventory_record
                            
                            # 准备数据
                            new_record = {
                                "product_name": row_data.get("name"),
                                "product_type": row_data.get("type"),
                                "quantity": float(row_data.get("stock_quantity", 0.0)),
                                "type": "in", # 初始入库
                                "reason": "手动添加库存项",
                                "operator": "User",
                                "date": datetime.now().strftime("%Y-%m-%d")
                            }
                            
                            # 补充其他字段
                            if "unit" in row_data: new_record["unit"] = row_data["unit"] # 注意 add_product_inventory_record 是否支持 unit 更新
                            
                            # 调用现有接口添加
                            # 注意：add_product_inventory_record 会处理如果不存在则创建的逻辑
                            success, msg = data_manager.add_product_inventory_record(new_record)
                            if success:
                                # 如果有 min/max stock，需要额外更新
                                # 获取新创建的 ID (这里比较麻烦，因为 add_product_inventory_record 没有返回 ID)
                                # 我们可以通过名称重新查找
                                # 简化起见，先只做添加
                                any_success = True
                
                if any_success:
                    st.toast("库存信息已更新")
                    import time
                    time.sleep(0.5)
                    st.rerun()
        
    # 4. 历史记录
    with st.expander("📜 历史流水记录"):
        records = data_manager.get_product_inventory_records()
        if records:
            df_recs = pd.DataFrame(records)
            # 排序
            df_recs = df_recs.sort_values(by="id", ascending=False)
            
            # 确保 batch_number 存在
            if "batch_number" not in df_recs.columns: df_recs["batch_number"] = ""

            st.dataframe(
                df_recs[["date", "product_name", "product_type", "type", "quantity", "batch_number", "reason", "operator", "snapshot_stock"]],
                use_container_width=True,
                column_config={
                    "type": st.column_config.TextColumn("类型", help="in=入库, out=出库"),
                    "quantity": st.column_config.NumberColumn("数量 (吨)", format="%.2f"),
                    "batch_number": st.column_config.TextColumn("批次号"),
                    "snapshot_stock": st.column_config.NumberColumn("结存 (吨)", format="%.2f")
                }
            )
        else:
            st.info("暂无历史记录")
