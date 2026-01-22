import streamlit as st
from datetime import datetime
import pandas as pd
import uuid
import io
import graphviz
from utils.unit_helper import convert_quantity, normalize_unit
from components.access_manager import check_page_permission, has_permission
from components.material_selector import render_material_cascade_selector

def _render_step_progress(current_status):
    """渲染生产订单步骤进度条"""
    steps = ["draft", "released", "issued", "finished"]
    step_labels = ["📝 草稿", "🚀 下达", "📦 领料", "🏁 完工"]
    
    # 获取当前索引
    try:
        current_idx = steps.index(current_status)
    except ValueError:
        current_idx = -1

    # 使用进度条和文字模拟
    cols = st.columns(len(steps))
    for i, label in enumerate(step_labels):
        with cols[i]:
            if i < current_idx:
                st.success(label)
            elif i == current_idx:
                st.info(f"**{label}**")
            else:
                st.write(f"<span style='color:gray'>{label}</span>", unsafe_allow_html=True)
    
    # 简单的进度条
    progress = (current_idx + 1) / len(steps)
    st.progress(progress)

def _render_bom_tree_graphviz(bom_tree):
    """使用 Graphviz 渲染 BOM 树"""
    dot = graphviz.Digraph(comment='BOM Tree')
    # 改为 TB (Top-to-Bottom) 布局，使节点水平排列，减少垂直空间占用
    dot.attr(rankdir='TB', nodesep='0.3', ranksep='0.5')
    dot.attr('node', shape='box', style='rounded,filled', 
             fontname='Microsoft YaHei', fontsize='9', 
             margin='0.1,0.05', height='0.3')
    dot.attr('edge', color='#666666', arrowhead='vee', arrowsize='0.7')

    def add_nodes(node, parent_id=None):
        if not node: return
        
        node_id = str(uuid.uuid4())
        
        # 节点内容
        if "code" in node: # 根节点或子 BOM 节点
            label = f"{node.get('name')}\n({node.get('code', 'N/A')})"
            fillcolor = '#e1f5fe' # 浅蓝色
        else: # 物料行
            label = f"{node.get('item_name')}\n{node.get('qty')} {node.get('uom')}"
            fillcolor = '#f5f5f5' # 浅灰色
            if node.get('substitutes'):
                label += f"\n(🔄 {node.get('substitutes')})"
        
        dot.node(node_id, label, fillcolor=fillcolor)
        
        if parent_id:
            dot.edge(parent_id, node_id)
            
        # 递归处理
        if "children" in node:
            for child in node["children"]:
                add_nodes(child, node_id)
        if "sub_bom" in node:
            add_nodes(node["sub_bom"], node_id)

    add_nodes(bom_tree)
    st.graphviz_chart(dot)



def render_sap_bom(bom_service, inventory_service, data_manager):
    """渲染 SAP/BOM 管理页面"""
    
    # Services injected via arguments
        
    st.header("🏭 SAP/BOM 管理")
    
    tab1, tab2, tab3, tab4 = st.tabs(["🧬 BOM 管理", "🏭 生产管理", "🚚 发货管理", "📈 台账报表"])
    
    with tab1:
        _render_bom_management(data_manager, inventory_service, bom_service)
    
    with tab2:
        _render_production_management(data_manager, bom_service, inventory_service)

    with tab3:
        _render_shipping_management(data_manager, inventory_service)
        
    with tab4:
        _render_inventory_reports(data_manager, bom_service)

def _render_bom_management(data_manager, inventory_service, bom_service):
    st.subheader("BOM 主数据管理")
    
    user = st.session_state.get("user")
    if not has_permission(user, "manage_bom"):
        st.info("仅管理员可以维护 BOM 主数据。")
        return
    
    boms = data_manager.get_all_boms()
    all_versions = data_manager.get_all_bom_versions()
    
    # 待审核提醒 (Card 风格)
    pending_versions = [v for v in all_versions if v.get("status") == "pending"]
    if pending_versions:
        with st.container(border=True):
            st.markdown("⚠️ **待审核 BOM 版本**")
            bom_map = {b.get("id"): b for b in boms}
            for v in pending_versions:
                bom = bom_map.get(v.get("bom_id"))
                bom_label = f"{bom.get('bom_code')}-{bom.get('bom_name')}" if bom else "Unknown"
                col_p1, col_p2, col_p3 = st.columns([4, 1, 1])
                with col_p1:
                    st.caption(f"{bom_label} | 版本 {v.get('version')} | 生效 {v.get('effective_from')} | 提交人 {v.get('created_by')}")
                with col_p2:
                    if st.button("批准", key=f"pending_approve_{v.get('id')}", type="primary", use_container_width=True):
                        data_manager.update_bom_version(v.get("id"), {
                            "status": "approved",
                            "approved_by": user.get("username") if user else None,
                            "approved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "locked": True
                        })
                        st.rerun()
                with col_p3:
                    if st.button("驳回", key=f"pending_reject_{v.get('id')}", use_container_width=True):
                        data_manager.update_bom_version(v.get("id"), {
                            "status": "rejected",
                            "rejected_by": user.get("username") if user else None,
                            "rejected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        st.rerun()

    if "bom_active_id" not in st.session_state:
        st.session_state.bom_active_id = None
    if "bom_edit_mode" not in st.session_state:
        st.session_state.bom_edit_mode = False
        
    col_list, col_detail = st.columns([1, 2])
    
    with col_list:
        st.markdown("#### BOM 列表")
        if st.button("➕ 新建 BOM", use_container_width=True, type="primary"):
            st.session_state.bom_active_id = "new"
            st.session_state.bom_edit_mode = True
            st.rerun()
            
        if not boms:
            st.info("暂无 BOM 数据")
        else:
            # 转换为 DataFrame 用于展示
            bom_df = pd.DataFrame([
                {"id": b["id"], "编号": b.get("bom_code"), "名称": b.get("bom_name"), "类型": b.get("bom_type")}
                for b in boms
            ])
            
            # 搜索过滤
            search_term = st.text_input("🔍 搜索", placeholder="输入编号、名称或 ID...").strip().lower()
            if search_term:
                # 增强搜索以包含 ID
                bom_df = bom_df[
                    bom_df["编号"].str.lower().str.contains(search_term, na=False) | 
                    bom_df["名称"].str.lower().str.contains(search_term, na=False) |
                    bom_df["id"].astype(str).str.contains(search_term, na=False)
                ]

            event = st.dataframe(
                bom_df,
                hide_index=True,
                use_container_width=True,
                on_select="rerun",
                selection_mode="single-row",
                column_config={"id": None} # 隐藏 ID 列
            )
            
            # 处理选择逻辑
            if event and event.selection and event.selection.rows:
                selected_idx = event.selection.rows[0]
                selected_id = bom_df.iloc[selected_idx]["id"]
                if selected_id != st.session_state.bom_active_id:
                    st.session_state.bom_active_id = selected_id
                    st.session_state.bom_edit_mode = False
                    st.rerun()

    with col_detail:
        if st.session_state.bom_active_id == "new":
            with st.container(border=True):
                _render_bom_form(data_manager, None)
        elif st.session_state.bom_active_id:
            bom_id = st.session_state.bom_active_id
            bom = next((b for b in boms if b.get('id') == bom_id), None)
            
            with st.container(border=True):
                if st.session_state.get("bom_edit_mode", False):
                     if bom:
                        _render_bom_form(data_manager, bom)
                     else:
                         st.info("BOM 未找到")
                elif bom:
                    _render_bom_detail(data_manager, inventory_service, bom, bom_service)
                else:
                    st.info("请在左侧选择 BOM")
        else:
            st.info("👈 请从左侧列表中选择一个 BOM 查看详情")

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

def _render_bom_detail(data_manager, inventory_service, bom, bom_service):
    user = st.session_state.get("user")
    
    # Header with status and type
    col_title, col_ops = st.columns([3, 1])
    with col_title:
        st.markdown(f"### {bom.get('bom_code')} - {bom.get('bom_name')}")
        mode = bom.get('production_mode', '自产')
        mode_text = f"{mode}"
        if mode == "代工":
            mode_text += f" ({bom.get('oem_manufacturer', '-')})"
        st.caption(f"类型: {bom.get('bom_type')} | 状态: {bom.get('status')} | 模式: {mode_text}")
    
    with col_ops:
        if st.button("✏️ 编辑", use_container_width=True):
             st.session_state.bom_edit_mode = True
             st.rerun()
        if st.button("🗑️ 删除", type="primary", use_container_width=True):
            st.session_state[f"confirm_del_bom_{bom['id']}"] = True
            
    if st.session_state.get(f"confirm_del_bom_{bom['id']}", False):
        with st.container(border=True):
            st.warning("确定要删除该 BOM 及其所有版本吗？")
            pwd = st.text_input("管理员口令", type="password", key=f"del_bom_pwd_{bom['id']}")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ 确认", key=f"yes_del_{bom['id']}", use_container_width=True):
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
                if st.button("❌ 取消", key=f"no_del_{bom['id']}", use_container_width=True):
                     del st.session_state[f"confirm_del_bom_{bom['id']}"]
                     st.rerun()

    # Visual BOM Tree
    st.markdown("#### 🌳 BOM 结构可视化")
    bom_tree = bom_service.get_bom_tree_structure(bom['id'])
    if bom_tree:
        _render_bom_tree_graphviz(bom_tree)
    else:
        st.info("该 BOM 尚未配置有效版本或结构为空。")

    st.divider()
    st.markdown("#### 📄 版本管理")
    
    versions = data_manager.get_bom_versions(bom['id'])
    versions = sorted(versions, key=lambda v: int(v.get("id", 0)))

    if len(versions) >= 2:
        with st.expander("🔍 版本比对", expanded=False):
            ver_map = {f"{v.get('version')} (生效: {v.get('effective_from')})": v for v in versions}
            ver_labels = list(ver_map.keys())
            col_a, col_b = st.columns(2)
            with col_a:
                sel_a_label = st.selectbox("版本 A", ver_labels, key=f"bom_ver_cmp_a_{bom['id']}")
            with col_b:
                sel_b_label = st.selectbox("版本 B", ver_labels, index=min(1, len(ver_labels)-1), key=f"bom_ver_cmp_b_{bom['id']}")
            
            ver_a = ver_map.get(sel_a_label)
            ver_b = ver_map.get(sel_b_label)
            if ver_a and ver_b and ver_a.get("id") != ver_b.get("id"):
                diff_list = bom_service.get_bom_version_diff(ver_a, ver_b)
                if diff_list:
                    diff_df = pd.DataFrame([
                        {
                            "物料": d['item_name'], 
                            "类型": {"modified": "修改", "added": "新增", "deleted": "删除"}.get(d['type']),
                            "单位": d['uom'],
                            "详情": f"{d['old_qty']} -> {d['new_qty']}" if d['type'] == 'modified' else f"{d.get('qty', '-')}"
                        } for d in diff_list
                    ])
                    st.dataframe(diff_df, use_container_width=True, hide_index=True)
                else:
                    st.info("两个版本无差异")

    if st.button("➕ 新增版本", type="primary"):
        # 自动生成版本号逻辑
        existing_nums = []
        for v in versions:
            vcode = str(v.get("version", "")).strip()
            if vcode.upper().startswith("V"):
                try: existing_nums.append(int(vcode[1:]))
                except: pass
        next_num = max(existing_nums) + 1 if existing_nums else 1
        new_ver_num = f"V{next_num}"
        
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
        st.info("暂无版本数据")
    else:
        ver_tabs = st.tabs([f"{v.get('version')} ({v.get('status') or 'approved'})" for v in versions])
        for i, ver in enumerate(versions):
            with ver_tabs[i]:
                _render_version_editor(data_manager, inventory_service, ver)


def _build_bom_version_diff(version_a, version_b):
    lines_a = version_a.get("lines", []) or []
    lines_b = version_b.get("lines", []) or []
    merged = {}
    for line in lines_a:
        key = (line.get("item_type"), line.get("item_id"))
        if key not in merged:
            merged[key] = {}
        merged[key]["a"] = line
    for line in lines_b:
        key = (line.get("item_type"), line.get("item_id"))
        if key not in merged:
            merged[key] = {}
        merged[key]["b"] = line
    rows = []
    for key, value in merged.items():
        line_a = value.get("a")
        line_b = value.get("b")
        qty_a = float(line_a.get("qty", 0.0)) if line_a else 0.0
        qty_b = float(line_b.get("qty", 0.0)) if line_b else 0.0
        base_line = line_b or line_a or {}
        name = base_line.get("item_name", "")
        uom = base_line.get("uom", "")
        diff_qty = qty_b - qty_a
        pct = None
        if qty_a != 0:
            pct = diff_qty / qty_a * 100.0
        if line_a is None:
            change = "新增"
        elif line_b is None:
            change = "删除"
        elif abs(diff_qty) < 1e-6:
            change = "不变"
        elif diff_qty > 0:
            change = "用量增加"
        else:
            change = "用量减少"
        rows.append(
            {
                "物料名称": name,
                "物料ID": key[1],
                "单位": uom,
                "版本A用量": qty_a,
                "版本B用量": qty_b,
                "差异用量": diff_qty,
                "差异百分比": pct,
                "变更类型": change,
            }
        )
    if not rows:
        return pd.DataFrame([])
    df = pd.DataFrame(rows)
    df["版本A用量"] = df["版本A用量"].round(3)
    df["版本B用量"] = df["版本B用量"].round(3)
    df["差异用量"] = df["差异用量"].round(3)
    if "差异百分比" in df.columns:
        df["差异百分比"] = df["差异百分比"].apply(
            lambda v: "" if pd.isna(v) else f"{v:.1f}%"
        )
    df = df.sort_values(["变更类型", "物料名称"])
    return df


def _render_export_download(df, base_filename, key_prefix, csv_encoding="utf-8-sig"):
    fmt = st.radio(
        "导出格式",
        ["CSV", "Excel"],
        horizontal=True,
        key=f"{key_prefix}_fmt",
    )
    if fmt == "CSV":
        data = df.to_csv(index=False, encoding=csv_encoding)
        mime = "text/csv"
        file_name = f"{base_filename}.csv"
    else:
        out = io.BytesIO()
        try:
            with pd.ExcelWriter(out, engine="xlsxwriter") as writer:
                df.to_excel(writer, index=False, sheet_name=base_filename)
        except:
            with pd.ExcelWriter(out) as writer:
                df.to_excel(writer, index=False, sheet_name=base_filename)
        data = out.getvalue()
        mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        file_name = f"{base_filename}.xlsx"
    st.download_button(
        "导出",
        data,
        file_name=file_name,
        mime=mime,
        key=f"{key_prefix}_download",
    )

def _render_version_editor(data_manager, inventory_service, version):
    current_lines = version.get("lines", [])
    user = st.session_state.get("user")
    locked = bool(version.get("locked", False))
    auth_key = f"ver_edit_auth_{version['id']}"
    if auth_key not in st.session_state:
        st.session_state[auth_key] = False

    status = version.get("status") or "approved"
    st.caption(f"当前版本状态: {status}")
    if user and has_permission(user, "manage_bom"):
        col_status1, col_status2 = st.columns(2)
        with col_status1:
            if status != "approved":
                if st.button("✅ 批准为有效版本", key=f"approve_ver_{version['id']}"):
                    data_manager.update_bom_version(version["id"], {
                        "status": "approved",
                        "approved_by": user.get("username"),
                        "approved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "locked": True
                    })
                    st.success("已批准")
                    st.rerun()
        with col_status2:
            if status == "pending":
                if st.button("❌ 驳回", key=f"reject_ver_{version['id']}"):
                    data_manager.update_bom_version(version["id"], {
                        "status": "rejected",
                        "rejected_by": user.get("username"),
                        "rejected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                    st.warning("已驳回")
                    st.rerun()

    col1, col2, col3 = st.columns(3)
    with col1:
        eff_from = st.date_input("生效日期", 
                               value=pd.to_datetime(version.get("effective_from", datetime.now())).date(),
                               key=f"eff_from_{version['id']}")
    with col2:
        yield_base = st.number_input("基准产量 (kg)", value=float(version.get("yield_base", 1000.0)), key=f"yield_{version['id']}")
    with col3:
        if st.button("删除版本", key=f"del_ver_{version['id']}"):
            success, msg = data_manager.delete_bom_version(version["id"])
            if success:
                if user:
                    detail = f"删除 BOM 版本 {version.get('version')} (ID={version.get('id')})"
                    data_manager.add_audit_log(user, "BOM_VERSION_DELETED", detail)
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)
    
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
            if user:
                detail = f"更新 BOM 版本 {version.get('version')} 头信息 (ID={version.get('id')})"
                data_manager.add_audit_log(user, "BOM_VERSION_HEADER_UPDATED", detail)
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
                        if user:
                            detail = f"删除 BOM 版本 {version.get('version')} 中的物料行 {line.get('item_name')}"
                            data_manager.add_audit_log(user, "BOM_LINE_DELETED", detail)
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
            # 使用级联选择器组件 (包含原材料和成品)
            selected_id, selected_obj, item_type = render_material_cascade_selector(
                data_manager, 
                inventory_service=inventory_service, 
                key_prefix=f"bom_add_{version['id']}",
                include_products=True
            )
            
            with st.form(f"add_line_form_{version['id']}", clear_on_submit=True):
                lc1, lc2 = st.columns([1, 1])
                with lc1:
                    l_qty = st.number_input("数量", min_value=0.0, step=0.1)
                with lc2:
                    l_phase = st.text_input("阶段 (e.g. A料)", value="")
                
                l_subs = st.text_input("替代料说明 (可选)", placeholder="例如: 可用类似规格替代")
                
                submitted = st.form_submit_button("确认添加")
                if submitted:
                    if not selected_id:
                        st.error("请先选择物料")
                    elif l_qty <= 0:
                        st.error("数量必须大于 0")
                    else:
                        item_name = selected_obj.get('name') or selected_obj.get('product_name')
                        new_line = {
                            "item_type": item_type,
                            "item_id": selected_id,
                            "item_name": item_name,
                            "qty": l_qty,
                            "uom": "kg",
                            "phase": l_phase,
                            "remark": "",
                            "substitutes": l_subs
                        }
                        current_lines.append(new_line)
                        data_manager.update_bom_version(version['id'], {"lines": current_lines})
                        if user:
                            detail = f"为 BOM 版本 {version.get('version')} 添加物料 {item_name} 数量 {l_qty} kg"
                            data_manager.add_audit_log(user, "BOM_LINE_ADDED", detail)
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
                if user:
                    detail = f"保存并锁定 BOM 版本 {version.get('version')} (ID={version.get('id')})"
                    data_manager.add_audit_log(user, "BOM_VERSION_LOCKED", detail)
                st.rerun()
    else:
        st.success("版本已保存")

def _render_production_management(data_manager, bom_service, inventory_service):
    st.subheader("生产订单管理")
    
    user = st.session_state.get("user")
    if not user:
        st.info("请登录后查看生产订单。")
        return
    
    if "prod_view" not in st.session_state:
        st.session_state.prod_view = "list"
    if "active_order_id" not in st.session_state:
        st.session_state.active_order_id = None
        
    orders = data_manager.get_all_production_orders()
    
    # --- KPI 看板 ---
    if st.session_state.prod_view == "list":
        status_counts = {"draft": 0, "released": 0, "issued": 0, "finished": 0}
        for o in orders:
            st_code = o.get("status", "draft")
            if st_code in status_counts:
                status_counts[st_code] += 1
        
        with st.container(border=True):
            st.markdown("##### 📊 生产概览")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("草稿", status_counts["draft"])
            c2.metric("已下达", status_counts["released"])
            c3.metric("领料中", status_counts["issued"])
            c4.metric("已完工", status_counts["finished"])

    if st.session_state.prod_view == "list":
        col_btn, col_search = st.columns([1, 3])
        with col_btn:
            if st.button("➕ 创建生产单", type="primary", use_container_width=True):
                st.session_state.prod_view = "create"
                st.rerun()
        
        if not orders:
            st.info("暂无生产单")
        else:
            # 数据转换
            boms = data_manager.get_all_boms()
            bom_map = {b['id']: f"{b.get('bom_code')}-{b.get('bom_name')}" for b in boms}
            
            order_data = []
            for o in orders:
                order_data.append({
                    "id": o["id"],
                    "单号": o.get("order_code"),
                    "产品": bom_map.get(o.get("bom_id"), "Unknown"),
                    "计划产量": f"{o.get('plan_qty')} kg",
                    "状态": o.get("status"),
                    "日期": o.get("plan_date") or o.get("created_at", "")[:10]
                })
            
            df_orders = pd.DataFrame(order_data)
            
            # 列表展示 (带选择)
            st.markdown("#### 📋 订单列表")
            event = st.dataframe(
                df_orders,
                hide_index=True,
                use_container_width=True,
                on_select="rerun",
                selection_mode="single-row",
                column_config={
                    "id": None,
                    "状态": st.column_config.SelectboxColumn(
                        "状态",
                        options=["draft", "released", "issued", "finished"],
                        required=True,
                    )
                }
            )
            
            if event and event.selection and event.selection.rows:
                idx = event.selection.rows[0]
                st.session_state.active_order_id = df_orders.iloc[idx]["id"]
                st.session_state.prod_view = "detail"
                st.rerun()

            # 原材料预警 (简化版，放在看板下方)
            with st.expander("⚠️ 原材料预警与消耗分析"):
                _render_production_scarcity_analysis(data_manager, boms, bom_map)

    elif st.session_state.prod_view == "create":
        _render_production_create(data_manager)
            
    elif st.session_state.prod_view == "detail":
        _render_production_detail(data_manager, inventory_service)

def _render_production_scarcity_analysis(data_manager, boms, bom_map):
    """提取原有的预警逻辑到独立函数"""
    raw_materials = data_manager.get_all_raw_materials()
    mat_inv = {}
    for m in raw_materials:
        qty = float(m.get("stock_quantity", 0.0))
        unit = m.get("unit", "kg")
        base_qty, ok = convert_quantity(qty, unit, "kg")
        mat_inv[m["id"]] = base_qty if ok else qty

    plan_batch_kg = 10000.0
    target_types = ["母液", "速凝剂"]
    type_boms = [b for b in boms if b.get("bom_type") in target_types]

    def per_batch_require(v):
        base = float(v.get("yield_base", 1000.0) or 1000.0)
        if base <= 0: base = 1000.0
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
        v = data_manager.get_effective_bom_version(b["id"])
        if not v: continue
        req = per_batch_require(v)
        if not req: continue
        score = scarcity_score(req)
        batches = min([int((mat_inv.get(mid, 0.0)) // q) if q > 0 else 0 for mid, q in req.items()]) if req else 0
        candidates.append({
            "bom_id": b["id"], "bom_label": bom_map.get(b["id"]), "bom_type": b.get("bom_type"),
            "version_id": v["id"], "per_batch_require": req, "scarcity_score": score, "max_batches_possible": batches
        })

    by_type = {}
    for c in candidates:
        t = c["bom_type"]
        if t not in by_type or c["scarcity_score"] < by_type[t]["scarcity_score"]:
            by_type[t] = c

    if by_type:
        warn_rows = []
        target_mat_ids = set()
        for b in type_boms:
            v = data_manager.get_effective_bom_version(b["id"])
            if v:
                for line in v.get("lines", []):
                    if line.get("item_type") == "raw_material":
                        target_mat_ids.add(line.get("item_id"))

        for m in raw_materials:
            mid = m["id"]
            avail = mat_inv.get(mid, 0.0)
            need_30 = sum(sel["per_batch_require"].get(mid, 0.0) * 3 for sel in by_type.values())
            warn = avail < need_30 and need_30 > 0
            
            warn_rows.append({
                "物料": m["name"],
                "当前库存(吨)": round(convert_quantity(avail, "kg", "ton")[0], 2),
                "预警": "🔴 缺料" if warn else "🟢 正常",
                "核心物料": "是" if mid in target_mat_ids else "否"
            })
        
        df_warn = pd.DataFrame(warn_rows)
        st.dataframe(df_warn, use_container_width=True, hide_index=True)
        
        if st.button("🚀 一键生成生产计划 (10吨/单)", type="primary"):
            for t, sel in by_type.items():
                new_order = {
                    "order_code": f"PROD-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4]}",
                    "bom_id": sel["bom_id"], "bom_version_id": sel["version_id"],
                    "plan_qty": plan_batch_kg, "status": "draft", "production_mode": "自产"
                }
                data_manager.add_production_order(new_order)
            st.success("已生成推荐生产单")
            st.rerun()

def _render_production_create(data_manager):
    st.markdown("#### 🏭 新建生产订单")
    with st.container(border=True):
        boms = data_manager.get_all_boms()
        bom_opts = {f"{b.get('bom_code')}-{b['bom_name']} (ID: {b['id']})": b for b in boms}
        sel_bom_label = st.selectbox("选择产品 BOM", list(bom_opts.keys()))
        sel_bom = bom_opts[sel_bom_label]
        
        versions = data_manager.get_bom_versions(sel_bom["id"])
        ver_opts = {f"{v.get('version')} (生效: {v.get('effective_from')})": v for v in versions if v.get("status") == "approved"}
        
        if not ver_opts:
            st.error("该 BOM 没有已批准的版本，无法生产")
            if st.button("返回"):
                st.session_state.prod_view = "list"
                st.rerun()
            return

        sel_ver_label = st.selectbox("选择版本", list(ver_opts.keys()))
        sel_ver = ver_opts[sel_ver_label]
        
        with st.form("new_order_form"):
            plan_qty = st.number_input("计划产量 (kg)", min_value=100.0, step=100.0, value=1000.0)
            plan_date = st.date_input("计划日期", datetime.now())
            prod_mode = st.radio("生产模式", ["自产", "代工"], horizontal=True)
            oem_name = st.text_input("代工厂家", placeholder="若是代工请填写")
            
            if st.form_submit_button("确认创建", type="primary"):
                new_order = {
                    "order_code": f"PROD-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4]}",
                    "bom_id": sel_bom["id"],
                    "bom_version_id": sel_ver["id"],
                    "plan_qty": plan_qty,
                    "plan_date": plan_date.strftime("%Y-%m-%d"),
                    "status": "draft",
                    "production_mode": prod_mode,
                    "oem_manufacturer": oem_name if prod_mode == "代工" else ""
                }
                new_id = data_manager.add_production_order(new_order)
                if new_id:
                    st.session_state.active_order_id = new_id
                    st.session_state.prod_view = "detail"
                    st.rerun()
        
        if st.button("取消"):
            st.session_state.prod_view = "list"
            st.rerun()

def _render_production_detail(data_manager, inventory_service):
    order_id = st.session_state.active_order_id
    orders = data_manager.get_all_production_orders()
    order = next((o for o in orders if o.get('id') == order_id), None)
    
    if not order:
        st.error("订单未找到")
        if st.button("返回列表"):
            st.session_state.prod_view = "list"
            st.rerun()
        return

    # 顶部导航
    col_back, col_status = st.columns([1, 4])
    with col_back:
        if st.button("⬅️ 返回", use_container_width=True):
            st.session_state.prod_view = "list"
            st.rerun()
    
    # 步骤条
    with st.container(border=True):
        _render_step_progress(order.get("status", "draft"))

    # 详情卡片
    with st.container(border=True):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**订单编号**: `{order.get('order_code')}`")
            st.markdown(f"**计划产量**: `{order.get('plan_qty')} kg`")
        with c2:
            st.markdown(f"**生产模式**: `{order.get('production_mode', '自产')}`")
            st.markdown(f"**计划日期**: `{order.get('plan_date', '-')}`")
        
        # 操作按钮
        st.divider()
        _render_production_actions(data_manager, order, inventory_service)

def _render_production_actions(data_manager, order, inventory_service):
    """渲染生产订单的操作按钮和状态流转"""
    status = order.get("status")
    
    if status == 'draft':
        if st.button("🚀 下达生产 (Release)", type="primary", use_container_width=True):
            data_manager.update_production_order(order['id'], {"status": "released"})
            st.rerun()
            
    elif status == 'released':
        if st.button("📄 生成领料单", type="primary", use_container_width=True):
            issue_id = data_manager.create_issue_from_order(order['id'])
            if issue_id:
                data_manager.update_production_order(order['id'], {"status": "issued"})
                st.rerun()
                
    elif status == 'issued':
        issues = data_manager.get_material_issues(order['id'])
        all_posted = all(i.get('status') == 'posted' for i in issues) if issues else False
        
        if not all_posted:
            st.warning("请先完成所有领料单的过账")
            for iss in issues:
                if iss.get('status') == 'draft':
                    if st.button(f"✅ 领料过账: {iss.get('issue_code')}", key=f"post_{iss['id']}", use_container_width=True):
                        data_manager.post_issue(iss['id'])
                        st.rerun()
        else:
            if st.button("🏁 完工入库 (Finish)", type="primary", use_container_width=True):
                data_manager.finish_production_order(order['id'], operator="User")
                st.rerun()
    
    elif status == 'finished':
        st.success("🎉 该订单已完工入库")
                
    elif st.session_state.prod_view == "create":
        st.markdown("#### 新建生产单")
        
        boms = data_manager.get_all_boms()
        bom_opts = {}
        for b in boms:
            code = b.get('bom_code', '').strip()
            name = b['bom_name'].strip()
            base_label = f"{code}-{name}" if code else name
            label = f"{base_label} (ID: {b.get('id')})"
            bom_opts[label] = b
        sel_bom_label = st.selectbox("选择产品 BOM", list(bom_opts.keys()), key="new_order_bom_label")
        sel_bom = bom_opts[sel_bom_label]
        prod_date = st.date_input("生产日期", datetime.now(), key="new_order_prod_date")
        versions = data_manager.get_bom_versions(sel_bom["id"])
        versions = sorted(versions, key=lambda v: int(v.get("id", 0)))
        ver_map = {}
        ver_labels = []
        for v in versions:
            vcode = v.get("version", "")
            vdate = v.get("effective_from", "-")
            vstatus = v.get("status", "") or "approved"
            label = f"{vcode} (ID: {v.get('id')}) | 生效 {vdate} | {vstatus}"
            ver_map[label] = v
            ver_labels.append(label)
        selected_ver = None
        if ver_labels:
            display_labels = ["请选择版本"] + ver_labels
            sel_ver_label = st.selectbox("选择BOM版本", display_labels, key="new_order_bom_ver")
            if sel_ver_label != "请选择版本":
                selected_ver = ver_map.get(sel_ver_label)
        
        with st.form("new_order_form"):
            plan_qty = st.number_input("计划产量 (kg)", min_value=0.0, step=100.0, value=1000.0, key="new_order_plan_qty")
            prod_mode = st.radio("生产模式", ["自产", "代工"], horizontal=True, key="new_order_prod_mode")
            oem_name = st.text_input("代工厂家名称", placeholder="若是代工，请填写厂家名称", key="new_order_oem_name")
            submitted = st.form_submit_button("创建")
            if submitted:
                if prod_mode == "代工" and not oem_name.strip():
                    st.error("选择代工模式时，必须填写代工厂家名称")
                elif not ver_labels:
                    st.error("该 BOM 没有可用版本，无法创建")
                elif not selected_ver:
                    st.error("请选择 BOM 版本")
                else:
                    new_order = {
                        "order_code": f"PROD-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4]}",
                        "bom_id": sel_bom["id"],
                        "bom_version_id": selected_ver["id"],
                        "plan_qty": plan_qty,
                        "plan_date": prod_date.strftime("%Y-%m-%d"),
                        "status": "draft",
                        "production_mode": prod_mode,
                        "oem_manufacturer": oem_name if prod_mode == "代工" else ""
                    }
                    new_id = data_manager.add_production_order(new_order)
                    user = st.session_state.get("user")
                    if user and new_id:
                        detail = f"创建生产单 #{new_id}，BOM {sel_bom_label}，版本 {selected_ver.get('version')}，计划产量 {plan_qty} kg，模式 {prod_mode}"
                        data_manager.add_audit_log(user, "PROD_ORDER_CREATED", detail)
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
                        user = st.session_state.get("user")
                        if user:
                            detail = f"删除生产单 #{order.get('id')}，单号 {order.get('order_code')}"
                            data_manager.add_audit_log(user, "PROD_ORDER_DELETED", detail)
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
            
            mode = order.get('production_mode', '自产') # 默认为自产兼容旧数据
            mode_text = f"模式: {mode}"
            if mode == "代工":
                mode_text += f" | 厂家: {order.get('oem_manufacturer', '-')}"
            plan_date = order.get("plan_date") or ""
            if plan_date:
                mode_text += f" | 生产日期: {plan_date}"
            st.caption(f"状态: {order.get('status')} | 计划产量: {order.get('plan_qty')} kg | {mode_text}")
            
            # 编辑计划产量 (仅限 Draft 状态)
            if order.get('status') == 'draft':
                 new_qty = st.number_input("修改计划产量 (kg)", value=float(order.get('plan_qty')), min_value=0.0, step=100.0)
                 if new_qty != float(order.get('plan_qty')):
                     if st.button("保存产量修改"):
                         old_qty = float(order.get('plan_qty'))
                         data_manager.update_production_order(order['id'], {"plan_qty": new_qty})
                         st.success("已更新")
                         user = st.session_state.get("user")
                         if user:
                             detail = f"修改生产单 #{order.get('id')} 计划产量: {old_qty} -> {new_qty} kg"
                             data_manager.add_audit_log(user, "PROD_ORDER_PLAN_QTY_UPDATED", detail)
                         st.rerun()

            # 状态流转
            if order.get('status') == 'draft':
                if st.button("🚀 下达生产 (Released)"):
                    data_manager.update_production_order(order['id'], {"status": "released"})
                    user = st.session_state.get("user")
                    if user:
                        detail = f"将生产单 #{order.get('id')} 状态从 draft 变更为 released"
                        data_manager.add_audit_log(user, "PROD_ORDER_STATUS_UPDATED", detail)
                    st.rerun()
            
            if order.get('status') == 'released':
                st.info("生产已下达，请生成领料单")
                if st.button("📄 生成领料单"):
                    issue_id = data_manager.create_issue_from_order(order['id'])
                    if issue_id:
                        st.success("领料单已生成")
                        data_manager.update_production_order(order['id'], {"status": "issued"})
                        user = st.session_state.get("user")
                        if user:
                            detail = f"为生产单 #{order.get('id')} 生成领料单 #{issue_id}，生产单状态更新为 issued"
                            data_manager.add_audit_log(user, "ISSUE_CREATED_FROM_ORDER", detail)
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
                                user = st.session_state.get("user")
                                operator_name = user.get("username") if user else "User"
                                success, msg = data_manager.post_issue(issue['id'], operator=operator_name)
                                if success:
                                    st.success(msg)
                                    if user:
                                        detail = f"对领料单 #{issue.get('id')} ({issue.get('issue_code')}) 执行过账"
                                        data_manager.add_audit_log(user, "ISSUE_POSTED", detail)
                                    st.rerun()
                                else:
                                    st.error(msg)
                        
                        elif issue.get('status') == 'posted':
                            st.success(f"已过账于 {issue.get('posted_at')}")
                            # 撤销过账按钮
                            if st.button("↩️ 撤销过账 (Cancel)", key=f"cancel_{issue['id']}"):
                                user = st.session_state.get("current_user")
                                operator_name = user.get("username") if user else "User"
                                success, msg = inventory_service.cancel_issue_posting(issue['id'], operator=operator_name)
                                if success:
                                    st.warning(msg)
                                    if user:
                                        detail = f"对领料单 #{issue.get('id')} ({issue.get('issue_code')}) 撤销过账"
                                        data_manager.add_audit_log(user, "ISSUE_CANCELLED", detail)
                                    st.rerun()
                                else:
                                    st.error(msg)
            
            if order.get('status') == 'issued':
                st.divider()
                if st.button("🏁 完工入库 (Finish)"):
                     success, msg = data_manager.finish_production_order(order['id'], operator="User")
                     if success:
                         st.success(msg)
                         user = st.session_state.get("current_user")
                         if user:
                             detail = f"完成生产单 #{order.get('id')} 入库"
                             data_manager.add_audit_log(user, "PROD_ORDER_FINISHED", detail)
                         st.rerun()
                     else:
                         st.error(msg)
            
            st.divider()
            st.markdown("#### 生产追溯链")
            boms = data_manager.get_all_boms()
            bom_map = {b.get("id"): b for b in boms}
            bom = bom_map.get(order.get("bom_id"))
            bom_label = ""
            if bom:
                code = str(bom.get("bom_code", "") or "").strip()
                name = str(bom.get("bom_name", "") or "").strip()
                bom_label = f"{code}-{name}" if code else name
            all_versions = data_manager.get_all_bom_versions()
            ver_map = {v.get("id"): v for v in all_versions}
            ver = ver_map.get(order.get("bom_version_id"))
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                st.write(f"BOM: {bom_label or '-'}")
            with col_t2:
                if ver:
                    st.write(f"版本: {ver.get('version')} | 生效 {ver.get('effective_from', '-')}")
                else:
                    st.write("版本: -")
            
            # 使用 Service 展示追溯信息（此处暂保持原有逻辑，因为涉及多表联合查询，若要迁移需在 BOMService 中新增 get_traceability_info）
            # 这里的逻辑主要是数据展示，耦合度尚可接受，暂不强制迁移
            
            issues = data_manager.get_material_issues(order['id'])
            if issues:
                st.markdown("##### 关联单据")
                issue_rows = []
                for iss in issues:
                    issue_rows.append({
                        "领料单号": iss.get("issue_code", ""),
                        "状态": iss.get("status", ""),
                        "创建时间": iss.get("created_at", ""),
                        "过账时间": iss.get("posted_at", "")
                    })
                df_issue = pd.DataFrame(issue_rows)
                st.dataframe(df_issue, use_container_width=True, hide_index=True)
            records = data_manager.get_inventory_records()
            if issues and records:
                issue_ids = [i.get("id") for i in issues]
                mats = data_manager.get_all_raw_materials()
                mat_map = {m.get("id"): m.get("name") for m in mats}
                agg = {}
                for r in records:
                    if r.get("related_doc_type") not in ["ISSUE", "ISSUE_CANCEL"]:
                        continue
                    if r.get("related_doc_id") not in issue_ids:
                        continue
                    mid = r.get("material_id")
                    if not mid:
                        continue
                    key = mid
                    if key not in agg:
                        agg[key] = {"consume": 0.0, "return": 0.0, "unit": r.get("unit", "kg")}
                    q = float(r.get("quantity", 0.0))
                    if r.get("type") == "consume_out":
                        agg[key]["consume"] += q
                    elif r.get("type") == "return_in":
                        agg[key]["return"] += q
                if agg:
                    st.markdown("##### 原材料消耗与退回")
                    rows = []
                    for mid, v in agg.items():
                        name = mat_map.get(mid, f"ID-{mid}")
                        net = v["consume"] - v["return"]
                        rows.append({
                            "物料": name,
                            "领用数量": round(v["consume"], 4),
                            "退回数量": round(v["return"], 4),
                            "净消耗": round(net, 4),
                            "单位": v["unit"]
                        })
                    df_mat = pd.DataFrame(rows)
                    st.dataframe(df_mat, use_container_width=True, hide_index=True)
            prod_records = data_manager.get_product_inventory_records()
            if prod_records:
                oc = order.get("order_code")
                finish_rows = []
                for r in prod_records:
                    reason = str(r.get("reason", "") or "")
                    batch = r.get("batch_number", "")
                    if f"生产完工: {oc}" in reason or batch == oc:
                        finish_rows.append({
                            "日期": r.get("date", ""),
                            "产品名称": r.get("product_name", ""),
                            "类型": r.get("product_type", ""),
                            "数量": r.get("quantity", 0),
                            "结存": r.get("snapshot_stock", 0)
                        })
                if finish_rows:
                    st.markdown("##### 成品入库记录")
                    df_fin = pd.DataFrame(finish_rows)
                    st.dataframe(df_fin, use_container_width=True, hide_index=True)

def _render_shipping_management(data_manager, inventory_service):
    st.subheader("发货管理")
    
    # 1. 发货操作区域
    st.markdown("#### 📦 新增发货单")
    
    # 获取成品库存列表
    inventory = inventory_service.get_products()
    if not inventory:
        st.warning("暂无成品库存，无法进行发货操作。请先进行生产入库。")
    else:
        with st.form("shipping_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                # 构造选项: "名称 (ID: id) (类型) - 库存: 100 吨"
                prod_options = {
                    f"{p.get('product_name') or p.get('name', 'Unknown')} (ID: {p.get('id')}) ({p.get('type', '-')}) - 库存: {float(p.get('stock_quantity', 0) or p.get('current_stock', 0))/1000.0:.2f} 吨": p 
                    for p in inventory
                }
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
                    current_stock_kg = float(selected_prod.get('stock_quantity', 0) or selected_prod.get('current_stock', 0))
                    current_stock_tons = current_stock_kg / 1000.0
                    
                    if ship_qty > current_stock_tons:
                        st.error(f"库存不足！当前库存: {current_stock_tons:.2f} 吨")
                    else:
                        user = st.session_state.get("user")
                        operator_name = user.get("username") if user else "User"
                        
                        # 使用 inventory_service.process_shipping 处理单位转换 (吨 -> kg)
                        success, msg = inventory_service.process_shipping(
                            product_name=selected_prod.get('product_name', 'Unknown'),
                            product_type=selected_prod.get('type', '其他'),
                            quantity_tons=ship_qty,
                            customer=customer,
                            remark=remark,
                            operator=operator_name,
                            date_str=ship_date.strftime("%Y-%m-%d")
                        )
                        
                        if success:
                            st.success(f"发货成功！已扣减库存 {ship_qty} 吨")
                            if user:
                                detail = f"发货 {selected_prod['product_name']}，数量 {ship_qty} 吨，客户 {customer}"
                                data_manager.add_audit_log(user, "SHIPPING_CREATED", detail)
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
        
        # 筛选功能
        with st.expander("🔍 筛选记录", expanded=False):
            f_col1, f_col2 = st.columns(2)
            with f_col1:
                # 提取所有产品名称供筛选
                unique_products = sorted(list(set(df_ship['product_name'].dropna().unique())))
                filter_prod = st.multiselect("筛选产品名称", unique_products, key="ship_filter_prod")
            with f_col2:
                filter_remark = st.text_input("搜索备注 (包含关键词)", key="ship_filter_remark")
        
        # 应用筛选
        if filter_prod:
            df_ship = df_ship[df_ship['product_name'].isin(filter_prod)]
        if filter_remark:
            df_ship = df_ship[df_ship['reason'].astype(str).str.contains(filter_remark, case=False, na=False)]
        
        # 选取展示列
        cols = ["date", "product_name", "product_type", "quantity", "reason", "operator", "snapshot_stock"]
        # 确保列存在
        display_cols = [c for c in cols if c in df_ship.columns]
        
        df_display = df_ship[display_cols].copy()
        
        # 修正显示单位：数据库存的是 kg，显示为 吨
        if "quantity" in df_display.columns:
            df_display["quantity"] = df_display["quantity"] / 1000.0
        if "snapshot_stock" in df_display.columns:
            df_display["snapshot_stock"] = df_display["snapshot_stock"] / 1000.0
            
        df_display.columns = [c.replace("date", "日期").replace("product_name", "产品名称")
                              .replace("product_type", "类型").replace("quantity", "数量(吨)")
                              .replace("reason", "详情/备注").replace("operator", "操作人")
                              .replace("snapshot_stock", "发货后结存(吨)") for c in df_display.columns]
        
        st.dataframe(df_display, use_container_width=True, hide_index=True)
        
def _render_inventory_reports(data_manager, bom_service):
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
            _render_export_download(df_bal, "库存余额", "stock_balance_export")
        else:
            st.info("暂无库存数据")
            
    with tab_ledger:
        records = data_manager.get_inventory_records()
        if records:
            # 补充物料名称 (解决 KeyError: 'material_name')
            materials = data_manager.get_all_raw_materials()
            mat_map = {m['id']: f"{m['name']} (ID: {m['id']})" for m in materials}
            
            enriched_records = []
            for r in records:
                r_copy = r.copy()
                # 强制使用带 ID 的名称以防重名歧义
                mid = r_copy.get("material_id")
                r_copy["material_name"] = mat_map.get(mid, f"Unknown (ID: {mid})")
                enriched_records.append(r_copy)
                
            df = pd.DataFrame(enriched_records)
            
            # 1. 增加筛选器
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                # 使用带 ID 的物料名称供筛选
                unique_materials = sorted(list(set(df['material_name'].dropna().unique())))
                sel_mat = st.multiselect("筛选物料 (支持按名称筛选)", unique_materials)
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
                hide_index=True,
            )
            _render_export_download(df_display, "台账流水", "ledger_export")
        else:
            st.info("暂无台账记录")

    with tab_prodcons:
        prod_records = data_manager.get_product_inventory_records()
        cons_records = [
            r
            for r in prod_records
            if r.get("type") == "out"
            and r.get("related_doc_type") != "SHIPPING"
            and r.get("related_doc_type") != "ISSUE_CANCEL"
        ]
        if cons_records:
            inventory = data_manager.get_product_inventory()
            prod_unit_map = {}
            for p in inventory:
                key = (p.get("name"), p.get("type"))
                prod_unit_map[key] = p.get("unit", "吨")
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
                pname = r.get("product_name", "")
                ptype = r.get("product_type", "")
                unit = prod_unit_map.get((pname, ptype), "吨")
                qty_raw = float(r.get("quantity", 0) or 0)
                qty_ton, ok_ton = convert_quantity(qty_raw, unit, "ton")
                qty_kg, ok_kg = convert_quantity(qty_raw, unit, "kg")
                display_ton = qty_ton if ok_ton else qty_raw
                display_kg = qty_kg if ok_kg else qty_raw
                display_rows.append({
                    "日期": r.get("date", ""),
                    "产品名称": pname,
                    "类型": ptype,
                    "数量(吨)": display_ton,
                    "数量(kg)": display_kg,
                    "来源类型": src_type,
                    "关联单据号": doc_no,
                    "来源/备注": reason,
                    "操作人": r.get("operator", ""),
                    "发出后结存(吨)": round(float(r.get("snapshot_stock", 0) or 0) / 1000.0, 4)
                })
            df_cons = pd.DataFrame(display_rows)
            st.dataframe(df_cons, use_container_width=True)
            _render_export_download(df_cons, "成品消耗", "product_consume_export")
        else:
            st.info("暂无成品消耗记录")

    with tab_stats:
        gran = st.selectbox("统计周期", ["周", "月", "年度"], index=1)
        enabled = st.checkbox("启用综合统计分析", value=False, key="inventory_stats_enabled")
        if not enabled:
            st.info("开启上方开关后，将加载原材料消耗、生产产出和发货出库的统计图表。")
        else:
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
                    _render_export_download(mat_exp, f"原材料消耗_{gran}", f"mat_stats_export_{gran}")
                    materials = data_manager.get_all_raw_materials()
                    mat_map = {m['id']: m['name'] for m in materials}
                    df_m_cons["_name"] = df_m_cons["material_id"].map(mat_map)
                    if "unit" in df_m_cons.columns:
                        df_m_cons["qty_kg"] = df_m_cons.apply(
                            lambda x: convert_quantity(
                                float(x["quantity"]), x["unit"], "kg"
                            )[0]
                            if pd.notna(x["unit"])
                            else float(x["quantity"]),
                            axis=1,
                        )
                    else:
                        df_m_cons["qty_kg"] = df_m_cons["quantity"].astype(float)
                    mat_by_type = (
                        df_m_cons.groupby(["period", "_name"])["qty_kg"]
                        .sum()
                        .reset_index()
                        .rename(columns={"_name": "原材料名称"})
                    )
                    mat_pivot = mat_by_type.pivot(
                        index="原材料名称", columns="period", values="qty_kg"
                    ).fillna(0.0)
                    mat_pivot_reset = mat_pivot.reset_index()
                    st.dataframe(mat_pivot_reset, use_container_width=True)
                    _render_export_download(
                        mat_pivot_reset,
                        f"原材料消耗_按种类_{gran}",
                        f"mat_type_stats_export_{gran}",
                    )
                else:
                    st.info("暂无数据")
            with col2:
                st.caption("生产产出 (吨)")
                if not prod_agg.empty:
                    st.bar_chart(prod_agg.set_index("period"))
                    prod_exp = prod_agg.rename(columns={"period": "周期", "quantity": "数量(吨)"})
                    _render_export_download(prod_exp, f"生产产出_{gran}", f"prod_stats_export_{gran}")
                else:
                    st.info("暂无数据")
            with col3:
                st.caption("发货出库 (吨)")
                if not ship_agg.empty:
                    st.bar_chart(ship_agg.set_index("period"))
                    ship_exp = ship_agg.rename(columns={"period": "周期", "quantity": "数量(吨)"})
                    _render_export_download(ship_exp, f"发货出库_{gran}", f"ship_stats_export_{gran}")
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
# 移除 _render_bom_tree_recursive，已迁移至 BOMService 并重构为 _render_bom_tree_from_struct

def _render_bom_tree_from_struct(node):
    if not node:
        return

    # Determine indentation
    level = node.get("level", 0)
    indent_space = "&nbsp;" * (level * 4)
    
    # Check if it is a BOM definition (Root) or a Line Item
    if "code" in node:
        # It is a BOM structure root
        name = node.get("name", "")
        code = node.get("code", "")
        ver = node.get("version", "")
        if node.get("is_loop"):
            st.markdown(f"{indent_space}⚠️ **{name}** ({code}) - <span style='color:red'>循环引用</span>", unsafe_allow_html=True)
            return
            
        header = f"📦 **{name}**"
        if code:
            header += f" ({code})"
        if ver:
            header += f" <span style='color:gray; font-size:0.9em'>ver: {ver}</span>"
        else:
            header += f" <span style='color:orange; font-size:0.9em'>(无生效版本)</span>"
            
        st.markdown(f"{indent_space}{header}", unsafe_allow_html=True)
        
        # Render children lines
        if "children" in node:
            for child in node["children"]:
                _render_bom_tree_from_struct(child)
                
    else:
        # It is a Line Item
        name = node.get("item_name", "Unknown")
        qty = node.get("qty", 0)
        uom = node.get("uom", "kg")
        subs = node.get("substitutes", "")
        
        info = f"{qty} {uom}"
        if subs:
            info += f" | 🔄 替代: {subs}"
            
        st.markdown(f"{indent_space}🔹 {name} <span style='color:gray'>: {info}</span>", unsafe_allow_html=True)
        
        # Check for sub-BOM (recursive structure)
        if "sub_bom" in node:
             _render_bom_tree_from_struct(node["sub_bom"])

