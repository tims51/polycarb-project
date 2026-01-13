import streamlit as st
import pandas as pd
from datetime import datetime
import uuid

def render_product_inventory_page(data_manager):
    st.title("📦 成品库存管理")
    
    # 1. 顶部统计卡片
    inventory = data_manager.get_product_inventory()
    
    # 分类统计
    categories = ["母液", "有碱速凝剂", "无碱速凝剂", "防冻剂", "成品减水剂"]
    
    cols = st.columns(len(categories))
    for idx, cat in enumerate(categories):
        total = sum(item['stock_quantity'] for item in inventory if item.get('type') == cat)
        with cols[idx]:
            st.metric(f"{cat}库存", f"{total:.2f} 吨")
            
    st.divider()
    
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
            c1, c2, c3 = st.columns([1.5, 1.5, 1])
            
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
                        "operator": "User",
                        "date": op_date.strftime("%Y-%m-%d")
                    }
                    
                    success, msg = data_manager.add_product_inventory_record(record_data)
                    if success:
                        st.success(f"操作成功: {op_name} {op_type} {op_qty}吨")
                        # 成功后，通过设置 session state 或 rerun 来清空/重置表单
                        # 但由于 key 绑定，直接 rerun 可能不会清空 text_input，除非我们手动清理 session state
                        # 或者简单地不做任何事，让用户手动清空？不，用户习惯是提交成功后清空。
                        # 使用 clear_on_submit=True 是最简单的，但失败时也会清空。
                        # 既然我们要“失败时保留”，那就只能 clear_on_submit=False，然后成功时手动清空。
                        
                        # 手动清空 session state 中绑定的 key
                        if "inv_op_name_txt" in st.session_state: st.session_state["inv_op_name_txt"] = ""
                        # selectbox 无法轻易重置为 index 0，除非删除 key
                        if "inv_op_name_sel" in st.session_state: del st.session_state["inv_op_name_sel"]
                        if "inv_op_qty" in st.session_state: st.session_state["inv_op_qty"] = 0.0
                        if "inv_op_reason" in st.session_state: st.session_state["inv_op_reason"] = ""
                        
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
        
        # 格式化显示
        df_display = df[["name", "type", "stock_quantity", "unit", "last_update"]].copy()
        df_display.columns = ["产品名称", "分类", "当前库存", "单位", "最后更新时间"]
        
        # 筛选器
        filter_cat = st.multiselect("按分类筛选", categories, default=categories)
        if filter_cat:
            df_display = df_display[df_display["分类"].isin(filter_cat)]
            
        st.dataframe(
            df_display,
            use_container_width=True,
            column_config={
                "当前库存": st.column_config.NumberColumn(
                    "当前库存",
                    format="%.2f 吨"
                )
            }
        )
        
    # 4. 历史记录
    with st.expander("📜 历史流水记录"):
        records = data_manager.get_product_inventory_records()
        if records:
            df_recs = pd.DataFrame(records)
            # 排序
            df_recs = df_recs.sort_values(by="id", ascending=False)
            
            st.dataframe(
                df_recs[["date", "product_name", "product_type", "type", "quantity", "reason", "operator", "snapshot_stock"]],
                use_container_width=True,
                column_config={
                    "type": st.column_config.TextColumn("类型", help="in=入库, out=出库"),
                    "quantity": st.column_config.NumberColumn("数量 (吨)", format="%.2f"),
                    "snapshot_stock": st.column_config.NumberColumn("结存 (吨)", format="%.2f")
                }
            )
        else:
            st.info("暂无历史记录")
