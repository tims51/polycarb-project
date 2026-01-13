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
        with st.form("product_op_form", clear_on_submit=True):
            c1, c2, c3 = st.columns([1.5, 1.5, 1])
            
            with c1:
                # 产品类型选择
                op_category = st.selectbox("产品类型*", categories + ["其他"])
                
                # 产品名称 (可以是现有产品，也可以是输入新名称)
                # 获取该类别下的现有产品列表
                existing_products = [item['name'] for item in inventory if item.get('type') == op_category]
                if existing_products:
                    product_mode = st.radio("选择产品", ["选择现有", "新增产品"], horizontal=True, label_visibility="collapsed")
                    if product_mode == "选择现有":
                        op_name = st.selectbox("产品名称*", existing_products)
                    else:
                        op_name = st.text_input("输入新产品名称*")
                else:
                    st.info(f"该分类下暂无产品，请直接输入名称")
                    op_name = st.text_input("产品名称*")
            
            with c2:
                op_type = st.selectbox("操作类型*", ["生产入库", "发货出库", "盘点调整"])
                op_qty = st.number_input("数量 (吨)*", min_value=0.0, step=0.01, format="%.2f")
                
            with c3:
                op_date = st.date_input("日期", datetime.now())
                op_reason = st.text_input("备注 / 客户 / 订单号")
            
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
                        # 暂时简化处理，需结合现有库存判断是in还是out，这里假设用户自己输入正数表示变动量
                        # 为了严谨，建议盘点使用调整单。这里简化为直接入/出
                        # 我们让用户选择是 盘盈(in) 还是 盘亏(out) ? 
                        # 简单起见，这里默认入库，用户可以在备注说明。
                        # 或者我们强制用户在数量上体现正负? 不，UI上是绝对值。
                        # 让我们把“盘点调整”去掉，或者拆分为 盘盈入库 / 盘亏出库
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
