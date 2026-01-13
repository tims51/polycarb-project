import streamlit as st
from datetime import datetime
import pandas as pd
import uuid

def render_sap_bom(data_manager):
    """渲染 SAP/BOM 管理页面"""
    st.header("🏭 SAP/BOM 管理")
    
    tab1, tab2, tab3 = st.tabs(["🧬 BOM 管理", "🏭 生产管理", "📈 台账报表"])
    
    with tab1:
        _render_bom_management(data_manager)
    
    with tab2:
        _render_production_management(data_manager)
        
    with tab3:
        _render_inventory_reports(data_manager)

def _render_bom_management(data_manager):
    st.subheader("BOM 主数据管理")
    
    if "bom_active_id" not in st.session_state:
        st.session_state.bom_active_id = None
    if "bom_edit_mode" not in st.session_state:
        st.session_state.bom_edit_mode = False
        
    # 左侧列表，右侧详情
    col_list, col_detail = st.columns([1, 2])
    
    boms = data_manager.get_all_boms()
    
    with col_list:
        st.markdown("#### BOM 列表")
        # 搜索框
        search_term = st.text_input("🔍 搜索 BOM", placeholder="编号/名称").strip().lower()
        
        if st.button("➕ 新建 BOM", use_container_width=True):
            st.session_state.bom_active_id = "new"
            st.session_state.bom_edit_mode = True
            st.rerun()
            
        if not boms:
            st.info("暂无 BOM 数据")
        else:
            # 过滤
            filtered_boms = boms
            if search_term:
                filtered_boms = [b for b in boms if search_term in b.get('bom_code', '').lower() or search_term in b.get('bom_name', '').lower()]
            
            for bom in filtered_boms:
                label = f"{bom.get('bom_code')} - {bom.get('bom_name')}"
                btn_type = "primary" if str(bom.get('id')) == str(st.session_state.bom_active_id) else "secondary"
                
                # 使用列布局放置删除按钮 (仅在悬停或选中时显示比较复杂，这里简化为每行一个删除小按钮不太好看，
                # 建议在详情页做删除，这里只做列表选择)
                if st.button(label, key=f"bom_sel_{bom['id']}", type=btn_type, use_container_width=True):
                    st.session_state.bom_active_id = bom['id']
                    st.session_state.bom_edit_mode = False
                    st.rerun()

    with col_detail:
        if st.session_state.bom_active_id == "new":
            _render_bom_form(data_manager, None)
        elif st.session_state.bom_active_id:
            bom_id = st.session_state.bom_active_id
            bom = next((b for b in boms if b.get('id') == bom_id), None)
            
            # 判断是否处于编辑模式 (修改现有 BOM)
            if st.session_state.get("bom_edit_mode", False):
                 if bom:
                    _render_bom_form(data_manager, bom)
                 else:
                     st.info("BOM 未找到")
            elif bom:
                _render_bom_detail(data_manager, bom)
            else:
                st.info("BOM 未找到 (可能已删除)")
                if st.button("返回列表"):
                    st.session_state.bom_active_id = None
                    st.rerun()
        else:
            st.info("请选择左侧 BOM 查看详情")

def _render_bom_form(data_manager, bom=None):
    st.markdown("#### 编辑 BOM 基本信息")
    with st.form("bom_base_form"):
        code = st.text_input("BOM 编号", value=bom.get("bom_code", "") if bom else "")
        name = st.text_input("BOM 名称", value=bom.get("bom_name", "") if bom else "")
        
        # 定义类型选项和映射
        type_options = ["母液", "成品", "速凝剂", "防冻剂"]
        current_type = bom.get("bom_type", "母液") if bom else "母液"
        
        # 兼容旧数据 (如果旧数据是英文，转为中文显示，保存时存中文)
        if current_type == "mother_liquor": current_type = "母液"
        elif current_type == "product": current_type = "成品"
        
        # 确保 current_type 在选项中，防止索引错误
        try:
            type_index = type_options.index(current_type)
        except ValueError:
            type_index = 0
            
        bom_type = st.selectbox("BOM 类型", type_options, index=type_index)
        
        # 生产模式
        current_mode = bom.get("production_mode", "自产") if bom else "自产"
        mode_options = ["自产", "代工"]
        try:
            mode_index = mode_options.index(current_mode)
        except ValueError:
            mode_index = 0
            
        prod_mode = st.radio("生产模式", mode_options, index=mode_index, horizontal=True)
        
        current_oem = bom.get("oem_manufacturer", "") if bom else ""
        oem_name = st.text_input("代工厂家名称", value=current_oem, placeholder="若是代工，请填写厂家名称")
        
        submitted = st.form_submit_button("保存")
        if submitted:
            if not code or not name:
                st.error("编号和名称必填")
            elif prod_mode == "代工" and not oem_name.strip():
                st.error("选择代工模式时，必须填写代工厂家名称")
            else:
                data = {
                    "bom_code": code,
                    "bom_name": name,
                    "bom_type": bom_type,
                    "status": "active", # 默认激活
                    "production_mode": prod_mode,
                    "oem_manufacturer": oem_name if prod_mode == "代工" else ""
                }
                if bom:
                    if data_manager.update_bom(bom['id'], data):
                        st.success("更新成功")
                        st.session_state.bom_edit_mode = False
                        st.rerun()
                else:
                    new_id = data_manager.add_bom(data)
                    if new_id:
                        st.success("创建成功")
                        st.session_state.bom_active_id = new_id
                        st.session_state.bom_edit_mode = False
                        st.rerun()
    
    if bom:
         if st.button("取消编辑"):
             st.session_state.bom_edit_mode = False
             st.rerun()

def _render_bom_detail(data_manager, bom):
    # 标题栏：显示信息 + 操作按钮
    col_title, col_ops = st.columns([3, 1])
    with col_title:
        st.markdown(f"### {bom.get('bom_code')} - {bom.get('bom_name')}")
        
        mode = bom.get('production_mode', '自产')
        mode_text = f"{mode}"
        if mode == "代工":
            mode_text += f" ({bom.get('oem_manufacturer', '-')})"
            
        st.caption(f"类型: {bom.get('bom_type')} | 状态: {bom.get('status')} | 模式: {mode_text}")
    
    with col_ops:
        if st.button("🗑️ 删除 BOM", type="primary"):
            # 确认删除逻辑 (简单起见直接删，或者弹窗确认)
            # Streamlit 原生没有弹窗，可以用 session_state 做二次确认
            st.session_state[f"confirm_del_bom_{bom['id']}"] = True
        
        if st.session_state.get(f"confirm_del_bom_{bom['id']}", False):
            st.warning("确定要删除吗？这将删除所有版本。")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ 确认", key=f"yes_del_{bom['id']}"):
                    if data_manager.delete_bom(bom['id']):
                        st.success("已删除")
                        st.session_state.bom_active_id = None
                        del st.session_state[f"confirm_del_bom_{bom['id']}"]
                        st.rerun()
            with c2:
                if st.button("❌ 取消", key=f"no_del_{bom['id']}"):
                     del st.session_state[f"confirm_del_bom_{bom['id']}"]
                     st.rerun()
                     
    if st.button("✏️ 编辑基本信息"):
         st.session_state.bom_edit_mode = True
         st.rerun()

    # 版本管理
    st.divider()
    st.markdown("#### 版本管理")
    
    versions = data_manager.get_bom_versions(bom['id'])
    
    # 新增版本按钮
    if st.button("➕ 新增版本"):
        new_ver_num = f"V{len(versions) + 1}"
        ver_data = {
            "bom_id": bom['id'],
            "version": new_ver_num,
            "effective_from": datetime.now().strftime("%Y-%m-%d"),
            "yield_base": 1000.0,
            "lines": []
        }
        data_manager.add_bom_version(ver_data)
        st.rerun()
        
    if not versions:
        st.info("暂无版本，请点击新增")
    else:
        # 版本Tabs
        ver_tabs = st.tabs([v.get('version', 'V?') for v in versions])
        
        # 准备原材料选项
        materials = data_manager.get_all_raw_materials()
        mat_options = {f"{m['name']} ({m.get('material_number')})": m['id'] for m in materials}
        
        for i, ver in enumerate(versions):
            with ver_tabs[i]:
                _render_version_editor(data_manager, ver, mat_options)

def _render_version_editor(data_manager, version, mat_options):
    current_lines = version.get("lines", [])

    col1, col2 = st.columns(2)
    with col1:
        eff_from = st.date_input("生效日期", 
                               value=pd.to_datetime(version.get("effective_from", datetime.now())).date(),
                               key=f"eff_from_{version['id']}")
    with col2:
        yield_base = st.number_input("基准产量 (kg)", value=float(version.get("yield_base", 1000.0)), key=f"yield_{version['id']}")
    
    # 实时显示总量校验
    total_qty_display = sum(float(line.get('qty', 0)) for line in current_lines)
    diff = total_qty_display - yield_base
    
    c_m1, c_m2, c_m3 = st.columns(3)
    c_m1.metric("当前物料总量", f"{total_qty_display:.3f} kg")
    c_m2.metric("设定基准产量", f"{yield_base:.3f} kg")
    c_m3.metric("差异", f"{diff:.3f} kg", delta_color="normal" if abs(diff) < 1e-6 else "inverse")

    # 更新头信息按钮
    if st.button("更新版本头信息", key=f"save_head_{version['id']}"):
        # 1) 计算当前明细总量
        total_qty = sum(float(line.get('qty', 0)) for line in current_lines)
        # 2) 校验
        if abs(total_qty - yield_base) > 1e-6:   # 允许 0.000001 误差
            st.error(f"物料总量 {total_qty:.3f} kg 与基准产量 {yield_base} kg 不一致，请先调整明细或输入管理员密码强制保存")
            # 3) 密码输入框
            with st.form(key=f"pwd_force_head_{version['id']}"):
                pwd = st.text_input("管理员密码", type="password", placeholder="默认 admin")
                submitted = st.form_submit_button("强制保存")
                if submitted and pwd == "admin":
                    data_manager.update_bom_version(version['id'], {
                        "effective_from": eff_from.strftime("%Y-%m-%d"),
                        "yield_base": yield_base
                    })
                    st.success("已强制保存")
                    st.rerun()
                elif submitted:
                    st.error("密码错误")
        else:
            data_manager.update_bom_version(version['id'], {
                "effective_from": eff_from.strftime("%Y-%m-%d"),
                "yield_base": yield_base
            })
            st.success("已保存")
            st.rerun()
    
    st.markdown("##### BOM 明细")
    
    # 使用 data_editor 编辑明细
    
    # 转换为 DataFrame 方便编辑
    # 结构: item_id (dropdown), qty, uom, phase, remark
    
    # 为了让 data_editor 支持下拉，我们需要构造一个包含显示名称的列
    # 但 data_editor 的 column_config.Selectbox 需要预定义的 options
    # 这里为了简化，我们先用两步法：添加行区域 + 简单表格展示/删除
    
    # 展示现有行
    if current_lines:
        for idx, line in enumerate(current_lines):
            c1, c2, c3, c4, c5 = st.columns([3, 1.5, 1, 1, 0.5])
            with c1:
                st.write(f"{line.get('item_name')}")
            with c2:
                st.write(f"{line.get('qty')} {line.get('uom')}")
            with c3:
                st.write(f"{line.get('phase', '-')}")
            with c4:
                st.write(f"{line.get('remark', '')}")
            with c5:
                if st.button("🗑️", key=f"del_line_{version['id']}_{idx}"):
                    del current_lines[idx]
                    data_manager.update_bom_version(version['id'], {"lines": current_lines})
                    st.rerun()
    
    st.divider()
    st.markdown("➕ 添加明细行")
    with st.form(f"add_line_form_{version['id']}", clear_on_submit=True):
        lc1, lc2, lc3 = st.columns([3, 1, 1])
        with lc1:
            sel_mat_label = st.selectbox("选择原材料", list(mat_options.keys()))
        with lc2:
            l_qty = st.number_input("数量", min_value=0.0, step=0.1)
        with lc3:
            l_phase = st.text_input("阶段 (e.g. A料)", value="")
            
        submitted = st.form_submit_button("添加")
        if submitted:
            mat_id = mat_options[sel_mat_label]
            mat_name = sel_mat_label.split(' (')[0]
            
            new_line = {
                "item_type": "raw_material",
                "item_id": mat_id,
                "item_name": mat_name,
                "qty": l_qty,
                "uom": "kg",
                "phase": l_phase,
                "remark": ""
            }
            current_lines.append(new_line)
            data_manager.update_bom_version(version['id'], {"lines": current_lines})
            st.rerun()

def _render_production_management(data_manager):
    st.subheader("生产订单管理")
    
    if "prod_view" not in st.session_state:
        st.session_state.prod_view = "list" # list, create, detail
    if "active_order_id" not in st.session_state:
        st.session_state.active_order_id = None
        
    if st.session_state.prod_view == "list":
        if st.button("➕ 创建生产单"):
            st.session_state.prod_view = "create"
            st.rerun()
            
        orders = data_manager.get_all_production_orders()
        
        # 搜索过滤
        search_term = st.text_input("🔍 搜索生产单", placeholder="单号").strip().lower()
        
        if not orders:
            st.info("暂无生产单")
        else:
            if search_term:
                orders = [o for o in orders if search_term in o.get('order_code', '').lower()]
            
            # 简单表格 (按创建时间倒序)
            orders.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            st.dataframe(
                pd.DataFrame(orders)[["id", "order_code", "status", "plan_qty", "created_at"]],
                use_container_width=True
            )
            
            # 选择操作
            c_sel, c_btn = st.columns([3, 1])
            with c_sel:
                selected_oid = st.selectbox("选择生产单查看详情", [o['id'] for o in orders], format_func=lambda x: f"Order #{x} - {next((o['order_code'] for o in orders if o['id']==x), '')}")
            with c_btn:
                if st.button("查看详情"):
                    st.session_state.active_order_id = selected_oid
                    st.session_state.prod_view = "detail"
                    st.rerun()
                
    elif st.session_state.prod_view == "create":
        st.markdown("#### 新建生产单")
        
        # 使用 key 来保留状态，但 form 会在提交后清空，所以我们用 session_state 
        if "new_prod_mode" not in st.session_state: st.session_state.new_prod_mode = "自产"
        
        # 生产模式选择（放在 form 外面或者作为 form 的一部分）
        # 这里为了交互流畅（选择代工后显示厂家输入框），建议把模式选择放在 form 外面，或者使用 st.radio
        
        with st.form("new_order_form"):
            # 选择 BOM
            boms = data_manager.get_all_boms()
            bom_opts = {f"{b['bom_code']} {b['bom_name']}": b for b in boms}
            sel_bom_label = st.selectbox("选择产品 BOM", list(bom_opts.keys()))
            
            plan_qty = st.number_input("计划产量", min_value=0.0, step=100.0, value=1000.0)
            
            # 生产模式
            prod_mode = st.radio("生产模式", ["自产", "代工"], horizontal=True)
            oem_name = st.text_input("代工厂家名称", placeholder="若是代工，请填写厂家名称")
            
            if st.form_submit_button("创建"):
                # 校验
                if prod_mode == "代工" and not oem_name.strip():
                    st.error("选择代工模式时，必须填写代工厂家名称")
                else:
                    sel_bom = bom_opts[sel_bom_label]
                    # 获取最新版本
                    vers = data_manager.get_bom_versions(sel_bom['id'])
                    if not vers:
                        st.error("该 BOM 没有版本，无法创建")
                    else:
                        # 默认选最后一个版本
                        target_ver = vers[-1]
                        
                        new_order = {
                            "order_code": f"PROD-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4]}",
                            "bom_id": sel_bom['id'],
                            "bom_version_id": target_ver['id'],
                            "plan_qty": plan_qty,
                            "status": "draft",
                            "production_mode": prod_mode,
                            "oem_manufacturer": oem_name if prod_mode == "代工" else ""
                        }
                        new_id = data_manager.add_production_order(new_order)
                        st.success(f"创建成功 #{new_id}")
                        st.session_state.active_order_id = new_id
                        st.session_state.prod_view = "detail"
                        st.rerun()
        
        if st.button("取消"):
            st.session_state.prod_view = "list"
            st.rerun()
            
    elif st.session_state.prod_view == "detail":
        col_back, col_del = st.columns([6, 1])
        with col_back:
            if st.button("⬅️ 返回列表"):
                st.session_state.prod_view = "list"
                st.rerun()
        
        orders = data_manager.get_all_production_orders()
        order = next((o for o in orders if o.get('id') == st.session_state.active_order_id), None)
        
        if not order:
            st.error("订单未找到")
        else:
            # 删除按钮逻辑
            with col_del:
                if st.button("🗑️ 删除", key="del_prod_btn"):
                     st.session_state.confirm_del_prod = True
            
            if st.session_state.get("confirm_del_prod", False):
                st.warning("确定删除该生产单？")
                if st.button("✅ 确认删除"):
                    success, msg = data_manager.delete_production_order(order['id'])
                    if success:
                        st.success(msg)
                        st.session_state.prod_view = "list"
                        st.session_state.active_order_id = None
                        del st.session_state.confirm_del_prod
                        st.rerun()
                    else:
                        st.error(msg)
                if st.button("❌ 取消"):
                    del st.session_state.confirm_del_prod
                    st.rerun()

            st.markdown(f"### 生产单: {order.get('order_code')}")
            
            # 显示生产模式和代工厂
            mode = order.get('production_mode', '自产') # 默认为自产兼容旧数据
            mode_text = f"模式: {mode}"
            if mode == "代工":
                mode_text += f" | 厂家: {order.get('oem_manufacturer', '-')}"
            
            st.caption(f"状态: {order.get('status')} | 计划产量: {order.get('plan_qty')} | {mode_text}")
            
            # 编辑计划产量 (仅限 Draft 状态)
            if order.get('status') == 'draft':
                 new_qty = st.number_input("修改计划产量", value=float(order.get('plan_qty')), min_value=0.0, step=100.0)
                 if new_qty != float(order.get('plan_qty')):
                     if st.button("保存产量修改"):
                         data_manager.update_production_order(order['id'], {"plan_qty": new_qty})
                         st.success("已更新")
                         st.rerun()

            # 状态流转
            if order.get('status') == 'draft':
                if st.button("🚀 下达生产 (Released)"):
                    data_manager.update_production_order(order['id'], {"status": "released"})
                    st.rerun()
            
            if order.get('status') == 'released':
                st.info("生产已下达，请生成领料单")
                if st.button("📄 生成领料单"):
                    issue_id = data_manager.create_issue_from_order(order['id'])
                    if issue_id:
                        st.success("领料单已生成")
                        data_manager.update_production_order(order['id'], {"status": "issued"})
                        st.rerun()
                        
            # 关联领料单
            issues = data_manager.get_material_issues(order['id'])
            if issues:
                st.markdown("#### 关联领料单")
                for issue in issues:
                    with st.expander(f"{issue.get('issue_code')} ({issue.get('status')})", expanded=True):
                        # 显示明细
                        lines = issue.get('lines', [])
                        if lines:
                            df_lines = pd.DataFrame(lines)
                            # 确保所需的列存在
                            required_cols = ['item_name', 'required_qty', 'uom']
                            display_cols = [col for col in required_cols if col in df_lines.columns]
                            
                            if display_cols:
                                st.table(df_lines[display_cols])
                            else:
                                st.table(df_lines) # 显示所有列作为后备
                        else:
                            st.info("无领料明细")
                        
                        if issue.get('status') == 'draft':
                            if st.button("✅ 确认领料过账 (Post)", key=f"post_{issue['id']}"):
                                success, msg = data_manager.post_issue(issue['id'], operator="User")
                                if success:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
                        
                        elif issue.get('status') == 'posted':
                            st.success(f"已过账于 {issue.get('posted_at')}")
                            # 撤销过账按钮
                            if st.button("↩️ 撤销过账 (Cancel)", key=f"cancel_{issue['id']}"):
                                success, msg = data_manager.cancel_issue_posting(issue['id'], operator="User")
                                if success:
                                    st.warning(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
            
            # 完工入库 (简化)
            if order.get('status') == 'issued': # 已领料
                st.divider()
                if st.button("🏁 完工入库 (Finish)"):
                     data_manager.update_production_order(order['id'], {"status": "finished"})
                     st.success("订单已完工")
                     st.rerun()

def _render_inventory_reports(data_manager):
    st.subheader("库存台账报表")
    
    tab_bal, tab_ledger = st.tabs(["💰 库存余额", "📝 台账流水"])
    
    with tab_bal:
        balances = data_manager.get_stock_balance()
        materials = data_manager.get_all_raw_materials()
        mat_map = {m['id']: m for m in materials}
        
        report_data = []
        for mid, qty in balances.items():
            mat = mat_map.get(mid)
            if mat:
                report_data.append({
                    "物料名称": mat['name'],
                    "物料号": mat.get('material_number'),
                    "当前库存": qty,
                    "单位": mat.get('unit', 'kg')
                })
        
        if report_data:
            st.dataframe(pd.DataFrame(report_data), use_container_width=True)
        else:
            st.info("暂无库存数据")
            
    with tab_ledger:
        records = data_manager.get_inventory_records()
        if records:
            df = pd.DataFrame(records)
            # 简单的列重命名
            st.dataframe(df.sort_values("created_at", ascending=False), use_container_width=True)
        else:
            st.info("暂无台账记录")
