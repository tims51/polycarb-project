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
                        
                        # 手动清空 session state 中绑定的 key
                        if "inv_op_name_txt" in st.session_state: st.session_state["inv_op_name_txt"] = ""
                        # selectbox 无法轻易重置为 index 0，除非删除 key
                        if "inv_op_name_sel" in st.session_state: del st.session_state["inv_op_name_sel"]
                        if "inv_op_qty" in st.session_state: st.session_state["inv_op_qty"] = 0.0
                        if "inv_op_reason" in st.session_state: st.session_state["inv_op_reason"] = ""
                        if "inv_op_batch" in st.session_state: st.session_state["inv_op_batch"] = ""
                        
                        st.rerun()
                    else:
                        st.error(msg)

    # 3. 库存报表
    st.subheader("📊 库存明细表")
    
    if not inventory:
        st.info("暂无库存数据")
    else:
        # 转换为 DataFrame
        df = pd.DataFrame(inventory)
        
        # 确保 min_stock / max_stock 列存在
        if "min_stock" not in df.columns: df["min_stock"] = 0.0
        if "max_stock" not in df.columns: df["max_stock"] = 0.0
        
        # 格式化显示
        df_display = df[["name", "type", "stock_quantity", "min_stock", "max_stock", "unit", "last_update"]].copy()
        df_display.columns = ["产品名称", "分类", "当前库存", "最低库存", "最高库存", "单位", "最后更新时间"]
        
        # 筛选器
        filter_cat = st.multiselect("按分类筛选", categories, default=categories)
        if filter_cat:
            df_display = df_display[df_display["分类"].isin(filter_cat)]
            
        st.dataframe(
            df_display,
            use_container_width=True,
            column_config={
                "当前库存": st.column_config.NumberColumn("当前库存", format="%.2f 吨"),
                "最低库存": st.column_config.NumberColumn("最低库存", format="%.2f 吨"),
                "最高库存": st.column_config.NumberColumn("最高库存", format="%.2f 吨"),
            }
        )
        
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
