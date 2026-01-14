import streamlit as st
from datetime import datetime
import pandas as pd
import uuid
import io
from utils.unit_helper import convert_quantity, normalize_unit

def render_sap_bom(data_manager):
    """渲染 SAP/BOM 管理页面"""
    st.header("🏭 SAP/BOM 管理")
    
    tab1, tab2, tab3, tab4 = st.tabs(["🧬 BOM 管理", "🏭 生产管理", "🚚 发货管理", "📈 台账报表"])
    
    with tab1:
        _render_bom_management(data_manager)
    
    with tab2:
        _render_production_management(data_manager)

    with tab3:
        _render_shipping_management(data_manager)
        
    with tab4:
        _render_inventory_reports(data_manager)

def _render_bom_management(data_manager):
    st.subheader("BOM 主数据管理")
    
    user = st.session_state.get("current_user")
    if not user or user.get("role") != "admin":
        st.info("仅管理员可以维护 BOM 主数据。")
        return
    
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
        admin_pwd = None
        if bom:
            admin_pwd = st.text_input("管理员口令", type="password", key=f"bom_admin_pwd_{bom['id']}")
        
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
                    "status": "active",
                    "production_mode": prod_mode,
                    "oem_manufacturer": oem_name if prod_mode == "代工" else ""
                }
                if bom:
                    if not admin_pwd:
                        st.error("请填写管理员口令")
                    elif not data_manager.verify_admin_password(admin_pwd):
                        st.error("管理员口令错误")
                    elif data_manager.update_bom(bom['id'], data):
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
            st.session_state[f"confirm_del_bom_{bom['id']}"] = True
        
        if st.session_state.get(f"confirm_del_bom_{bom['id']}", False):
            st.warning("确定要删除吗？这将删除该 BOM 及其所有版本。")
            pwd = st.text_input("管理员口令", type="password", key=f"del_bom_pwd_{bom['id']}")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ 确认", key=f"yes_del_{bom['id']}"):
                    if not pwd:
                        st.error("请填写管理员口令")
                    elif not data_manager.verify_admin_password(pwd):
                        st.error("管理员口令错误")
                    elif data_manager.delete_bom(bom['id']):
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

    # 结构树可视化
    with st.expander("🌳 查看多级 BOM 结构树"):
        _render_bom_tree_recursive(data_manager, bom['id'])

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
    locked = bool(version.get("locked", False))
    auth_key = f"ver_edit_auth_{version['id']}"
    if auth_key not in st.session_state:
        st.session_state[auth_key] = False

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

    if st.button("更新版本头信息", key=f"save_head_{version['id']}"):
        if locked and not st.session_state[auth_key]:
            with st.form(key=f"pwd_head_{version['id']}"):
                pwd = st.text_input("管理员密码", type="password")
                submitted = st.form_submit_button("开始修改")
                if submitted and data_manager.verify_admin_password(pwd):
                    st.session_state[auth_key] = True
                    st.success("已验证")
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
                if not locked or st.session_state[auth_key]:
                    if st.button("🗑️", key=f"del_line_{version['id']}_{idx}"):
                        del current_lines[idx]
                        data_manager.update_bom_version(version['id'], {"lines": current_lines})
                        st.rerun()
    
    st.divider()
    with st.expander("➕ 单个添加 | 📂 批量导入 (Excel)", expanded=False):
        if locked and not st.session_state[auth_key]:
            st.info("版本已保存，修改需要管理员密码")
            with st.form(key=f"pwd_edit_{version['id']}"):
                pwd = st.text_input("管理员密码", type="password")
                submitted = st.form_submit_button("开始修改")
                if submitted and data_manager.verify_admin_password(pwd):
                    st.session_state[auth_key] = True
                    st.success("已验证")
                    st.rerun()
                elif submitted:
                    st.error("密码错误")
        else:
            # 获取原材料和成品库存选项
            raw_materials = data_manager.get_all_raw_materials()
            product_inventory = data_manager.get_product_inventory()
            
            combined_options = {}
            for m in raw_materials:
                label = f"[原材料] {m['name']} ({m.get('material_number', '-')})"
                combined_options[label] = f"raw_material:{m['id']}"
            for p in product_inventory:
                label = f"[成品] {p['name']} ({p.get('type', '其他')})"
                combined_options[label] = f"product:{p['id']}"

            with st.form(f"add_line_form_{version['id']}", clear_on_submit=True):
                lc1, lc2, lc3 = st.columns([3, 1, 1])
                with lc1:
                    sel_item_label = st.selectbox("选择物料 (原材料/产品)", list(combined_options.keys()))
                with lc2:
                    l_qty = st.number_input("数量", min_value=0.0, step=0.1)
                with lc3:
                    l_phase = st.text_input("阶段 (e.g. A料)", value="")
                
                # 新增替代料说明输入
                l_subs = st.text_input("替代料说明 (可选)", placeholder="例如: 可用类似规格替代")
                
                submitted = st.form_submit_button("添加")
                if submitted:
                    type_id_str = combined_options[sel_item_label]
                    item_type, item_id = type_id_str.split(":")
                    
                    # 提取名称
                    item_name = sel_item_label
                    if "]" in item_name:
                         try:
                             item_name = item_name.split("] ", 1)[1].rsplit(" (", 1)[0]
                         except:
                             pass
                    
                    new_line = {
                        "item_type": item_type,
                        "item_id": int(item_id),
                        "item_name": item_name,
                        "qty": l_qty,
                        "uom": "kg",
                        "phase": l_phase,
                        "remark": "",
                        "substitutes": l_subs # 保存替代料
                    }
                    current_lines.append(new_line)
                    data_manager.update_bom_version(version['id'], {"lines": current_lines})
                    st.rerun()
    st.divider()
    if not locked:
        if st.button("保存版本", key=f"save_version_{version['id']}"):
            total_qty = sum(float(line.get('qty', 0)) for line in current_lines)
            if abs(total_qty - yield_base) > 1e-6:
                st.error(f"物料总量 {total_qty:.3f} kg 与基准产量 {yield_base} kg 不一致")
                with st.form(key=f"pwd_force_save_{version['id']}"):
                    pwd = st.text_input("管理员密码", type="password")
                    submitted = st.form_submit_button("强制保存")
                    if submitted and data_manager.verify_admin_password(pwd):
                        data_manager.update_bom_version(version['id'], {
                            "effective_from": eff_from.strftime("%Y-%m-%d"),
                            "yield_base": yield_base,
                            "lines": current_lines,
                            "locked": True
                        })
                        st.success("已保存并锁定")
                        st.rerun()
                    elif submitted:
                        st.error("密码错误")
            else:
                data_manager.update_bom_version(version['id'], {
                    "effective_from": eff_from.strftime("%Y-%m-%d"),
                    "yield_base": yield_base,
                    "lines": current_lines,
                    "locked": True
                })
                st.success("已保存并锁定")
                st.rerun()
    else:
        st.success("版本已保存")

def _render_production_management(data_manager):
    st.subheader("生产订单管理")
    
    user = st.session_state.get("current_user")
    if not user:
        st.info("请登录后查看生产订单。")
        return
    
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
            
            boms = data_manager.get_all_boms()
            bom_map = {}
            for b in boms:
                code = str(b.get('bom_code', '')).strip()
                name = str(b.get('bom_name', '')).strip()
                bom_map[b.get('id')] = f"{code}-{name}" if code else name
            display_rows = []
            for o in orders:
                pname = bom_map.get(o.get('bom_id'), "")
                display_rows.append({
                    "产品名称": pname,
                    "生产单号": o.get("order_code", ""),
                    "状态": o.get("status", ""),
                    "计划产量 (kg)": o.get("plan_qty", 0),
                    "创建时间": o.get("created_at", "")
                })
            df_orders = pd.DataFrame(display_rows)
            st.dataframe(df_orders, use_container_width=True)
            csv_orders = df_orders.to_csv(index=False, encoding="utf-8-sig")
            st.download_button("导出CSV", csv_orders, file_name="生产单列表.csv", mime="text/csv")
            out_orders = io.BytesIO()
            try:
                with pd.ExcelWriter(out_orders, engine='xlsxwriter') as writer:
                    df_orders.to_excel(writer, index=False, sheet_name='生产单列表')
                    wb = writer.book
                    ws = writer.sheets['生产单列表']
                    fmt = wb.add_format({'bold': True})
                    for i, col in enumerate(df_orders.columns):
                        ws.write(0, i, col, fmt)
            except:
                with pd.ExcelWriter(out_orders) as writer:
                    df_orders.to_excel(writer, index=False, sheet_name='生产单列表')
            st.download_button("导出Excel", out_orders.getvalue(), file_name="生产单列表.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            st.divider()
            st.markdown("#### 生产计划报表")
            plan_batch_kg = 10000.0
            raw_materials = data_manager.get_all_raw_materials()
            mat_inv = {}
            for m in raw_materials:
                qty = float(m.get("stock_quantity", 0.0))
                unit = m.get("unit", "kg")
                base_qty, ok = convert_quantity(qty, unit, "kg")
                mat_inv[m["id"]] = base_qty if ok else qty
            target_types = ["母液", "速凝剂"]
            type_boms = [b for b in boms if b.get("bom_type") in target_types]
            versions = data_manager.get_bom_versions(0)
            all_versions = data_manager.load_data().get("bom_versions", [])
            def latest_valid_version(bid):
                vs = [v for v in all_versions if v.get("bom_id") == bid]
                for v in reversed(vs):
                    if v.get("lines"):
                        return v
                return None
            def per_batch_require(v):
                base = float(v.get("yield_base", 1000.0) or 1000.0)
                if base <= 0:
                    base = 1000.0
                ratio = plan_batch_kg / base
                req = {}
                for line in v.get("lines", []):
                    if line.get("item_type", "raw_material") == "raw_material":
                        mid = line.get("item_id")
                        lqty = float(line.get("qty", 0.0))
                        luom = line.get("uom", "kg")
                        need = lqty * ratio
                        need_kg, ok = convert_quantity(need, luom, "kg")
                        req[mid] = req.get(mid, 0.0) + (need_kg if ok else need)
                return req
            def scarcity_score(req):
                s = 0.0
                for mid, q in req.items():
                    avail = mat_inv.get(mid, 0.0)
                    w = 1.0 / (avail if avail > 0 else 1e-9)
                    s += q * w
                return s
            candidates = []
            for b in type_boms:
                v = latest_valid_version(b["id"])
                if not v:
                    continue
                req = per_batch_require(v)
                if not req:
                    continue
                score = scarcity_score(req)
                batches = min([int((mat_inv.get(mid, 0.0)) // q) if q > 0 else 0 for mid, q in req.items()]) if req else 0
                candidates.append({
                    "bom_id": b["id"],
                    "bom_label": bom_map.get(b["id"]),
                    "bom_type": b.get("bom_type"),
                    "version_id": v["id"],
                    "per_batch_require": req,
                    "scarcity_score": score,
                    "max_batches_possible": batches
                })
            by_type = {}
            for c in candidates:
                t = c["bom_type"]
                if t not in by_type or c["scarcity_score"] < by_type[t]["scarcity_score"]:
                    by_type[t] = c
            report_rows = []
            for t, sel in by_type.items():
                total_req = sum(sel["per_batch_require"].values())
                report_rows.append({
                    "产品类型": t,
                    "选用配方": sel["bom_label"],
                    "可生产批次": sel["max_batches_possible"],
                    "每批次原材料合计(kg)": round(total_req, 4)
                })
            if report_rows:
                st.dataframe(pd.DataFrame(report_rows), use_container_width=True)
                csv_plan = pd.DataFrame(report_rows).to_csv(index=False, encoding="utf-8-sig")
                st.download_button("导出CSV", csv_plan, file_name="生产计划报表.csv", mime="text/csv")
                out_plan = io.BytesIO()
                df_plan = pd.DataFrame(report_rows)
                try:
                    with pd.ExcelWriter(out_plan, engine='xlsxwriter') as writer:
                        df_plan.to_excel(writer, index=False, sheet_name='生产计划报表')
                        wb = writer.book
                        ws = writer.sheets['生产计划报表']
                        fmt = wb.add_format({'bold': True})
                        for i, col in enumerate(df_plan.columns):
                            ws.write(0, i, col, fmt)
                except:
                    with pd.ExcelWriter(out_plan) as writer:
                        df_plan.to_excel(writer, index=False, sheet_name='生产计划报表')
                st.download_button("导出Excel", out_plan.getvalue(), file_name="生产计划报表.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                st.markdown("##### 原材料消耗与预警")
                warn_rows = []
                for m in raw_materials:
                    mid = m["id"]
                    name = m["name"]
                    avail = mat_inv.get(mid, 0.0)
                    need_30 = 0.0
                    for t, sel in by_type.items():
                        q = sel["per_batch_require"].get(mid, 0.0)
                        need_30 += q * 3
                    est_batches = 0
                    if need_30 > 0:
                        est_batches = round(avail / (need_30 / 3.0), 4)
                    warn = avail < need_30 and need_30 > 0
                    warn_rows.append({
                        "原材料名称": name,
                        "当前库存(kg)": round(avail, 4),
                        "预计剩余生产批次": est_batches,
                        "预警": "是" if warn else "否"
                    })
                df_warn = pd.DataFrame(warn_rows)
                def _hl(row):
                    return ['background-color: #ffecec; color: #c1121f' if row['预警'] == '是' else '' for _ in row]
                st.dataframe(df_warn.style.apply(_hl, axis=1), use_container_width=True)
                csv_warn = df_warn.to_csv(index=False, encoding="utf-8-sig")
                st.download_button("导出CSV", csv_warn, file_name="原材料预警.csv", mime="text/csv")
                out_warn = io.BytesIO()
                try:
                    with pd.ExcelWriter(out_warn, engine='xlsxwriter') as writer:
                        df_warn.to_excel(writer, index=False, sheet_name='原材料预警')
                        wb = writer.book
                        ws = writer.sheets['原材料预警']
                        fmt = wb.add_format({'bold': True})
                        for i, col in enumerate(df_warn.columns):
                            ws.write(0, i, col, fmt)
                except:
                    with pd.ExcelWriter(out_warn) as writer:
                        df_warn.to_excel(writer, index=False, sheet_name='原材料预警')
                st.download_button("导出Excel", out_warn.getvalue(), file_name="原材料预警.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                col_exec1, col_exec2 = st.columns(2)
                with col_exec1:
                    if st.button("创建10吨生产单"):
                        for t, sel in by_type.items():
                            new_order = {
                                "order_code": f"PROD-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4]}",
                                "bom_id": sel["bom_id"],
                                "bom_version_id": sel["version_id"],
                                "plan_qty": plan_batch_kg,
                                "status": "draft",
                                "production_mode": "自产",
                                "oem_manufacturer": ""
                            }
                            data_manager.add_production_order(new_order)
                        st.success("已创建生产单")
                        st.rerun()
            
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
            # 2026-01-13 Update: 统一使用 {bom_code}-{bom_name} 格式
            bom_opts = {}
            for b in boms:
                code = b.get('bom_code', '').strip()
                name = b['bom_name'].strip()
                label = f"{code}-{name}" if code else name
                bom_opts[label] = b
            
            sel_bom_label = st.selectbox("选择产品 BOM", list(bom_opts.keys()))
            
            plan_qty = st.number_input("计划产量 (kg)", min_value=0.0, step=100.0, value=1000.0)
            
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
                        # 选择最新且有明细的版本（倒序查找）
                        target_ver = None
                        for v in reversed(vers):
                            if v.get("lines"):
                                target_ver = v
                                break
                        if not target_ver:
                            st.error("该 BOM 的所有版本均无明细，请先维护版本行项目")
                            st.stop()
                        
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
            
            st.caption(f"状态: {order.get('status')} | 计划产量: {order.get('plan_qty')} kg | {mode_text}")
            
            # 编辑计划产量 (仅限 Draft 状态)
            if order.get('status') == 'draft':
                 new_qty = st.number_input("修改计划产量 (kg)", value=float(order.get('plan_qty')), min_value=0.0, step=100.0)
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
                     # 使用新方法，自动更新成品库存
                     success, msg = data_manager.finish_production_order(order['id'])
                     if success:
                         st.success(msg)
                         st.rerun()
                     else:
                         st.error(msg)

def _render_shipping_management(data_manager):
    st.subheader("发货管理")
    
    # 1. 发货操作区域
    st.markdown("#### 📦 新增发货单")
    
    # 获取成品库存列表
    inventory = data_manager.get_product_inventory()
    if not inventory:
        st.warning("暂无成品库存，无法进行发货操作。请先进行生产入库。")
    else:
        with st.form("shipping_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                # 构造选项: "名称 (库存: 100 吨)"
                prod_options = {f"{p['name']} ({p.get('type', '-')}) - 库存: {float(p.get('stock_quantity', 0)):.2f} {p.get('unit', '吨')}": p for p in inventory}
                labels = [""] + list(prod_options.keys())
                sel_label = st.selectbox("选择发货产品", labels, index=0)
                
            with col2:
                ship_qty_text = st.text_input("发货数量 (吨)", value="")
            
            col3, col4 = st.columns(2)
            with col3:
                customer = st.text_input("客户名称 / 目的地")
            with col4:
                ship_date = st.date_input("发货日期", datetime.now())
                
            remark = st.text_input("备注 (订单号/物流单号)")
            
            submitted = st.form_submit_button("确认发货", type="primary")
            
            if submitted:
                if not sel_label:
                    st.error("请选择发货产品")
                elif not ship_qty_text.strip():
                    st.error("请输入发货数量")
                elif not customer:
                    st.error("请填写客户名称")
                else:
                    try:
                        ship_qty = float(ship_qty_text.strip())
                    except:
                        st.error("发货数量格式错误")
                        st.stop()
                    if ship_qty <= 0:
                        st.error("发货数量必须大于0")
                        st.stop()
                    selected_prod = prod_options[sel_label]
                    current_stock = float(selected_prod.get('stock_quantity', 0))
                    
                    if ship_qty > current_stock:
                        st.error(f"库存不足！当前库存: {current_stock:.2f} 吨")
                    else:
                        # 构造记录数据
                        record_data = {
                            "product_name": selected_prod['name'],
                            "product_type": selected_prod.get('type', '其他'),
                            "quantity": ship_qty,
                            "type": "out", # 出库
                            "reason": f"发货: {customer} {remark}",
                            "operator": "User", # 实际应获取当前用户
                            "date": ship_date.strftime("%Y-%m-%d"),
                            "related_doc_type": "SHIPPING"
                        }
                        
                        success, msg = data_manager.add_product_inventory_record(record_data)
                        if success:
                            st.success(f"发货成功！已扣减库存 {ship_qty} 吨")
                            st.rerun()
                        else:
                            st.error(msg)

    # 2. 发货记录列表
    st.divider()
    st.markdown("#### 📜 近期发货记录")
    
    records = data_manager.get_product_inventory_records()
    shipping_records = [r for r in records if r.get('related_doc_type') == 'SHIPPING']
    
    if shipping_records:
        # 按时间倒序
        shipping_records.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        df_ship = pd.DataFrame(shipping_records)
        # 选取展示列
        cols = ["date", "product_name", "product_type", "quantity", "reason", "operator", "snapshot_stock"]
        # 确保列存在
        display_cols = [c for c in cols if c in df_ship.columns]
        
        df_display = df_ship[display_cols].copy()
        df_display.columns = [c.replace("date", "日期").replace("product_name", "产品名称")
                              .replace("product_type", "类型").replace("quantity", "数量(吨)")
                              .replace("reason", "详情/备注").replace("operator", "操作人")
                              .replace("snapshot_stock", "发货后结存") for c in df_display.columns]
        
        st.dataframe(df_display, use_container_width=True)
        csv_ship = df_display.to_csv(index=False, encoding="utf-8-sig")
        st.download_button("导出CSV", csv_ship, file_name="发货记录.csv", mime="text/csv")
        out_ship = io.BytesIO()
        try:
            with pd.ExcelWriter(out_ship, engine='xlsxwriter') as writer:
                df_display.to_excel(writer, index=False, sheet_name='发货记录')
                wb = writer.book
                ws = writer.sheets['发货记录']
                fmt = wb.add_format({'bold': True})
                for i, col in enumerate(df_display.columns):
                    ws.write(0, i, col, fmt)
        except:
            with pd.ExcelWriter(out_ship) as writer:
                df_display.to_excel(writer, index=False, sheet_name='发货记录')
        st.download_button("导出Excel", out_ship.getvalue(), file_name="发货记录.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        st.info("暂无发货记录")

def _render_inventory_reports(data_manager):
    st.subheader("库存台账报表")
    
    tab_bal, tab_ledger, tab_prodcons, tab_stats = st.tabs(["💰 库存余额", "📝 台账流水", "📉 成品消耗", "📊 综合统计"])
    
    with tab_bal:
        # 修改逻辑：不再使用 get_stock_balance (纯流水计算)，
        # 而是直接读取原材料主数据的当前库存 (stock_quantity)，因为它包含了初始库存和所有变动。
        # 这样能保证数据的一致性。
        
        materials = data_manager.get_all_raw_materials()
        
        report_data = []
        for mat in materials:
            # 1. 获取当前库存 (基础单位)
            stock_qty = float(mat.get('stock_quantity', 0.0))
            base_unit = mat.get('unit', 'kg')
            
            # 2. 单位转换 (转为吨)
            # 逻辑：
            # - 如果基础单位是 kg/g/lb 等质量单位 -> 转为 ton
            # - 如果基础单位是 L/mL 等体积单位 -> 保持原样或转为 m3 (这里暂保持原样)
            # - 如果已经是 ton -> 保持原样
            
            from utils.unit_helper import convert_quantity, normalize_unit
            
            # 尝试转换到吨
            display_qty, success = convert_quantity(stock_qty, base_unit, 'ton')
            
            if success:
                display_unit = "吨"
            else:
                # 转换失败 (非质量单位)，保持原值
                display_qty = stock_qty
                display_unit = base_unit
            
            report_data.append({
                "物料名称": mat['name'],
                "物料号": mat.get('material_number'),
                "当前库存 (吨)": f"{display_qty:.4f}" if success else f"{display_qty:.4f} ({display_unit})",
                "原始库存": f"{stock_qty:.4f}",
                "原始单位": base_unit
            })
        
        if report_data:
            df_bal = pd.DataFrame(report_data)
            st.dataframe(df_bal, use_container_width=True)
            csv_bal = df_bal.to_csv(index=False, encoding="utf-8-sig")
            st.download_button("导出CSV", csv_bal, file_name="库存余额.csv", mime="text/csv")
            out_bal = io.BytesIO()
            try:
                with pd.ExcelWriter(out_bal, engine='xlsxwriter') as writer:
                    df_bal.to_excel(writer, index=False, sheet_name='库存余额')
                    wb = writer.book
                    ws = writer.sheets['库存余额']
                    fmt = wb.add_format({'bold': True})
                    for i, col in enumerate(df_bal.columns):
                        ws.write(0, i, col, fmt)
            except:
                with pd.ExcelWriter(out_bal) as writer:
                    df_bal.to_excel(writer, index=False, sheet_name='库存余额')
            st.download_button("导出Excel", out_bal.getvalue(), file_name="库存余额.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.info("暂无库存数据")
            
    with tab_ledger:
        records = data_manager.get_inventory_records()
        if records:
            # 补充物料名称 (解决 KeyError: 'material_name')
            materials = data_manager.get_all_raw_materials()
            mat_map = {m['id']: m['name'] for m in materials}
            
            enriched_records = []
            for r in records:
                r_copy = r.copy()
                if "material_name" not in r_copy:
                    # 尝试从 map 获取，如果没有则显示 ID
                    r_copy["material_name"] = mat_map.get(r_copy.get("material_id"), f"Unknown-{r_copy.get('material_id')}")
                enriched_records.append(r_copy)
                
            df = pd.DataFrame(enriched_records)
            
            # 1. 增加筛选器
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                # 提取所有物料名称供筛选
                unique_materials = sorted(list(set(df['material_name'].dropna().unique())))
                sel_mat = st.multiselect("筛选物料", unique_materials)
            with col_f2:
                # 提取操作类型 (in/out) 并转为中文显示
                type_map = {"in": "入库", "out": "出库"}
                sel_type = st.multiselect("筛选类型", ["入库", "出库"])
            with col_f3:
                # 日期范围
                min_date = pd.to_datetime(df['created_at']).min().date()
                max_date = pd.to_datetime(df['created_at']).max().date()
                sel_date = st.date_input("日期范围", [min_date, max_date])

            # 应用筛选
            if sel_mat:
                df = df[df['material_name'].isin(sel_mat)]
            if sel_type:
                # 将中文类型转回英文代码进行筛选
                filter_codes = [k for k, v in type_map.items() if v in sel_type]
                df = df[df['type'].isin(filter_codes)]
            if isinstance(sel_date, list) and len(sel_date) == 2:
                 # 简单的字符串比较筛选 (前提是 created_at 格式为 YYYY-MM-DD HH:MM:SS)
                 start_str = sel_date[0].strftime("%Y-%m-%d")
                 end_str = sel_date[1].strftime("%Y-%m-%d")
                 df = df[(df['created_at'] >= start_str) & (df['created_at'] <= end_str + " 23:59:59")]

            # 2. 数据美化与列重命名
            # 确保按时间倒序
            df = df.sort_values("created_at", ascending=False)
            
            # 映射类型显示
            df['type_display'] = df['type'].map({"in": "📥 入库", "out": "📤 出库"}).fillna(df['type'])
            
            # 格式化数量 (添加单位)
            # 假设 unit 列存在，如果不存在则默认为 kg
            if 'unit' not in df.columns:
                df['unit'] = 'kg'
            df['qty_display'] = df.apply(lambda x: f"{float(x['quantity']):.4f} {x['unit']}", axis=1)
            
            # 选择并重命名列
            # 原始列: id, material_id, material_name, type, quantity, unit, price, created_at, operator, remark, batch_info
            display_cols = {
                "created_at": "时间",
                "material_name": "物料名称",
                "type_display": "操作类型",
                "qty_display": "数量",
                "operator": "操作人",
                "remark": "备注"
            }
            
            # 确保存在的列才显示
            available_cols = [c for c in display_cols.keys() if c in df.columns or c in ['type_display', 'qty_display']]
            
            df_display = df[available_cols].rename(columns=display_cols)
            
            st.dataframe(
                df_display, 
                use_container_width=True,
                hide_index=True
            )
            csv_ledger = df_display.to_csv(index=False, encoding="utf-8-sig")
            st.download_button("导出CSV", csv_ledger, file_name="台账流水.csv", mime="text/csv")
            out_ledger = io.BytesIO()
            try:
                with pd.ExcelWriter(out_ledger, engine='xlsxwriter') as writer:
                    df_display.to_excel(writer, index=False, sheet_name='台账流水')
                    wb = writer.book
                    ws = writer.sheets['台账流水']
                    fmt = wb.add_format({'bold': True})
                    for i, col in enumerate(df_display.columns):
                        ws.write(0, i, col, fmt)
            except:
                with pd.ExcelWriter(out_ledger) as writer:
                    df_display.to_excel(writer, index=False, sheet_name='台账流水')
            st.download_button("导出Excel", out_ledger.getvalue(), file_name="台账流水.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.info("暂无台账记录")

    with tab_prodcons:
        prod_records = data_manager.get_product_inventory_records()
        cons_records = [r for r in prod_records if r.get('type') == 'out' and r.get('related_doc_type') != 'SHIPPING']
        if cons_records:
            display_rows = []
            for r in cons_records:
                reason = str(r.get("reason", "") or "")
                rdt = r.get("related_doc_type")
                src_type = ""
                doc_no = ""
                if rdt:
                    if rdt == "ISSUE":
                        src_type = "生产领料"
                    elif rdt == "SHIPPING":
                        src_type = "发货"
                    else:
                        src_type = rdt
                else:
                    if "生产领料" in reason:
                        src_type = "生产领料"
                        try:
                            part = reason.split("生产领料: ", 1)[1]
                            doc_no = part.split(" ", 1)[0].split("(", 1)[0]
                        except:
                            doc_no = ""
                    else:
                        src_type = "其他"
                if not doc_no and "生产领料" in reason:
                    try:
                        part = reason.split("生产领料: ", 1)[1]
                        doc_no = part.split(" ", 1)[0].split("(", 1)[0]
                    except:
                        doc_no = ""
                display_rows.append({
                    "日期": r.get("date", ""),
                    "产品名称": r.get("product_name", ""),
                    "类型": r.get("product_type", ""),
                    "数量(吨)": r.get("quantity", 0),
                    "来源类型": src_type,
                    "关联单据号": doc_no,
                    "来源/备注": reason,
                    "操作人": r.get("operator", ""),
                    "发出后结存": r.get("snapshot_stock", 0)
                })
            df_cons = pd.DataFrame(display_rows)
            st.dataframe(df_cons, use_container_width=True)
            csv_cons = df_cons.to_csv(index=False, encoding="utf-8-sig")
            st.download_button("导出CSV", csv_cons, file_name="成品消耗.csv", mime="text/csv")
            out_cons = io.BytesIO()
            try:
                with pd.ExcelWriter(out_cons, engine='xlsxwriter') as writer:
                    df_cons.to_excel(writer, index=False, sheet_name='成品消耗')
                    wb = writer.book
                    ws = writer.sheets['成品消耗']
                    fmt = wb.add_format({'bold': True})
                    for i, col in enumerate(df_cons.columns):
                        ws.write(0, i, col, fmt)
            except:
                with pd.ExcelWriter(out_cons) as writer:
                    df_cons.to_excel(writer, index=False, sheet_name='成品消耗')
            st.download_button("导出Excel", out_cons.getvalue(), file_name="成品消耗.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.info("暂无成品消耗记录")

    with tab_stats:
        gran = st.selectbox("统计周期", ["周", "月", "年度"], index=1)
        mats = data_manager.get_inventory_records()
        prods = data_manager.get_product_inventory_records()
        def parse_dt(x, fallback=None):
            if not x and fallback:
                x = fallback
            try:
                return pd.to_datetime(x)
            except:
                return pd.NaT
        def period_str(dt):
            if pd.isna(dt):
                return ""
            if gran == "周":
                iso = dt.isocalendar()
                return f"{iso.year}-W{int(iso.week):02d}"
            if gran == "月":
                return dt.strftime("%Y-%m")
            return dt.strftime("%Y")
        df_m = pd.DataFrame(mats)
        if not df_m.empty:
            if "created_at" in df_m.columns:
                df_m["_dt"] = df_m["created_at"].apply(lambda x: parse_dt(x))
            else:
                df_m["_dt"] = df_m["date"].apply(lambda x: parse_dt(x))
            df_m["period"] = df_m["_dt"].apply(period_str)
            df_m_cons = df_m[df_m.get("type").isin(["consume_out"])].copy()
            mat_agg = df_m_cons.groupby("period")["quantity"].sum().reset_index()
        else:
            mat_agg = pd.DataFrame(columns=["period", "quantity"])
        df_p = pd.DataFrame(prods)
        if not df_p.empty:
            if "created_at" in df_p.columns:
                df_p["_dt"] = df_p["created_at"].apply(lambda x: parse_dt(x))
            else:
                df_p["_dt"] = df_p["date"].apply(lambda x: parse_dt(x))
            df_p["period"] = df_p["_dt"].apply(period_str)
            df_p_prod = df_p[df_p.get("type").isin(["in"])].copy()
            df_p_ship = df_p[(df_p.get("type").isin(["out"])) & (df_p.get("related_doc_type") == "SHIPPING")].copy()
            prod_agg = df_p_prod.groupby("period")["quantity"].sum().reset_index()
            ship_agg = df_p_ship.groupby("period")["quantity"].sum().reset_index()
        else:
            prod_agg = pd.DataFrame(columns=["period", "quantity"])
            ship_agg = pd.DataFrame(columns=["period", "quantity"])
        col1, col2, col3 = st.columns(3)
        with col1:
            st.caption("原材料消耗 (kg)")
            if not mat_agg.empty:
                st.bar_chart(mat_agg.set_index("period"))
                mat_exp = mat_agg.rename(columns={"period": "周期", "quantity": "数量(kg)"})
                csv_mat = mat_exp.to_csv(index=False, encoding="utf-8-sig")
                st.download_button("导出CSV", csv_mat, file_name=f"原材料消耗_{gran}.csv", mime="text/csv")
                out_mat = io.BytesIO()
                try:
                    with pd.ExcelWriter(out_mat, engine='xlsxwriter') as writer:
                        mat_exp.to_excel(writer, index=False, sheet_name='原材料消耗')
                        wb = writer.book
                        ws = writer.sheets['原材料消耗']
                        fmt = wb.add_format({'bold': True})
                        for i, col in enumerate(mat_exp.columns):
                            ws.write(0, i, col, fmt)
                except:
                    with pd.ExcelWriter(out_mat) as writer:
                        mat_exp.to_excel(writer, index=False, sheet_name='原材料消耗')
                st.download_button("导出Excel", out_mat.getvalue(), file_name=f"原材料消耗_{gran}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                materials = data_manager.get_all_raw_materials()
                mat_map = {m['id']: m['name'] for m in materials}
                df_m_cons["_name"] = df_m_cons["material_id"].map(mat_map)
                if "unit" in df_m_cons.columns:
                    df_m_cons["qty_kg"] = df_m_cons.apply(lambda x: convert_quantity(float(x["quantity"]), x["unit"], "kg")[0] if pd.notna(x["unit"]) else float(x["quantity"]), axis=1)
                else:
                    df_m_cons["qty_kg"] = df_m_cons["quantity"].astype(float)
                mat_by_type = df_m_cons.groupby(["period", "_name"])["qty_kg"].sum().reset_index().rename(columns={"_name": "原材料名称"})
                mat_pivot = mat_by_type.pivot(index="原材料名称", columns="period", values="qty_kg").fillna(0.0)
                st.dataframe(mat_pivot.reset_index(), use_container_width=True)
                csv_mat_type = mat_pivot.reset_index().to_csv(index=False, encoding="utf-8-sig")
                st.download_button("导出CSV(按种类)", csv_mat_type, file_name=f"原材料消耗_按种类_{gran}.csv", mime="text/csv")
                out_mat_type = io.BytesIO()
                try:
                    with pd.ExcelWriter(out_mat_type, engine='xlsxwriter') as writer:
                        mat_pivot.reset_index().to_excel(writer, index=False, sheet_name='原材料消耗_按种类')
                        wb = writer.book
                        ws = writer.sheets['原材料消耗_按种类']
                        fmt = wb.add_format({'bold': True})
                        for i, col in enumerate(mat_pivot.reset_index().columns):
                            ws.write(0, i, col, fmt)
                except:
                    with pd.ExcelWriter(out_mat_type) as writer:
                        mat_pivot.reset_index().to_excel(writer, index=False, sheet_name='原材料消耗_按种类')
                st.download_button("导出Excel(按种类)", out_mat_type.getvalue(), file_name=f"原材料消耗_按种类_{gran}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.info("暂无数据")
        with col2:
            st.caption("生产产出 (吨)")
            if not prod_agg.empty:
                st.bar_chart(prod_agg.set_index("period"))
                prod_exp = prod_agg.rename(columns={"period": "周期", "quantity": "数量(吨)"})
                csv_prod = prod_exp.to_csv(index=False, encoding="utf-8-sig")
                st.download_button("导出CSV", csv_prod, file_name=f"生产产出_{gran}.csv", mime="text/csv")
                out_prod = io.BytesIO()
                try:
                    with pd.ExcelWriter(out_prod, engine='xlsxwriter') as writer:
                        prod_exp.to_excel(writer, index=False, sheet_name='生产产出')
                        wb = writer.book
                        ws = writer.sheets['生产产出']
                        fmt = wb.add_format({'bold': True})
                        for i, col in enumerate(prod_exp.columns):
                            ws.write(0, i, col, fmt)
                except:
                    with pd.ExcelWriter(out_prod) as writer:
                        prod_exp.to_excel(writer, index=False, sheet_name='生产产出')
                st.download_button("导出Excel", out_prod.getvalue(), file_name=f"生产产出_{gran}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.info("暂无数据")
        with col3:
            st.caption("发货出库 (吨)")
            if not ship_agg.empty:
                st.bar_chart(ship_agg.set_index("period"))
                ship_exp = ship_agg.rename(columns={"period": "周期", "quantity": "数量(吨)"})
                csv_shipagg = ship_exp.to_csv(index=False, encoding="utf-8-sig")
                st.download_button("导出CSV", csv_shipagg, file_name=f"发货出库_{gran}.csv", mime="text/csv")
                out_shipagg = io.BytesIO()
                try:
                    with pd.ExcelWriter(out_shipagg, engine='xlsxwriter') as writer:
                        ship_exp.to_excel(writer, index=False, sheet_name='发货出库')
                        wb = writer.book
                        ws = writer.sheets['发货出库']
                        fmt = wb.add_format({'bold': True})
                        for i, col in enumerate(ship_exp.columns):
                            ws.write(0, i, col, fmt)
                except:
                    with pd.ExcelWriter(out_shipagg) as writer:
                        ship_exp.to_excel(writer, index=False, sheet_name='发货出库')
                st.download_button("导出Excel", out_shipagg.getvalue(), file_name=f"发货出库_{gran}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.info("暂无数据")
        total_mat = float(mat_agg["quantity"].sum()) if not mat_agg.empty else 0.0
        total_prod = float(prod_agg["quantity"].sum()) if not prod_agg.empty else 0.0
        total_ship = float(ship_agg["quantity"].sum()) if not ship_agg.empty else 0.0
        st.markdown(f"**摘要**：原料 {total_mat:.4f} kg | 生产 {total_prod:.4f} 吨 | 发货 {total_ship:.4f} 吨")
        if not mat_agg.empty and not prod_agg.empty and not ship_agg.empty:
            all_out = io.BytesIO()
            try:
                with pd.ExcelWriter(all_out, engine='xlsxwriter') as writer:
                    mat_exp.to_excel(writer, index=False, sheet_name=f'原材料消耗_{gran}')
                    try:
                        mat_pivot.reset_index().to_excel(writer, index=False, sheet_name=f'原材料消耗_按种类_{gran}')
                    except:
                        pass
                    prod_exp.to_excel(writer, index=False, sheet_name=f'生产产出_{gran}')
                    ship_exp.to_excel(writer, index=False, sheet_name=f'发货出库_{gran}')
                    pd.DataFrame([{"指标": "原料(kg)", "总量": f"{total_mat:.4f}"},
                                  {"指标": "生产(吨)", "总量": f"{total_prod:.4f}"},
                                  {"指标": "发货(吨)", "总量": f"{total_ship:.4f}"}]).to_excel(writer, index=False, sheet_name='摘要')
            except:
                with pd.ExcelWriter(all_out) as writer:
                    mat_exp.to_excel(writer, index=False, sheet_name=f'原材料消耗_{gran}')
                    try:
                        mat_pivot.reset_index().to_excel(writer, index=False, sheet_name=f'原材料消耗_按种类_{gran}')
                    except:
                        pass
                    prod_exp.to_excel(writer, index=False, sheet_name=f'生产产出_{gran}')
                    ship_exp.to_excel(writer, index=False, sheet_name=f'发货出库_{gran}')
                    pd.DataFrame([{"指标": "原料(kg)", "总量": f"{total_mat:.4f}"},
                                  {"指标": "生产(吨)", "总量": f"{total_prod:.4f}"},
                                  {"指标": "发货(吨)", "总量": f"{total_ship:.4f}"}]).to_excel(writer, index=False, sheet_name='摘要')
            st.download_button("导出整合Excel", all_out.getvalue(), file_name=f"综合统计_{gran}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
def _render_bom_tree_recursive(data_manager, bom_id, level=0, visited=None):
    """递归渲染 BOM 结构树"""
    if visited is None: visited = set()
    
    # 防止无限递归
    if bom_id in visited:
        st.markdown(f"{'&nbsp;' * 4 * level} 🔄 (循环引用: ID {bom_id})", unsafe_allow_html=True)
        return
    visited.add(bom_id)
    
    # 获取 BOM 信息
    boms = data_manager.get_all_boms()
    bom = next((b for b in boms if b['id'] == bom_id), None)
    if not bom: return
    
    # 获取最新版本
    versions = data_manager.get_bom_versions(bom_id)
    if not versions:
        st.markdown(f"{'&nbsp;' * 4 * level} 📦 **{bom['bom_name']}** (无版本)", unsafe_allow_html=True)
        return
        
    latest_ver = versions[-1]
    
    # 渲染节点
    indent = "&nbsp;" * 4 * level
    icon = "🏭" if level == 0 else "🔧"
    st.markdown(f"{indent} {icon} **{bom['bom_name']}** ({bom['bom_code']}) <span style='color:grey; font-size:0.8em'>V{latest_ver['version']}</span>", unsafe_allow_html=True)
    
    # 渲染子节点
    for line in latest_ver.get("lines", []):
        item_name = line.get('item_name', 'Unknown')
        qty = line.get('qty', 0)
        uom = line.get('uom', 'kg')
        item_type = line.get('item_type', 'raw_material')
        subs = line.get('substitutes', '')
        
        child_indent = "&nbsp;" * 4 * (level + 1)
        
        note = ""
        if subs: note = f" <span style='color:orange; font-size:0.8em'>(替: {subs})</span>"
        
        if item_type == "product":
            # 递归调用
            # 先打印行本身
            st.markdown(f"{child_indent} 📦 {item_name}: {qty} {uom}{note}", unsafe_allow_html=True)
            # 递归
            _render_bom_tree_recursive(data_manager, line.get('item_id'), level + 1, visited.copy())
        else:
            # 叶子节点 (原材料)
            st.markdown(f"{child_indent} 🧪 {item_name}: {qty} {uom}{note}", unsafe_allow_html=True)
