
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
        
        # 2. 预警列表
        if low_count > 0:
            UIManager.toast(f"⚠️ 以下 {low_count} 个产品库存低于 10 吨，请及时补货！", type="warning")
            low_df = pd.DataFrame(summary['low_stock_items'])
            UIManager.render_data_table(
                low_df[["product_name", "type", "current_stock", "unit"]].rename(columns={
                    "product_name": "产品名称", "type": "类型", "current_stock": "当前库存", "unit": "单位"
                }),
                mobile_cols=["产品名称", "当前库存", "单位"]
            )
        
        # 3. 库存分布图表
        st.subheader("📈 库存分布")
        dist_df = summary['stock_distribution']
        if not dist_df.empty:
            fig = px.bar(
                dist_df, 
                x="product_name", 
                y="current_stock", 
                color="type",
                text_auto='.2f',
                title="各产品当前库存 (吨)",
                labels={"product_name": "产品", "current_stock": "库存(吨)", "type": "类型"}
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("暂无库存数据")

    # ==================== Tab 2: 库存操作 ====================
    with tab_ops:
        op_type = st.radio("选择操作类型", ["生产入库", "销售出库", "库存校准"], horizontal=True)
        
        products = service.get_products()
        prod_names = [p["product_name"] for p in products] if products else []
        
        if op_type == "生产入库":
            st.markdown("#### 🏭 生产入库登记")
            with st.form("inbound_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    # 这里如果是真实场景，应该从生产订单中选择
                    p_name = st.selectbox("入库产品", prod_names + ["(新产品)"])
                    if p_name == "(新产品)":
                        new_name = st.text_input("输入新产品名称")
                        p_type = st.selectbox("产品类型", ["母液", "速凝剂", "复配", "其他"])
                        final_p_name = new_name
                    else:
                        # 查找类型
                        curr_p = next((p for p in products if p["product_name"] == p_name), {})
                        p_type = curr_p.get("type", "其他")
                        st.info(f"类型: {p_type}")
                        final_p_name = p_name
                        
                with col2:
                    qty = st.number_input("入库数量 (吨)", min_value=0.01, step=0.1)
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
                    p_name = st.selectbox("出库产品", prod_names)
                    # 显示当前库存
                    curr_p = next((p for p in products if p["product_name"] == p_name), None)
                    curr_stock = float(curr_p.get("current_stock", 0)) if curr_p else 0
                    st.caption(f"当前库存: {curr_stock} 吨")
                    
                with col2:
                    qty = st.number_input("出库数量 (吨)", min_value=0.01, max_value=curr_stock, step=0.1)
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
                                p_name, qty, customer, remark,
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
                p_name = st.selectbox("校准产品", prod_names, key="cal_prod")
                curr_p = next((p for p in products if p["product_name"] == p_name), None)
                sys_stock = float(curr_p.get("current_stock", 0)) if curr_p else 0
                st.metric("系统账面库存", f"{sys_stock:.4f} 吨")
                
            with col2:
                actual_stock = st.number_input("实物盘点库存 (吨)", min_value=0.0, step=0.0001, format="%.4f")
                diff = actual_stock - sys_stock
                st.metric("差异 (实盘-账面)", f"{diff:+.4f} 吨", delta=diff, delta_color="off")
            
            reason = st.text_input("差异原因说明 (必填)", placeholder="例如：盘亏、计量误差...")
            
            if st.button("确认校准并生成调整单", type="primary"):
                if abs(diff) < 0.0001:
                    UIManager.toast("无差异，无需调整", type="warning")
                elif not reason:
                    UIManager.toast("请填写差异原因", type="error")
                else:
                    with UIManager.with_spinner("正在校准库存..."):
                        success, msg = service.calibrate_stock(
                            p_name, actual_stock, reason,
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
            # 字段映射优化显示
            display_cols = {
                "date": "日期",
                "product_name": "产品名称",
                "type": "变动类型",
                "quantity": "数量",
                "snapshot_stock": "结存",
                "reason": "摘要/批号",
                "operator": "操作人"
            }
            
            # 格式化
            df_display = df_records[display_cols.keys()].rename(columns=display_cols)
            
            UIManager.render_data_table(
                df_display, 
                mobile_cols=["产品名称", "变动类型", "数量", "结存"],
                hide_index=True,
                column_config={
                    "数量": st.column_config.NumberColumn("数量", format="%.4f"),
                    "结存": st.column_config.NumberColumn("结存", format="%.4f"),
                }
            )
            
            # 导出
            csv = df_display.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                "📥 导出查询结果 (CSV)",
                csv,
                "inventory_report.csv",
                "text/csv",
                key='download-csv'
            )
        else:
            st.info("未找到符合条件的记录")
