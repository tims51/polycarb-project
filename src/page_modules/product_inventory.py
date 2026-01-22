
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta
from services.inventory_service import InventoryService
from components.ui_manager import UIManager

def render_product_inventory_page(service: InventoryService):
    st.title("📦 成品库存管理")
    
    # Service injected via argument

    
    # 侧边栏设置 (如果需要)
    # with st.sidebar:
    #     st.caption("库存模块 v2.0")

    # 主要布局：Tabs
    tab_dashboard, tab_ops, tab_reports = st.tabs(["📊 监控看板", "🛠️ 库存操作", "📑 明细查询"])
    
    # ==================== Tab 1: 监控看板 ====================
    with tab_dashboard:
        summary = service.get_inventory_summary(low_stock_threshold=10.0)
        dist_df = summary['stock_distribution']
        
        # 1. KPI Cards
        kpi1, kpi2, kpi3 = st.columns(3)
        with kpi1:
            UIManager.render_card("总库存量", f"{summary['total_stock']:.2f} 吨", icon="📦", color="#007bff")
        with kpi2:
            UIManager.render_card("在库产品数", f"{summary['product_count']} 个", icon="🏭", color="#28a745")
        
        low_count = len(summary['low_stock_items'])
        with kpi3:
            delta_val = f"-{low_count}" if low_count > 0 else "正常"
            UIManager.render_card("库存预警", f"{low_count} 项", sub_value=delta_val, icon="⚠️", color="#dc3545" if low_count > 0 else "#28a745")
        
        st.markdown("---")
        
        # 2. 库存分布看板
        st.subheader("📊 库存分布看板")
        inventory_data = service.get_products()
        
        if inventory_data:
            df_inv = pd.DataFrame(inventory_data)
            # 兼容字段名：stock_quantity 或 current_stock
            if "stock_quantity" not in df_inv.columns and "current_stock" in df_inv.columns:
                df_inv["stock_quantity"] = df_inv["current_stock"]
            
            # 确保数字列为 float 并转换为吨 (数据库存的是 kg)
            df_inv["stock_quantity"] = pd.to_numeric(df_inv["stock_quantity"], errors='coerce').fillna(0.0) / 1000.0
            
            # 聚合：按产品名称汇总库存，确保同名项合并
            df_chart = df_inv.groupby("product_name", as_index=False)["stock_quantity"].sum()
            # 过滤：只显示有库存的产品 (> 0.0001 吨)
            df_chart = df_chart[df_chart["stock_quantity"] > 0.0001]
            
            if not df_chart.empty:
                c1, c2 = st.columns(2)
                with c1:
                    # 饼图：占比
                    fig_pie = px.pie(
                        df_chart,
                        values='stock_quantity',
                        names='product_name',
                        title='库存占比分布',
                        hole=0.4,
                        color_discrete_sequence=px.colors.qualitative.Pastel
                    )
                    fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig_pie, use_container_width=True)
                
                with c2:
                    # 柱状图：绝对值
                    fig_bar = px.bar(
                        df_chart,
                        x='product_name',
                        y='stock_quantity',
                        title='当前库存量 (吨)',
                        text_auto='.2f',
                        color='stock_quantity',
                        color_continuous_scale='Blues',
                        labels={'product_name': '产品名称', 'stock_quantity': '库存(吨)'}
                    )
                    st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("当前无库存产品 (库存均为 0)")
        else:
            st.info("暂无库存数据")

        st.markdown("---")

        # 3. 库存清单 (清晰明了的形式)
        st.subheader("📋 成品库存清单")
        if not dist_df.empty:
            # 预警提示
            if low_count > 0:
                st.warning(f"⚠️ 注意：有 {low_count} 项产品库存低于预警值 (10吨)")
            
            # 格式化表格显示
            df_display = dist_df.copy()
            df_display = df_display.rename(columns={
                "product_name": "产品名称",
                "type": "类型",
                "current_stock": "当前库存",
                "unit": "单位"
            })
            
            # 使用 st.dataframe 提供清晰、可搜索、可排序的表格
            st.dataframe(
                df_display,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "当前库存": st.column_config.NumberColumn(
                        "当前库存",
                        format="%.3f 吨",
                        help="当前系统账面库存数量"
                    ),
                    "类型": st.column_config.SelectboxColumn(
                        "类型",
                        options=["母液", "速凝剂", "复配", "其他"]
                    )
                }
            )
            
            # 导出功能
            csv = df_display.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                "📥 导出库存清单 (CSV)",
                csv,
                f"inventory_list_{date.today()}.csv",
                "text/csv",
                key='download-inventory-list'
            )
        else:
            st.info("暂无产品库存数据")

    # ==================== Tab 2: 库存操作 ====================
    with tab_ops:
        op_type = st.radio("选择操作类型", ["生产入库", "销售出库", "库存校准"], horizontal=True)
        
        products = service.get_products()
        # 遵循 AI_RULES: 下拉框必须包含 ID 或 编码
        prod_options = {f"{p['product_name']} (ID: {p['id']})": p for p in products} if products else {}
        prod_display_names = list(prod_options.keys())
        
        if op_type == "生产入库":
            st.markdown("#### 🏭 生产入库登记")
            with st.form("inbound_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    p_label = st.selectbox("入库产品", prod_display_names + ["(新产品)"])
                    if p_label == "(新产品)":
                        new_name = st.text_input("输入新产品名称")
                        p_type = st.selectbox("产品类型", ["母液", "速凝剂", "复配", "其他"])
                        final_p_name = new_name
                    else:
                        selected_p = prod_options[p_label]
                        p_type = selected_p.get("type", "其他")
                        st.info(f"类型: {p_type}")
                        final_p_name = selected_p["product_name"]
                        
                with col2:
                    qty = st.number_input("入库数量 (吨)", min_value=0.00001, step=0.00001, format="%.5f")
                    batch_no = st.text_input("生产批号 (Batch No.)", placeholder="e.g. PROD-20260120-001")
                
                op_date = st.date_input("入库日期", date.today())
                
                submitted = st.form_submit_button("确认入库", type="primary")
                if submitted:
                    if not final_p_name:
                        UIManager.toast("请输入产品名称", type="error")
                    elif not batch_no:
                        UIManager.toast("必须填写生产批号以进行追溯", type="error")
                    else:
                        with UIManager.with_spinner("正在处理入库..."):
                            success, msg = service.process_inbound(
                                final_p_name, p_type, qty, batch_no, 
                                operator=st.session_state.get("username", "Admin"),
                                date_str=op_date.strftime("%Y-%m-%d")
                            )
                            if success:
                                UIManager.toast(f"✅ 入库成功！库存已更新。", type="success")
                            else:
                                UIManager.toast(f"❌ 失败: {msg}", type="error")

        elif op_type == "销售出库":
            st.markdown("#### 🚚 销售出库登记")
            with st.form("outbound_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    p_label = st.selectbox("出库产品", prod_display_names)
                    selected_p = prod_options[p_label]
                    curr_stock_kg = float(selected_p.get("stock_quantity", 0))
                    curr_stock_tons = curr_stock_kg / 1000.0
                    st.caption(f"当前库存: {curr_stock_tons:.3f} 吨")
                    
                with col2:
                    qty = st.number_input("出库数量 (吨)", min_value=0.00001, max_value=max(0.00001, curr_stock_tons), step=0.00001, format="%.5f")
                    customer = st.text_input("客户名称")
                
                remark = st.text_input("备注 (订单号/物流单号)")
                op_date = st.date_input("出库日期", date.today())
                
                submitted = st.form_submit_button("确认出库", type="primary")
                if submitted:
                    if not customer:
                        UIManager.toast("请填写客户名称", type="error")
                    else:
                        with UIManager.with_spinner("正在处理出库..."):
                            success, msg = service.process_outbound(
                                selected_p["product_name"], qty, customer, remark,
                                operator=st.session_state.get("username", "Admin"),
                                date_str=op_date.strftime("%Y-%m-%d")
                            )
                            if success:
                                UIManager.toast(f"✅ 出库成功！库存已扣减。", type="success")
                            else:
                                UIManager.toast(f"❌ 失败: {msg}", type="error")

        elif op_type == "库存校准":
            st.markdown("#### ⚖️ 库存盘点校准")
            st.info("当系统库存与实物盘点不一致时使用此功能。")
            
            col1, col2 = st.columns(2)
            with col1:
                p_label = st.selectbox("校准产品", prod_display_names, key="cal_prod")
                selected_p = prod_options[p_label]
                sys_stock_kg = float(selected_p.get("stock_quantity", 0))
                sys_stock_tons = sys_stock_kg / 1000.0
                st.metric("系统账面库存", f"{sys_stock_tons:.5f} 吨")
                
            with col2:
                actual_stock = st.number_input("实物盘点库存 (吨)", min_value=0.0, step=0.00001, format="%.5f")
                diff = actual_stock - sys_stock_tons
                st.metric("差异 (实盘-账面)", f"{diff:+.5f} 吨", delta=diff, delta_color="off")
            
            reason = st.text_input("差异原因说明 (必填)", placeholder="例如：盘亏、计量误差...")
            
            if st.button("确认校准并生成调整单", type="primary"):
                if abs(diff) < 0.0001:
                    UIManager.toast("无差异，无需调整", type="warning")
                elif not reason:
                    UIManager.toast("请填写差异原因", type="error")
                else:
                    with UIManager.with_spinner("正在校准库存..."):
                        success, msg = service.calibrate_stock(
                            selected_p["product_name"], actual_stock, reason,
                            operator=st.session_state.get("username", "Admin")
                        )
                        if success:
                            UIManager.toast("✅ 校准成功！", type="success")
                            st.rerun()
                        else:
                            UIManager.toast(msg, type="error")

    # ==================== Tab 3: 明细查询 ====================
    with tab_reports:
        st.markdown("#### 🔍 库存流水查询")
        
        # 筛选区
        with st.expander("筛选条件", expanded=True):
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                start_d = st.date_input("开始日期", date.today() - timedelta(days=30))
            with col2:
                end_d = st.date_input("结束日期", date.today())
            with col3:
                # 获取所有类型
                all_types = sorted(list(set([p.get("type", "其他") for p in products]))) if products else []
                sel_type = st.selectbox("产品类型", ["全部"] + all_types)
            with col4:
                search_txt = st.text_input("关键词搜索", placeholder="产品名/批号/客户...")
        
        # 查询
        df_records = service.get_inventory_history(
            start_date=start_d, 
            end_date=end_d, 
            product_type=sel_type, 
            search_term=search_txt
        )
        
        if not df_records.empty:
            df = df_records.copy()
            
            # 1. 单位转换与填充：数据库存的是 kg，显示为 吨
            if "quantity" in df.columns:
                df["quantity"] = pd.to_numeric(df["quantity"], errors='coerce').fillna(0.0) / 1000.0
            
            if "snapshot_stock" not in df.columns:
                df["snapshot_stock"] = None
            
            # 处理结存显示 (转换为吨)
            def format_snapshot(val):
                if pd.notnull(val) and isinstance(val, (int, float)):
                    return f"{val/1000.0:.4f}"
                return "-"
            
            df["snapshot_stock"] = df["snapshot_stock"].apply(format_snapshot)
            
            # 2. 确保有时间字段 (如果没有 created_at 就用 date 补)
            if "created_at" not in df.columns:
                df["created_at"] = df.get("date", "")
            
            # 3. 整理显示列
            display_cols = {
                "created_at": "🕒 发生时间",
                "product_name": "📦 产品名称",
                "type": "🔄 变动类型",
                "quantity": "🔢 变动数量(吨)",
                "snapshot_stock": "💰 结存快照(吨)",
                "reason": "📝 备注/关联单据",
                "operator": "👤 操作人"
            }
            
            # 过滤掉不存在的列
            valid_cols = [c for c in display_cols.keys() if c in df.columns]
            df_show = df[valid_cols].rename(columns=display_cols)
            
            # 4. 渲染表格
            st.dataframe(
                df_show,
                use_container_width=True,
                column_config={
                    "🕒 发生时间": st.column_config.TextColumn("🕒 发生时间"), 
                    "🔄 变动类型": st.column_config.TextColumn("🔄 变动类型"),
                    "🔢 变动数量(吨)": st.column_config.NumberColumn("🔢 变动数量(吨)", format="%.4f"),
                    "💰 结存快照(吨)": st.column_config.TextColumn("💰 结存快照(吨)"), 
                },
                height=500,
                hide_index=True
            )
            
            # 导出
            csv = df_show.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                "📥 导出查询结果 (CSV)",
                csv,
                f"inventory_report_{date.today()}.csv",
                "text/csv",
                key='download-csv'
            )
        else:
            st.info("未找到符合条件的记录")
