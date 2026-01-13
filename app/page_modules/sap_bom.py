import streamlit as st
from datetime import datetime
import pandas as pd
import uuid

def render_sap_bom(data_manager):
    """娓叉煋 SAP/BOM 绠＄悊椤甸潰"""
    st.header("馃彮 SAP/BOM 绠＄悊")
    
    tab1, tab2, tab3 = st.tabs(["馃К BOM 绠＄悊", "馃彮 鐢熶骇绠＄悊", "馃搱 鍙拌处鎶ヨ〃"])
    
    with tab1:
        _render_bom_management(data_manager)
    
    with tab2:
        _render_production_management(data_manager)
        
    with tab3:
        _render_inventory_reports(data_manager)

def _render_bom_management(data_manager):
    st.subheader("BOM 涓绘暟鎹鐞?)
    
    if "bom_active_id" not in st.session_state:
        st.session_state.bom_active_id = None
    if "bom_edit_mode" not in st.session_state:
        st.session_state.bom_edit_mode = False
        
    # 宸︿晶鍒楄〃锛屽彸渚ц鎯?
    col_list, col_detail = st.columns([1, 2])
    
    boms = data_manager.get_all_boms()
    
    with col_list:
        st.markdown("#### BOM 鍒楄〃")
        # 鎼滅储妗?
        search_term = st.text_input("馃攳 鎼滅储 BOM", placeholder="缂栧彿/鍚嶇О").strip().lower()
        
        if st.button("鉃?鏂板缓 BOM", use_container_width=True):
            st.session_state.bom_active_id = "new"
            st.session_state.bom_edit_mode = True
            st.rerun()
            
        if not boms:
            st.info("鏆傛棤 BOM 鏁版嵁")
        else:
            # 杩囨护
            filtered_boms = boms
            if search_term:
                filtered_boms = [b for b in boms if search_term in b.get('bom_code', '').lower() or search_term in b.get('bom_name', '').lower()]
            
            for bom in filtered_boms:
                label = f"{bom.get('bom_code')} - {bom.get('bom_name')}"
                btn_type = "primary" if str(bom.get('id')) == str(st.session_state.bom_active_id) else "secondary"
                
                # 浣跨敤鍒楀竷灞€鏀剧疆鍒犻櫎鎸夐挳 (浠呭湪鎮仠鎴栭€変腑鏃舵樉绀烘瘮杈冨鏉傦紝杩欓噷绠€鍖栦负姣忚涓€涓垹闄ゅ皬鎸夐挳涓嶅お濂界湅锛?
                # 寤鸿鍦ㄨ鎯呴〉鍋氬垹闄わ紝杩欓噷鍙仛鍒楄〃閫夋嫨)
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
            
            # 鍒ゆ柇鏄惁澶勪簬缂栬緫妯″紡 (淇敼鐜版湁 BOM)
            if st.session_state.get("bom_edit_mode", False):
                 if bom:
                    _render_bom_form(data_manager, bom)
                 else:
                     st.info("BOM 鏈壘鍒?)
            elif bom:
                _render_bom_detail(data_manager, bom)
            else:
                st.info("BOM 鏈壘鍒?(鍙兘宸插垹闄?")
                if st.button("杩斿洖鍒楄〃"):
                    st.session_state.bom_active_id = None
                    st.rerun()
        else:
            st.info("璇烽€夋嫨宸︿晶 BOM 鏌ョ湅璇︽儏")

def _render_bom_form(data_manager, bom=None):
    st.markdown("#### 缂栬緫 BOM 鍩烘湰淇℃伅")
    with st.form("bom_base_form"):
        code = st.text_input("BOM 缂栧彿", value=bom.get("bom_code", "") if bom else "")
        name = st.text_input("BOM 鍚嶇О", value=bom.get("bom_name", "") if bom else "")
        
        # 瀹氫箟绫诲瀷閫夐」鍜屾槧灏?
        type_options = ["姣嶆恫", "鎴愬搧", "閫熷嚌鍓?, "闃插喕鍓?]
        current_type = bom.get("bom_type", "姣嶆恫") if bom else "姣嶆恫"
        
        # 鍏煎鏃ф暟鎹?(濡傛灉鏃ф暟鎹槸鑻辨枃锛岃浆涓轰腑鏂囨樉绀猴紝淇濆瓨鏃跺瓨涓枃)
        if current_type == "mother_liquor": current_type = "姣嶆恫"
        elif current_type == "product": current_type = "鎴愬搧"
        
        # 纭繚 current_type 鍦ㄩ€夐」涓紝闃叉绱㈠紩閿欒
        try:
            type_index = type_options.index(current_type)
        except ValueError:
            type_index = 0
            
        bom_type = st.selectbox("BOM 绫诲瀷", type_options, index=type_index)
        
        # 鐢熶骇妯″紡
        current_mode = bom.get("production_mode", "鑷骇") if bom else "鑷骇"
        mode_options = ["鑷骇", "浠ｅ伐"]
        try:
            mode_index = mode_options.index(current_mode)
        except ValueError:
            mode_index = 0
            
        prod_mode = st.radio("鐢熶骇妯″紡", mode_options, index=mode_index, horizontal=True)
        
        current_oem = bom.get("oem_manufacturer", "") if bom else ""
        oem_name = st.text_input("浠ｅ伐鍘傚鍚嶇О", value=current_oem, placeholder="鑻ユ槸浠ｅ伐锛岃濉啓鍘傚鍚嶇О")
        
        submitted = st.form_submit_button("淇濆瓨")
        if submitted:
            if not code or not name:
                st.error("缂栧彿鍜屽悕绉板繀濉?)
            elif prod_mode == "浠ｅ伐" and not oem_name.strip():
                st.error("閫夋嫨浠ｅ伐妯″紡鏃讹紝蹇呴』濉啓浠ｅ伐鍘傚鍚嶇О")
            else:
                data = {
                    "bom_code": code,
                    "bom_name": name,
                    "bom_type": bom_type,
                    "status": "active", # 榛樿婵€娲?
                    "production_mode": prod_mode,
                    "oem_manufacturer": oem_name if prod_mode == "浠ｅ伐" else ""
                }
                if bom:
                    if data_manager.update_bom(bom['id'], data):
                        st.success("鏇存柊鎴愬姛")
                        st.session_state.bom_edit_mode = False
                        st.rerun()
                else:
                    new_id = data_manager.add_bom(data)
                    if new_id:
                        st.success("鍒涘缓鎴愬姛")
                        st.session_state.bom_active_id = new_id
                        st.session_state.bom_edit_mode = False
                        st.rerun()
    
    if bom:
         if st.button("鍙栨秷缂栬緫"):
             st.session_state.bom_edit_mode = False
             st.rerun()

def _render_bom_detail(data_manager, bom):
    # 鏍囬鏍忥細鏄剧ず淇℃伅 + 鎿嶄綔鎸夐挳
    col_title, col_ops = st.columns([3, 1])
    with col_title:
        st.markdown(f"### {bom.get('bom_code')} - {bom.get('bom_name')}")
        
        mode = bom.get('production_mode', '鑷骇')
        mode_text = f"{mode}"
        if mode == "浠ｅ伐":
            mode_text += f" ({bom.get('oem_manufacturer', '-')})"
            
        st.caption(f"绫诲瀷: {bom.get('bom_type')} | 鐘舵€? {bom.get('status')} | 妯″紡: {mode_text}")
    
    with col_ops:
        if st.button("馃棏锔?鍒犻櫎 BOM", type="primary"):
            # 纭鍒犻櫎閫昏緫 (绠€鍗曡捣瑙佺洿鎺ュ垹锛屾垨鑰呭脊绐楃‘璁?
            # Streamlit 鍘熺敓娌℃湁寮圭獥锛屽彲浠ョ敤 session_state 鍋氫簩娆＄‘璁?
            st.session_state[f"confirm_del_bom_{bom['id']}"] = True
        
        if st.session_state.get(f"confirm_del_bom_{bom['id']}", False):
            st.warning("纭畾瑕佸垹闄ゅ悧锛熻繖灏嗗垹闄ゆ墍鏈夌増鏈€?)
            c1, c2 = st.columns(2)
            with c1:
                if st.button("鉁?纭", key=f"yes_del_{bom['id']}"):
                    if data_manager.delete_bom(bom['id']):
                        st.success("宸插垹闄?)
                        st.session_state.bom_active_id = None
                        del st.session_state[f"confirm_del_bom_{bom['id']}"]
                        st.rerun()
            with c2:
                if st.button("鉂?鍙栨秷", key=f"no_del_{bom['id']}"):
                     del st.session_state[f"confirm_del_bom_{bom['id']}"]
                     st.rerun()
                     
    if st.button("鉁忥笍 缂栬緫鍩烘湰淇℃伅"):
         st.session_state.bom_edit_mode = True
         st.rerun()

    # 缁撴瀯鏍戝彲瑙嗗寲
    with st.expander("馃尦 鏌ョ湅澶氱骇 BOM 缁撴瀯鏍?):
        _render_bom_tree_recursive(data_manager, bom['id'])

    # 鐗堟湰绠＄悊
    st.divider()
    st.markdown("#### 鐗堟湰绠＄悊")
    
    versions = data_manager.get_bom_versions(bom['id'])
    
    # 鏂板鐗堟湰鎸夐挳
    if st.button("鉃?鏂板鐗堟湰"):
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
        st.info("鏆傛棤鐗堟湰锛岃鐐瑰嚮鏂板")
    else:
        # 鐗堟湰Tabs
        ver_tabs = st.tabs([v.get('version', 'V?') for v in versions])
        
        # 鍑嗗鍘熸潗鏂欓€夐」
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
        eff_from = st.date_input("鐢熸晥鏃ユ湡", 
                               value=pd.to_datetime(version.get("effective_from", datetime.now())).date(),
                               key=f"eff_from_{version['id']}")
    with col2:
        yield_base = st.number_input("鍩哄噯浜ч噺 (kg)", value=float(version.get("yield_base", 1000.0)), key=f"yield_{version['id']}")
    
    # 瀹炴椂鏄剧ず鎬婚噺鏍￠獙
    total_qty_display = sum(float(line.get('qty', 0)) for line in current_lines)
    diff = total_qty_display - yield_base
    
    c_m1, c_m2, c_m3 = st.columns(3)
    c_m1.metric("褰撳墠鐗╂枡鎬婚噺", f"{total_qty_display:.3f} kg")
    c_m2.metric("璁惧畾鍩哄噯浜ч噺", f"{yield_base:.3f} kg")
    c_m3.metric("宸紓", f"{diff:.3f} kg", delta_color="normal" if abs(diff) < 1e-6 else "inverse")

    if st.button("鏇存柊鐗堟湰澶翠俊鎭?, key=f"save_head_{version['id']}"):
        if locked and not st.session_state[auth_key]:
            with st.form(key=f"pwd_head_{version['id']}"):
                pwd = st.text_input("绠＄悊鍛樺瘑鐮?, type="password")
                submitted = st.form_submit_button("寮€濮嬩慨鏀?)
                if submitted and pwd == "admin":
                    st.session_state[auth_key] = True
                    st.success("宸查獙璇?)
                    st.rerun()
                elif submitted:
                    st.error("瀵嗙爜閿欒")
        else:
            data_manager.update_bom_version(version['id'], {
                "effective_from": eff_from.strftime("%Y-%m-%d"),
                "yield_base": yield_base
            })
            st.success("宸蹭繚瀛?)
            st.rerun()
    
    st.markdown("##### BOM 鏄庣粏")
    
    # 浣跨敤 data_editor 缂栬緫鏄庣粏
    
    # 杞崲涓?DataFrame 鏂逛究缂栬緫
    # 缁撴瀯: item_id (dropdown), qty, uom, phase, remark
    
    # 涓轰簡璁?data_editor 鏀寔涓嬫媺锛屾垜浠渶瑕佹瀯閫犱竴涓寘鍚樉绀哄悕绉扮殑鍒?
    # 浣?data_editor 鐨?column_config.Selectbox 闇€瑕侀瀹氫箟鐨?options
    # 杩欓噷涓轰簡绠€鍖栵紝鎴戜滑鍏堢敤涓ゆ娉曪細娣诲姞琛屽尯鍩?+ 绠€鍗曡〃鏍煎睍绀?鍒犻櫎
    
    # 灞曠ず鐜版湁琛?
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
                    if st.button("馃棏锔?, key=f"del_line_{version['id']}_{idx}"):
                        del current_lines[idx]
                        data_manager.update_bom_version(version['id'], {"lines": current_lines})
                        st.rerun()
    
    st.divider()
    with st.expander("鉃?鍗曚釜娣诲姞 | 馃搨 鎵归噺瀵煎叆 (Excel)", expanded=False):
        if locked and not st.session_state[auth_key]:
            st.info("鐗堟湰宸蹭繚瀛橈紝淇敼闇€瑕佺鐞嗗憳瀵嗙爜")
            with st.form(key=f"pwd_edit_{version['id']}"):
                pwd = st.text_input("绠＄悊鍛樺瘑鐮?, type="password")
                submitted = st.form_submit_button("寮€濮嬩慨鏀?)
                if submitted and pwd == "admin":
                    st.session_state[auth_key] = True
                    st.success("宸查獙璇?)
                    st.rerun()
                elif submitted:
                    st.error("瀵嗙爜閿欒")
        else:
            # 鑾峰彇鍘熸潗鏂欏拰浜у搧(BOM)閫夐」
            raw_materials = data_manager.get_all_raw_materials()
            products = data_manager.get_all_boms()
            
            combined_options = {}
            for m in raw_materials:
                label = f"[鍘熸潗鏂橾 {m['name']} ({m.get('material_number', '-')})"
                combined_options[label] = f"raw_material:{m['id']}"
            for p in products:
                label = f"[浜у搧] {p['bom_name']} ({p.get('bom_code', '-')})"
                combined_options[label] = f"product:{p['id']}"

            with st.form(f"add_line_form_{version['id']}", clear_on_submit=True):
                lc1, lc2, lc3 = st.columns([3, 1, 1])
                with lc1:
                    sel_item_label = st.selectbox("閫夋嫨鐗╂枡 (鍘熸潗鏂?浜у搧)", list(combined_options.keys()))
                with lc2:
                    l_qty = st.number_input("鏁伴噺", min_value=0.0, step=0.1)
                with lc3:
                    l_phase = st.text_input("闃舵 (e.g. A鏂?", value="")
                
                # 鏂板鏇夸唬鏂欒鏄庤緭鍏?
                l_subs = st.text_input("鏇夸唬鏂欒鏄?(鍙€?", placeholder="渚嬪: 鍙敤绫讳技瑙勬牸鏇夸唬")
                
                submitted = st.form_submit_button("娣诲姞")
                if submitted:
                    type_id_str = combined_options[sel_item_label]
                    item_type, item_id = type_id_str.split(":")
                    
                    # 鎻愬彇鍚嶇О
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
                        "substitutes": l_subs # 淇濆瓨鏇夸唬鏂?
                    }
                    current_lines.append(new_line)
                    data_manager.update_bom_version(version['id'], {"lines": current_lines})
                    st.rerun()
    st.divider()
    if not locked:
        if st.button("淇濆瓨鐗堟湰", key=f"save_version_{version['id']}"):
            total_qty = sum(float(line.get('qty', 0)) for line in current_lines)
            if abs(total_qty - yield_base) > 1e-6:
                st.error(f"鐗╂枡鎬婚噺 {total_qty:.3f} kg 涓庡熀鍑嗕骇閲?{yield_base} kg 涓嶄竴鑷?)
                with st.form(key=f"pwd_force_save_{version['id']}"):
                    pwd = st.text_input("绠＄悊鍛樺瘑鐮?, type="password")
                    submitted = st.form_submit_button("寮哄埗淇濆瓨")
                    if submitted and pwd == "admin":
                        data_manager.update_bom_version(version['id'], {
                            "effective_from": eff_from.strftime("%Y-%m-%d"),
                            "yield_base": yield_base,
                            "lines": current_lines,
                            "locked": True
                        })
                        st.success("宸蹭繚瀛樺苟閿佸畾")
                        st.rerun()
                    elif submitted:
                        st.error("瀵嗙爜閿欒")
            else:
                data_manager.update_bom_version(version['id'], {
                    "effective_from": eff_from.strftime("%Y-%m-%d"),
                    "yield_base": yield_base,
                    "lines": current_lines,
                    "locked": True
                })
                st.success("宸蹭繚瀛樺苟閿佸畾")
                st.rerun()
    else:
        st.success("鐗堟湰宸蹭繚瀛?)

def _render_production_management(data_manager):
    st.subheader("鐢熶骇璁㈠崟绠＄悊")
    
    if "prod_view" not in st.session_state:
        st.session_state.prod_view = "list" # list, create, detail
    if "active_order_id" not in st.session_state:
        st.session_state.active_order_id = None
        
    if st.session_state.prod_view == "list":
        if st.button("鉃?鍒涘缓鐢熶骇鍗?):
            st.session_state.prod_view = "create"
            st.rerun()
            
        orders = data_manager.get_all_production_orders()
        
        # 鎼滅储杩囨护
        search_term = st.text_input("馃攳 鎼滅储鐢熶骇鍗?, placeholder="鍗曞彿").strip().lower()
        
        if not orders:
            st.info("鏆傛棤鐢熶骇鍗?)
        else:
            if search_term:
                orders = [o for o in orders if search_term in o.get('order_code', '').lower()]
            
            # 绠€鍗曡〃鏍?(鎸夊垱寤烘椂闂村€掑簭)
            orders.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            st.dataframe(
                pd.DataFrame(orders)[["id", "order_code", "status", "plan_qty", "created_at"]],
                use_container_width=True
            )
            
            # 閫夋嫨鎿嶄綔
            c_sel, c_btn = st.columns([3, 1])
            with c_sel:
                selected_oid = st.selectbox("閫夋嫨鐢熶骇鍗曟煡鐪嬭鎯?, [o['id'] for o in orders], format_func=lambda x: f"Order #{x} - {next((o['order_code'] for o in orders if o['id']==x), '')}")
            with c_btn:
                if st.button("鏌ョ湅璇︽儏"):
                    st.session_state.active_order_id = selected_oid
                    st.session_state.prod_view = "detail"
                    st.rerun()
                
    elif st.session_state.prod_view == "create":
        st.markdown("#### 鏂板缓鐢熶骇鍗?)
        
        # 浣跨敤 key 鏉ヤ繚鐣欑姸鎬侊紝浣?form 浼氬湪鎻愪氦鍚庢竻绌猴紝鎵€浠ユ垜浠敤 session_state 
        if "new_prod_mode" not in st.session_state: st.session_state.new_prod_mode = "鑷骇"
        
        # 鐢熶骇妯″紡閫夋嫨锛堟斁鍦?form 澶栭潰鎴栬€呬綔涓?form 鐨勪竴閮ㄥ垎锛?
        # 杩欓噷涓轰簡浜や簰娴佺晠锛堥€夋嫨浠ｅ伐鍚庢樉绀哄巶瀹惰緭鍏ユ锛夛紝寤鸿鎶婃ā寮忛€夋嫨鏀惧湪 form 澶栭潰锛屾垨鑰呬娇鐢?st.radio
        
        with st.form("new_order_form"):
            # 閫夋嫨 BOM
            boms = data_manager.get_all_boms()
            bom_opts = {f"{b['bom_code']} {b['bom_name']}": b for b in boms}
            sel_bom_label = st.selectbox("閫夋嫨浜у搧 BOM", list(bom_opts.keys()))
            
            plan_qty = st.number_input("璁″垝浜ч噺", min_value=0.0, step=100.0, value=1000.0)
            
            # 鐢熶骇妯″紡
            prod_mode = st.radio("鐢熶骇妯″紡", ["鑷骇", "浠ｅ伐"], horizontal=True)
            oem_name = st.text_input("浠ｅ伐鍘傚鍚嶇О", placeholder="鑻ユ槸浠ｅ伐锛岃濉啓鍘傚鍚嶇О")
            
            if st.form_submit_button("鍒涘缓"):
                # 鏍￠獙
                if prod_mode == "浠ｅ伐" and not oem_name.strip():
                    st.error("閫夋嫨浠ｅ伐妯″紡鏃讹紝蹇呴』濉啓浠ｅ伐鍘傚鍚嶇О")
                else:
                    sel_bom = bom_opts[sel_bom_label]
                    # 鑾峰彇鏈€鏂扮増鏈?
                    vers = data_manager.get_bom_versions(sel_bom['id'])
                    if not vers:
                        st.error("璇?BOM 娌℃湁鐗堟湰锛屾棤娉曞垱寤?)
                    else:
                        # 榛樿閫夋渶鍚庝竴涓増鏈?
                        target_ver = vers[-1]
                        
                        new_order = {
                            "order_code": f"PROD-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4]}",
                            "bom_id": sel_bom['id'],
                            "bom_version_id": target_ver['id'],
                            "plan_qty": plan_qty,
                            "status": "draft",
                            "production_mode": prod_mode,
                            "oem_manufacturer": oem_name if prod_mode == "浠ｅ伐" else ""
                        }
                        new_id = data_manager.add_production_order(new_order)
                        st.success(f"鍒涘缓鎴愬姛 #{new_id}")
                        st.session_state.active_order_id = new_id
                        st.session_state.prod_view = "detail"
                        st.rerun()
        
        if st.button("鍙栨秷"):
            st.session_state.prod_view = "list"
            st.rerun()
            
    elif st.session_state.prod_view == "detail":
        col_back, col_del = st.columns([6, 1])
        with col_back:
            if st.button("猬咃笍 杩斿洖鍒楄〃"):
                st.session_state.prod_view = "list"
                st.rerun()
        
        orders = data_manager.get_all_production_orders()
        order = next((o for o in orders if o.get('id') == st.session_state.active_order_id), None)
        
        if not order:
            st.error("璁㈠崟鏈壘鍒?)
        else:
            # 鍒犻櫎鎸夐挳閫昏緫
            with col_del:
                if st.button("馃棏锔?鍒犻櫎", key="del_prod_btn"):
                     st.session_state.confirm_del_prod = True
            
            if st.session_state.get("confirm_del_prod", False):
                st.warning("纭畾鍒犻櫎璇ョ敓浜у崟锛?)
                if st.button("鉁?纭鍒犻櫎"):
                    success, msg = data_manager.delete_production_order(order['id'])
                    if success:
                        st.success(msg)
                        st.session_state.prod_view = "list"
                        st.session_state.active_order_id = None
                        del st.session_state.confirm_del_prod
                        st.rerun()
                    else:
                        st.error(msg)
                if st.button("鉂?鍙栨秷"):
                    del st.session_state.confirm_del_prod
                    st.rerun()

            st.markdown(f"### 鐢熶骇鍗? {order.get('order_code')}")
            
            # 鏄剧ず鐢熶骇妯″紡鍜屼唬宸ュ巶
            mode = order.get('production_mode', '鑷骇') # 榛樿涓鸿嚜浜у吋瀹规棫鏁版嵁
            mode_text = f"妯″紡: {mode}"
            if mode == "浠ｅ伐":
                mode_text += f" | 鍘傚: {order.get('oem_manufacturer', '-')}"
            
            st.caption(f"鐘舵€? {order.get('status')} | 璁″垝浜ч噺: {order.get('plan_qty')} | {mode_text}")
            
            # 缂栬緫璁″垝浜ч噺 (浠呴檺 Draft 鐘舵€?
            if order.get('status') == 'draft':
                 new_qty = st.number_input("淇敼璁″垝浜ч噺", value=float(order.get('plan_qty')), min_value=0.0, step=100.0)
                 if new_qty != float(order.get('plan_qty')):
                     if st.button("淇濆瓨浜ч噺淇敼"):
                         data_manager.update_production_order(order['id'], {"plan_qty": new_qty})
                         st.success("宸叉洿鏂?)
                         st.rerun()

            # 鐘舵€佹祦杞?
            if order.get('status') == 'draft':
                if st.button("馃殌 涓嬭揪鐢熶骇 (Released)"):
                    data_manager.update_production_order(order['id'], {"status": "released"})
                    st.rerun()
            
            if order.get('status') == 'released':
                st.info("鐢熶骇宸蹭笅杈撅紝璇风敓鎴愰鏂欏崟")
                if st.button("馃搫 鐢熸垚棰嗘枡鍗?):
                    issue_id = data_manager.create_issue_from_order(order['id'])
                    if issue_id:
                        st.success("棰嗘枡鍗曞凡鐢熸垚")
                        data_manager.update_production_order(order['id'], {"status": "issued"})
                        st.rerun()
                        
            # 鍏宠仈棰嗘枡鍗?
            issues = data_manager.get_material_issues(order['id'])
            if issues:
                st.markdown("#### 鍏宠仈棰嗘枡鍗?)
                for issue in issues:
                    with st.expander(f"{issue.get('issue_code')} ({issue.get('status')})", expanded=True):
                        # 鏄剧ず鏄庣粏
                        lines = issue.get('lines', [])
                        if lines:
                            df_lines = pd.DataFrame(lines)
                            # 纭繚鎵€闇€鐨勫垪瀛樺湪
                            required_cols = ['item_name', 'required_qty', 'uom']
                            display_cols = [col for col in required_cols if col in df_lines.columns]
                            
                            if display_cols:
                                st.table(df_lines[display_cols])
                            else:
                                st.table(df_lines) # 鏄剧ず鎵€鏈夊垪浣滀负鍚庡
                        else:
                            st.info("鏃犻鏂欐槑缁?)
                        
                        if issue.get('status') == 'draft':
                            if st.button("鉁?纭棰嗘枡杩囪处 (Post)", key=f"post_{issue['id']}"):
                                success, msg = data_manager.post_issue(issue['id'], operator="User")
                                if success:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
                        
                        elif issue.get('status') == 'posted':
                            st.success(f"宸茶繃璐︿簬 {issue.get('posted_at')}")
                            # 鎾ら攢杩囪处鎸夐挳
                            if st.button("鈫╋笍 鎾ら攢杩囪处 (Cancel)", key=f"cancel_{issue['id']}"):
                                success, msg = data_manager.cancel_issue_posting(issue['id'], operator="User")
                                if success:
                                    st.warning(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
            
            # 瀹屽伐鍏ュ簱 (绠€鍖?
            if order.get('status') == 'issued': # 宸查鏂?
                st.divider()
                if st.button("馃弫 瀹屽伐鍏ュ簱 (Finish)"):
                     data_manager.update_production_order(order['id'], {"status": "finished"})
                     st.success("璁㈠崟宸插畬宸?)
                     st.rerun()

def _render_inventory_reports(data_manager):
    st.subheader("搴撳瓨鍙拌处鎶ヨ〃")
    
    tab_bal, tab_ledger = st.tabs(["馃挵 搴撳瓨浣欓", "馃摑 鍙拌处娴佹按"])
    
    with tab_bal:
        # 淇敼閫昏緫锛氫笉鍐嶄娇鐢?get_stock_balance (绾祦姘磋绠?锛?
        # 鑰屾槸鐩存帴璇诲彇鍘熸潗鏂欎富鏁版嵁鐨勫綋鍓嶅簱瀛?(stock_quantity)锛屽洜涓哄畠鍖呭惈浜嗗垵濮嬪簱瀛樺拰鎵€鏈夊彉鍔ㄣ€?
        # 杩欐牱鑳戒繚璇佹暟鎹殑涓€鑷存€с€?
        
        materials = data_manager.get_all_raw_materials()
        
        report_data = []
        for mat in materials:
            # 1. 鑾峰彇褰撳墠搴撳瓨 (鍩虹鍗曚綅)
            stock_qty = float(mat.get('stock_quantity', 0.0))
            base_unit = mat.get('unit', 'kg')
            
            # 2. 鍗曚綅杞崲 (杞负鍚?
            # 閫昏緫锛?
            # - 濡傛灉鍩虹鍗曚綅鏄?kg/g/lb 绛夎川閲忓崟浣?-> 杞负 ton
            # - 濡傛灉鍩虹鍗曚綅鏄?L/mL 绛変綋绉崟浣?-> 淇濇寔鍘熸牱鎴栬浆涓?m3 (杩欓噷鏆備繚鎸佸師鏍?
            # - 濡傛灉宸茬粡鏄?ton -> 淇濇寔鍘熸牱
            
            from utils.unit_helper import convert_quantity, normalize_unit
            
            # 灏濊瘯杞崲鍒板惃
            display_qty, success = convert_quantity(stock_qty, base_unit, 'ton')
            
            if success:
                display_unit = "鍚?
            else:
                # 杞崲澶辫触 (闈炶川閲忓崟浣?锛屼繚鎸佸師鍊?
                display_qty = stock_qty
                display_unit = base_unit
            
            report_data.append({
                "鐗╂枡鍚嶇О": mat['name'],
                "鐗╂枡鍙?: mat.get('material_number'),
                "褰撳墠搴撳瓨 (鍚?": f"{display_qty:.4f}" if success else f"{display_qty:.4f} ({display_unit})",
                "鍘熷搴撳瓨": f"{stock_qty:.4f}",
                "鍘熷鍗曚綅": base_unit
            })
        
        if report_data:
            st.dataframe(pd.DataFrame(report_data), use_container_width=True)
        else:
            st.info("鏆傛棤搴撳瓨鏁版嵁")
            
    with tab_ledger:
        records = data_manager.get_inventory_records()
        if records:
            df = pd.DataFrame(records)
            # 绠€鍗曠殑鍒楅噸鍛藉悕
            st.dataframe(df.sort_values("created_at", ascending=False), use_container_width=True)
        else:
            st.info("鏆傛棤鍙拌处璁板綍")

def _render_bom_tree_recursive(data_manager, bom_id, level=0, visited=None):
    """閫掑綊娓叉煋 BOM 缁撴瀯鏍?""
    if visited is None: visited = set()
    
    # 闃叉鏃犻檺閫掑綊
    if bom_id in visited:
        st.markdown(f"{'&nbsp;' * 4 * level} 馃攧 (寰幆寮曠敤: ID {bom_id})", unsafe_allow_html=True)
        return
    visited.add(bom_id)
    
    # 鑾峰彇 BOM 淇℃伅
    boms = data_manager.get_all_boms()
    bom = next((b for b in boms if b['id'] == bom_id), None)
    if not bom: return
    
    # 鑾峰彇鏈€鏂扮増鏈?    versions = data_manager.get_bom_versions(bom_id)
    if not versions:
        st.markdown(f"{'&nbsp;' * 4 * level} 馃摝 **{bom['bom_name']}** (鏃犵増鏈?", unsafe_allow_html=True)
        return
        
    latest_ver = versions[-1]
    
    # 娓叉煋鑺傜偣
    indent = "&nbsp;" * 4 * level
    icon = "馃彮" if level == 0 else "馃敡"
    st.markdown(f"{indent} {icon} **{bom['bom_name']}** ({bom['bom_code']}) <span style='color:grey; font-size:0.8em'>V{latest_ver['version']}</span>", unsafe_allow_html=True)
    
    # 娓叉煋瀛愯妭鐐?    for line in latest_ver.get("lines", []):
        item_name = line.get('item_name', 'Unknown')
        qty = line.get('qty', 0)
        uom = line.get('uom', 'kg')
        item_type = line.get('item_type', 'raw_material')
        subs = line.get('substitutes', '')
        
        child_indent = "&nbsp;" * 4 * (level + 1)
        
        note = ""
        if subs: note = f" <span style='color:orange; font-size:0.8em'>(鏇? {subs})</span>"
        
        if item_type == "product":
            # 閫掑綊璋冪敤
            # 鍏堟墦鍗拌鏈韩
            st.markdown(f"{child_indent} 馃摝 {item_name}: {qty} {uom}{note}", unsafe_allow_html=True)
            # 閫掑綊
            _render_bom_tree_recursive(data_manager, line.get('item_id'), level + 1, visited.copy())
        else:
            # 鍙跺瓙鑺傜偣 (鍘熸潗鏂?
            st.markdown(f"{child_indent} 馃И {item_name}: {qty} {uom}{note}", unsafe_allow_html=True)
