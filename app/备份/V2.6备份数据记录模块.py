# -------------------- 数据记录页面 --------------------
def render_data_recording():
    """渲染数据记录页面 - 重构版"""
    st.header("📝 数据记录")
    
    # 使用标签页组织不同模块
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🧪 合成实验", 
        "📦 原材料管理", 
        "📊 成品减水剂",
        "🧫 净浆实验", 
        "🏗️ 砂浆实验", 
        "🏢 混凝土实验"
    ])
    
    # ==================== 原材料管理模块 ====================
    with tab2:
        st.subheader("📦 原材料管理")
        
        # 初始化原材料数据
        if "raw_materials" not in st.session_state:
            st.session_state.raw_materials = []
        
        # 添加新原材料表单
        with st.expander("➕ 添加新原材料", expanded=True):
            with st.form("add_raw_material_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    material_name = st.text_input("原材料名称*", key="material_name")
                    chemical_formula = st.text_input("化学式", key="chemical_formula")
                    molecular_weight = st.number_input("分子量 (g/mol)", 
                                                      min_value=0.0, 
                                                      step=0.01,
                                                      key="molecular_weight")
                    solid_content = st.number_input("固含 (%)", 
                                                   min_value=0.0, 
                                                   max_value=100.0,
                                                   step=0.1,
                                                   key="solid_content")
                with col2:
                    unit_price = st.number_input("单价 (元/吨)", 
                                                min_value=0.0,
                                                step=0.1,
                                                key="unit_price")
                    odor = st.selectbox("气味", 
                                       ["无", "轻微", "中等", "强烈", "刺激性"],
                                       key="odor")
                    storage_condition = st.text_input("存储条件", key="storage_condition")
                    supplier = st.text_input("供应商", key="supplier")
                
                main_usage = st.text_area("主要用途描述*", height=100, key="main_usage")
                
                submitted = st.form_submit_button("添加原材料", type="primary")
                if submitted:
                    if material_name and main_usage:
                        # 检查是否重复
                        existing_names = [m.get("name") for m in st.session_state.raw_materials]
                        if material_name in existing_names:
                            st.error(f"原材料 '{material_name}' 已存在！")
                        else:
                            new_material = {
                                "id": len(st.session_state.raw_materials) + 1,
                                "name": material_name,
                                "chemical_formula": chemical_formula,
                                "molecular_weight": molecular_weight,
                                "solid_content": solid_content,
                                "unit_price": unit_price,
                                "odor": odor,
                                "storage_condition": storage_condition,
                                "supplier": supplier,
                                "main_usage": main_usage,
                                "created_date": datetime.now().strftime("%Y-%m-%d")
                            }
                            st.session_state.raw_materials.append(new_material)
                            st.success(f"原材料 '{material_name}' 添加成功！")
                    else:
                        st.error("请填写带*的必填项")
        
        # 原材料列表
        st.divider()
        st.subheader("📋 原材料列表")
        
        if st.session_state.raw_materials:
            # 搜索功能
            search_col1, search_col2 = st.columns([3, 1])
            with search_col1:
                search_term = st.text_input("🔍 搜索原材料", 
                                           placeholder="输入名称或化学式搜索")
            with search_col2:
                items_per_page = st.selectbox("每页显示", [10, 20, 50], index=0)
            
            # 过滤数据
            filtered_materials = st.session_state.raw_materials
            if search_term:
                filtered_materials = [
                    m for m in filtered_materials
                    if search_term.lower() in m.get("name", "").lower() or 
                    search_term.lower() in m.get("chemical_formula", "").lower()
                ]
            
            # 分页
            if "material_page" not in st.session_state:
                st.session_state.material_page = 1
            
            total_pages = max(1, (len(filtered_materials) + items_per_page - 1) // items_per_page)
            start_idx = (st.session_state.material_page - 1) * items_per_page
            end_idx = min(start_idx + items_per_page, len(filtered_materials))
            current_materials = filtered_materials[start_idx:end_idx]
            
            # 显示表格
            if current_materials:
                # 创建紧凑表格
                for material in current_materials:
                    with st.container():
                        col1, col2, col3 = st.columns([2, 2, 1])
                        with col1:
                            st.markdown(f"**{material['name']}**")
                            if material['chemical_formula']:
                                st.caption(f"化学式: {material['chemical_formula']}")
                            st.caption(f"分子量: {material['molecular_weight']} g/mol")
                        with col2:
                            st.caption(f"固含: {material['solid_content']}%")
                            st.caption(f"单价: ¥{material['unit_price']}/吨")
                            st.caption(f"气味: {material['odor']}")
                        with col3:
                            st.caption(f"ID: {material['id']}")
                            if st.button("删除", key=f"del_material_{material['id']}"):
                                st.session_state.raw_materials = [
                                    m for m in st.session_state.raw_materials 
                                    if m['id'] != material['id']
                                ]
                                st.rerun()
                        st.markdown(f"**用途:** {material['main_usage']}")
                        st.divider()
                
                # 分页控制
                if total_pages > 1:
                    pag_col1, pag_col2, pag_col3 = st.columns([1, 2, 1])
                    with pag_col2:
                        col_prev, col_page, col_next = st.columns([1, 2, 1])
                        with col_prev:
                            if st.button("⬅️", key="mat_prev") and st.session_state.material_page > 1:
                                st.session_state.material_page -= 1
                                st.rerun()
                        with col_page:
                            page_num = st.number_input(
                                "页码", 
                                min_value=1, 
                                max_value=total_pages,
                                value=st.session_state.material_page,
                                key="mat_page_input",
                                label_visibility="collapsed"
                            )
                            if page_num != st.session_state.material_page:
                                st.session_state.material_page = page_num
                                st.rerun()
                        with col_next:
                            if st.button("➡️", key="mat_next") and st.session_state.material_page < total_pages:
                                st.session_state.material_page += 1
                                st.rerun()
        else:
            st.info("暂无原材料数据，请添加第一个原材料")
    
    # -------------------- 数据记录页面 --------------------
def render_data_recording():
    """渲染数据记录页面 - 重构版"""
    st.header("📝 数据记录")
    
    # 使用标签页组织不同模块
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🧪 合成实验", 
        "📦 原材料管理", 
        "📊 成品减水剂",
        "🧫 净浆实验", 
        "🏗️ 砂浆实验", 
        "🏢 混凝土实验"
    ])
    
    # ==================== 原材料管理模块 ====================
    with tab2:
        st.subheader("📦 原材料管理")
        
        # 初始化原材料数据
        if "raw_materials" not in st.session_state:
            st.session_state.raw_materials = []
        
        # 添加新原材料表单
        with st.expander("➕ 添加新原材料", expanded=True):
            with st.form("data_recording_raw_material_add_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    material_name = st.text_input("原材料名称*", key="data_raw_material_name")
                    chemical_formula = st.text_input("化学式", key="data_raw_chemical_formula")
                    molecular_weight = st.number_input("分子量 (g/mol)", 
                                                      min_value=0.0, 
                                                      step=0.01,
                                                      key="data_raw_molecular_weight")
                    solid_content = st.number_input("固含 (%)", 
                                                   min_value=0.0, 
                                                   max_value=100.0,
                                                   step=0.1,
                                                   key="data_raw_solid_content")
                with col2:
                    unit_price = st.number_input("单价 (元/吨)", 
                                                min_value=0.0,
                                                step=0.1,
                                                key="data_raw_unit_price")
                    odor = st.selectbox("气味", 
                                       ["无", "轻微", "中等", "强烈", "刺激性"],
                                       key="data_raw_odor")
                    storage_condition = st.text_input("存储条件", key="data_raw_storage_condition")
                    supplier = st.text_input("供应商", key="data_raw_supplier")
                
                main_usage = st.text_area("主要用途描述*", height=100, key="data_raw_main_usage")
                
                submitted = st.form_submit_button("添加原材料", type="primary")
                if submitted:
                    if material_name and main_usage:
                        # 检查是否重复
                        existing_names = [m.get("name") for m in st.session_state.raw_materials]
                        if material_name in existing_names:
                            st.error(f"原材料 '{material_name}' 已存在！")
                        else:
                            new_material = {
                                "id": len(st.session_state.raw_materials) + 1,
                                "name": material_name,
                                "chemical_formula": chemical_formula,
                                "molecular_weight": molecular_weight,
                                "solid_content": solid_content,
                                "unit_price": unit_price,
                                "odor": odor,
                                "storage_condition": storage_condition,
                                "supplier": supplier,
                                "main_usage": main_usage,
                                "created_date": datetime.now().strftime("%Y-%m-%d")
                            }
                            st.session_state.raw_materials.append(new_material)
                            st.success(f"原材料 '{material_name}' 添加成功！")
                            time.sleep(0.5)
                            st.rerun()
                    else:
                        st.error("请填写带*的必填项")
        
        # 原材料列表
        st.divider()
        st.subheader("📋 原材料列表")
        
        if st.session_state.raw_materials:
            # 搜索功能
            search_col1, search_col2 = st.columns([3, 1])
            with search_col1:
                search_term = st.text_input("🔍 搜索原材料", 
                                           placeholder="输入名称或化学式搜索",
                                           key="data_raw_material_search")
            with search_col2:
                items_per_page = st.selectbox("每页显示", [10, 20, 50], index=0, key="data_raw_material_page_size")
            
            # 过滤数据
            filtered_materials = st.session_state.raw_materials
            if search_term:
                filtered_materials = [
                    m for m in filtered_materials
                    if search_term.lower() in m.get("name", "").lower() or 
                    search_term.lower() in m.get("chemical_formula", "").lower()
                ]
            
            # 分页
            if "data_material_page" not in st.session_state:
                st.session_state.data_material_page = 1
            
            total_pages = max(1, (len(filtered_materials) + items_per_page - 1) // items_per_page)
            start_idx = (st.session_state.data_material_page - 1) * items_per_page
            end_idx = min(start_idx + items_per_page, len(filtered_materials))
            current_materials = filtered_materials[start_idx:end_idx]
            
            # 显示表格
            if current_materials:
                # 创建紧凑表格
                for material in current_materials:
                    with st.container():
                        col1, col2, col3 = st.columns([2, 2, 1])
                        with col1:
                            st.markdown(f"**{material['name']}**")
                            if material['chemical_formula']:
                                st.caption(f"化学式: {material['chemical_formula']}")
                            st.caption(f"分子量: {material['molecular_weight']} g/mol")
                        with col2:
                            st.caption(f"固含: {material['solid_content']}%")
                            st.caption(f"单价: ¥{material['unit_price']}/吨")
                            st.caption(f"气味: {material['odor']}")
                        with col3:
                            st.caption(f"ID: {material['id']}")
                            delete_key = f"data_del_material_{material['id']}"
                            if st.button("删除", key=delete_key):
                                st.session_state.raw_materials = [
                                    m for m in st.session_state.raw_materials 
                                    if m['id'] != material['id']
                                ]
                                st.success(f"已删除原材料: {material['name']}")
                                time.sleep(0.5)
                                st.rerun()
                        st.markdown(f"**用途:** {material['main_usage']}")
                        st.divider()
                
                # 分页控制
                if total_pages > 1:
                    pag_col1, pag_col2, pag_col3 = st.columns([1, 2, 1])
                    with pag_col2:
                        col_prev, col_page, col_next = st.columns([1, 2, 1])
                        with col_prev:
                            prev_key = "data_raw_mat_prev"
                            if st.button("⬅️", key=prev_key) and st.session_state.data_material_page > 1:
                                st.session_state.data_material_page -= 1
                                st.rerun()
                        with col_page:
                            page_num = st.number_input(
                                "页码", 
                                min_value=1, 
                                max_value=total_pages,
                                value=st.session_state.data_material_page,
                                key="data_raw_mat_page_input",
                                label_visibility="collapsed"
                            )
                            if page_num != st.session_state.data_material_page:
                                st.session_state.data_material_page = page_num
                                st.rerun()
                        with col_next:
                            next_key = "data_raw_mat_next"
                            if st.button("➡️", key=next_key) and st.session_state.data_material_page < total_pages:
                                st.session_state.data_material_page += 1
                                st.rerun()
            else:
                st.info("没有找到匹配的原材料")
        else:
            st.info("暂无原材料数据，请添加第一个原材料")
    
    # ==================== 合成实验模块 ====================
    with tab1:
        st.subheader("🧪 合成实验记录")
        
        # 初始化合成实验数据
        if "synthesis_records" not in st.session_state:
            st.session_state.synthesis_records = []
        
        # 获取实验项目选项
        experiments = data_manager.get_all_experiments()
        experiment_options = {f"{e['id']}: {e['name']}": e['id'] for e in experiments}
        
        # 获取原材料选项
        raw_material_names = [m['name'] for m in st.session_state.raw_materials] if st.session_state.raw_materials else []
        raw_material_options = {m['name']: m['id'] for m in st.session_state.raw_materials} if st.session_state.raw_materials else {}
        
        # 添加新合成实验表单
        with st.expander("➕ 新增合成实验", expanded=True):
            with st.form("data_recording_synthesis_experiment_form", clear_on_submit=True):
                # ==================== 第一部分：基础信息 ====================
                st.markdown("### 📝 第一部分：基础信息")
                base_col1, base_col2 = st.columns(2)
                
                with base_col1:
                    # 关联实验项目
                    if experiment_options:
                        selected_exp_key = st.selectbox(
                            "关联实验项目*",
                            options=["请选择..."] + list(experiment_options.keys()),
                            key="data_synthesis_project_select"
                        )
                        experiment_id = experiment_options.get(selected_exp_key) if selected_exp_key != "请选择..." else None
                    else:
                        st.warning("请先在实验管理模块创建实验")
                        experiment_id = None
                    
                    # 配方编号
                    formula_id = st.text_input("配方编号*", 
                                             placeholder="例如: PC-001-202401",
                                             key="data_synthesis_formula_id")
                    
                with base_col2:
                    # 设计固含
                    design_solid_content = st.number_input("设计固含 (%)*", 
                                                          min_value=0.0, 
                                                          max_value=100.0,
                                                          value=40.0,
                                                          step=0.1,
                                                          help="设计的固含量百分比",
                                                          key="data_synthesis_design_solid")
                    
                    # 合成日期
                    synthesis_date = st.date_input("合成日期", 
                                                  datetime.now(),
                                                  key="data_synthesis_date")
                    
                    # 操作人
                    operator = st.text_input("操作人*", 
                                            placeholder="请输入操作人员姓名",
                                            key="data_synthesis_operator")
                
                st.divider()
                
                # ==================== 第二部分：反应釜物料 ====================
                st.markdown("### ⚗️ 第二部分：反应釜物料")
                st.info("请从原材料库中选择以下物料并填写用量（单位: g）")
                
                # 反应釜物料 - 使用表格布局
                reactor_cols = st.columns(7)
                reactor_materials = []
                
                # 定义反应釜物料列表
                reactor_items = [
                    {"name": "单体1", "key": "monomer1"},
                    {"name": "单体2", "key": "monomer2"},
                    {"name": "单体3", "key": "monomer3"},
                    {"name": "单体4", "key": "monomer4"},
                    {"name": "引发剂", "key": "initiator"},
                    {"name": "链转移剂1", "key": "chain_transfer1"},
                    {"name": "水", "key": "water_reactor"}
                ]
                
                for i, item in enumerate(reactor_items):
                    with reactor_cols[i]:
                        st.markdown(f"**{item['name']}**")
                        
                        # 物料选择 - 使用模糊搜索的selectbox
                        material_options = ["请选择..."] + raw_material_names
                        selected_material = st.selectbox(
                            f"选择{item['name']}",
                            options=material_options,
                            key=f"data_reactor_{item['key']}_select_{i}",
                            help="输入名称搜索原材料",
                            index=0,
                            label_visibility="collapsed"
                        )
                        
                        # 用量输入
                        amount = st.number_input(
                            f"用量 (g)",
                            min_value=0.0,
                            step=0.1,
                            value=0.0,
                            key=f"data_reactor_{item['key']}_amount_{i}",
                            label_visibility="collapsed"
                        )
                        
                        if selected_material and selected_material != "请选择..." and amount > 0:
                            reactor_materials.append({
                                "name": item["name"],
                                "material_name": selected_material,
                                "amount": amount
                            })
                
                # 显示反应釜物料总用量
                total_reactor = sum([m["amount"] for m in reactor_materials])
                st.caption(f"反应釜物料总用量: **{total_reactor:.2f} g**")
                
                st.divider()
                
                # ==================== 第三部分：A料 ====================
                st.markdown("### 🔴 第三部分：A料")
                st.info("A料组成及滴加参数")
                
                # A料物料
                a_cols = st.columns(6)
                a_materials = []
                
                # 定义A料物料列表
                a_items = [
                    {"name": "单体a", "key": "monomer_a"},
                    {"name": "单体b", "key": "monomer_b"},
                    {"name": "单体c", "key": "monomer_c"},
                    {"name": "单体d", "key": "monomer_d"},
                    {"name": "水", "key": "water_a"},
                    {"name": "其他", "key": "other_a"}
                ]
                
                for i, item in enumerate(a_items):
                    with a_cols[i]:
                        st.markdown(f"**{item['name']}**")
                        
                        # 物料选择 - 使用模糊搜索的selectbox
                        material_options = ["请选择..."] + raw_material_names
                        selected_material = st.selectbox(
                            f"选择{item['name']}",
                            options=material_options,
                            key=f"data_a_{item['key']}_select_{i}",
                            help="输入名称搜索原材料",
                            index=0,
                            label_visibility="collapsed"
                        )
                        
                        # 用量输入
                        amount = st.number_input(
                            f"用量 (g)",
                            min_value=0.0,
                            step=0.1,
                            value=0.0,
                            key=f"data_a_{item['key']}_amount_{i}",
                            label_visibility="collapsed"
                        )
                        
                        if selected_material and selected_material != "请选择..." and amount > 0:
                            a_materials.append({
                                "name": item["name"],
                                "material_name": selected_material,
                                "amount": amount
                            })
                
                # A料滴加参数
                st.markdown("**滴加参数**")
                a_drip_col1, a_drip_col2, a_drip_col3 = st.columns(3)
                
                with a_drip_col1:
                    # A料总量（自动计算）
                    a_total_amount = sum([m["amount"] for m in a_materials])
                    # 修复：移除metric的key参数
                    st.metric("A料总用量", f"{a_total_amount:.2f} g")
                
                with a_drip_col2:
                    # 滴加时间
                    a_drip_time = st.number_input(
                        "滴加时间 (分钟)*",
                        min_value=0.0,
                        value=120.0,
                        step=1.0,
                        key="data_a_drip_time_input"
                    )
                
                with a_drip_col3:
                    # 滴加速度（自动计算）
                    a_drip_speed = 0.0
                    if a_drip_time > 0 and a_total_amount > 0:
                        a_drip_speed = a_total_amount / a_drip_time
                    # 修复：移除metric的key参数
                    st.metric("滴加速度", f"{a_drip_speed:.2f} g/min")
                
                st.divider()
                
                # ==================== 第四部分：B料 ====================
                st.markdown("### 🔵 第四部分：B料")
                st.info("B料组成及滴加参数")
                
                # B料物料
                b_cols = st.columns(5)
                b_materials = []
                
                # 定义B料物料列表
                b_items = [
                    {"name": "引发剂2", "key": "initiator2"},
                    {"name": "链转移剂2", "key": "chain_transfer2"},
                    {"name": "水", "key": "water_b"},
                    {"name": "其他1", "key": "other_b1"},
                    {"name": "其他2", "key": "other_b2"}
                ]
                
                for i, item in enumerate(b_items):
                    with b_cols[i]:
                        st.markdown(f"**{item['name']}**")
                        
                        # 物料选择 - 使用模糊搜索的selectbox
                        material_options = ["请选择..."] + raw_material_names
                        selected_material = st.selectbox(
                            f"选择{item['name']}",
                            options=material_options,
                            key=f"data_b_{item['key']}_select_{i}",
                            help="输入名称搜索原材料",
                            index=0,
                            label_visibility="collapsed"
                        )
                        
                        # 用量输入
                        amount = st.number_input(
                            f"用量 (g)",
                            min_value=0.0,
                            step=0.1,
                            value=0.0,
                            key=f"data_b_{item['key']}_amount_{i}",
                            label_visibility="collapsed"
                        )
                        
                        if selected_material and selected_material != "请选择..." and amount > 0:
                            b_materials.append({
                                "name": item["name"],
                                "material_name": selected_material,
                                "amount": amount
                            })
                
                # B料滴加参数
                st.markdown("**滴加参数**")
                b_drip_col1, b_drip_col2, b_drip_col3 = st.columns(3)
                
                with b_drip_col1:
                    # B料总量（自动计算）
                    b_total_amount = sum([m["amount"] for m in b_materials])
                    # 修复：移除metric的key参数
                    st.metric("B料总用量", f"{b_total_amount:.2f} g")
                
                with b_drip_col2:
                    # 滴加时间
                    b_drip_time = st.number_input(
                        "滴加时间 (分钟)*",
                        min_value=0.0,
                        value=60.0,
                        step=1.0,
                        key="data_b_drip_time_input"
                    )
                
                with b_drip_col3:
                    # 滴加速度（自动计算）
                    b_drip_speed = 0.0
                    if b_drip_time > 0 and b_total_amount > 0:
                        b_drip_speed = b_total_amount / b_drip_time
                    # 修复：移除metric的key参数
                    st.metric("滴加速度", f"{b_drip_speed:.2f} g/min")
                
                st.divider()
                
                # ==================== 第五部分：反应参数 ====================
                st.markdown("### 🔥 第五部分：反应参数")
                
                # 反应参数
                st.markdown("**温度控制**")
                reaction_col1, reaction_col2, reaction_col3 = st.columns(3)
                
                with reaction_col1:
                    # 起始温度
                    start_temp = st.number_input(
                        "起始温度 (°C)*",
                        min_value=0.0,
                        max_value=100.0,
                        value=20.0,
                        step=0.5,
                        key="data_start_temp_input"
                    )
                
                with reaction_col2:
                    # 最高温度
                    max_temp = st.number_input(
                        "最高温度 (°C)*",
                        min_value=0.0,
                        max_value=200.0,
                        value=80.0,
                        step=0.5,
                        key="data_max_temp_input"
                    )
                
                with reaction_col3:
                    # 保温时间
                    holding_time = st.number_input(
                        "保温时间 (小时)*",
                        min_value=0.0,
                        max_value=24.0,
                        value=2.0,
                        step=0.5,
                        key="data_holding_time_input"
                    )
                
                # 工艺备注
                process_notes = st.text_area(
                    "实验工艺备注",
                    height=150,
                    placeholder="请详细记录实验过程中的观察、调整、异常情况等工艺信息...",
                    key="data_synthesis_process_notes"
                )
                
                # 提交按钮
                submitted = st.form_submit_button("💾 保存合成实验记录", type="primary")
                
                if submitted:
                    # 验证必填项
                    validation_errors = []
                    
                    if not experiment_id:
                        validation_errors.append("请选择关联实验项目")
                    
                    if not formula_id:
                        validation_errors.append("请输入配方编号")
                    
                    if not design_solid_content:
                        validation_errors.append("请输入设计固含")
                    
                    if not operator:
                        validation_errors.append("请输入操作人")
                    
                    if a_drip_time <= 0:
                        validation_errors.append("请输入有效的A料滴加时间")
                    
                    if b_drip_time <= 0:
                        validation_errors.append("请输入有效的B料滴加时间")
                    
                    if start_temp <= 0:
                        validation_errors.append("请输入有效的起始温度")
                    
                    if max_temp <= 0 or max_temp < start_temp:
                        validation_errors.append("最高温度必须大于起始温度")
                    
                    if holding_time <= 0:
                        validation_errors.append("请输入有效的保温时间")
                    
                    # 检查是否选择了至少一种物料
                    if not reactor_materials and not a_materials and not b_materials:
                        validation_errors.append("请至少添加一种物料")
                    
                    if validation_errors:
                        for error in validation_errors:
                            st.error(error)
                    else:
                        # 构建新的合成实验记录
                        new_record = {
                            "id": len(st.session_state.synthesis_records) + 1,
                            "formula_id": formula_id,
                            "experiment_id": experiment_id,
                            "design_solid_content": design_solid_content,
                            "operator": operator,
                            "synthesis_date": synthesis_date.strftime("%Y-%m-%d"),
                            
                            # 反应釜物料
                            "reactor_materials": reactor_materials,
                            "reactor_total_amount": total_reactor,
                            
                            # A料
                            "a_materials": a_materials,
                            "a_total_amount": a_total_amount,
                            "a_drip_time": a_drip_time,
                            "a_drip_speed": a_drip_speed,
                            
                            # B料
                            "b_materials": b_materials,
                            "b_total_amount": b_total_amount,
                            "b_drip_time": b_drip_time,
                            "b_drip_speed": b_drip_speed,
                            
                            # 反应参数
                            "start_temp": start_temp,
                            "max_temp": max_temp,
                            "holding_time": holding_time,
                            
                            # 备注
                            "process_notes": process_notes,
                            
                            # 元数据
                            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "last_modified": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        
                        # 保存到session_state
                        st.session_state.synthesis_records.append(new_record)
                        
                        # 显示成功消息和摘要
                        st.success(f"✅ 合成实验记录 '{formula_id}' 保存成功！")
                        
                        # 显示数据摘要
                        with st.expander("📋 查看数据摘要", expanded=False):
                            summary_col1, summary_col2 = st.columns(2)
                            
                            with summary_col1:
                                st.markdown("**基础信息**")
                                st.write(f"**配方编号:** {formula_id}")
                                st.write(f"**操作人:** {operator}")
                                st.write(f"**设计固含:** {design_solid_content}%")
                                st.write(f"**合成日期:** {synthesis_date.strftime('%Y-%m-%d')}")
                            
                            with summary_col2:
                                st.markdown("**物料总览**")
                                st.write(f"**反应釜总用量:** {total_reactor:.2f} g")
                                st.write(f"**A料总用量:** {a_total_amount:.2f} g")
                                st.write(f"**B料总用量:** {b_total_amount:.2f} g")
                                total_materials = total_reactor + a_total_amount + b_total_amount
                                st.write(f"**总物料量:** {total_materials:.2f} g")
                        
                        time.sleep(0.5)
                        st.rerun()
    
    # ==================== 合成实验数据查看 ====================
        st.divider()
        st.subheader("📊 合成实验数据查看")
        
        if st.session_state.synthesis_records:
            # 搜索和过滤功能
            search_col1, search_col2, search_col3 = st.columns([2, 2, 1])
            with search_col1:
                search_formula = st.text_input("搜索配方编号", 
                                             placeholder="输入配方编号",
                                             key="data_synthesis_search_formula")
            with search_col2:
                search_operator = st.text_input("搜索操作人", 
                                              placeholder="输入操作人姓名",
                                              key="data_synthesis_search_operator")
            with search_col3:
                items_per_page = st.selectbox("每页显示", [10, 20, 50], index=1, key="data_synthesis_page_size")
            
            # 过滤数据
            filtered_records = st.session_state.synthesis_records
            if search_formula:
                filtered_records = [
                    r for r in filtered_records
                    if search_formula.lower() in r.get("formula_id", "").lower()
                ]
            if search_operator:
                filtered_records = [
                    r for r in filtered_records
                    if search_operator.lower() in r.get("operator", "").lower()
                ]
            
            # 分页
            if "data_syn_page" not in st.session_state:
                st.session_state.data_syn_page = 1
            
            total_pages = max(1, (len(filtered_records) + items_per_page - 1) // items_per_page)
            start_idx = (st.session_state.data_syn_page - 1) * items_per_page
            end_idx = min(start_idx + items_per_page, len(filtered_records))
            current_records = filtered_records[start_idx:end_idx]
            
            # 显示表格
            if current_records:
                # 表头
                header_cols = st.columns([1, 2, 2, 2, 2, 2])
                headers = ["序号", "配方编号", "操作人", "设计固含(%)", "合成日期", "操作"]
                
                for i, header in enumerate(headers):
                    header_cols[i].markdown(f"**{header}**")
                
                st.divider()
                
                # 数据行
                for idx, record in enumerate(current_records, start=start_idx+1):
                    with st.container():
                        row_cols = st.columns([1, 2, 2, 2, 2, 2])
                        
                        with row_cols[0]:
                            st.write(idx)
                        
                        with row_cols[1]:
                            formula = record.get("formula_id", "")
                            st.write(f"`{formula}`")
                        
                        with row_cols[2]:
                            st.write(record.get("operator", ""))
                        
                        with row_cols[3]:
                            st.write(f"{record.get('design_solid_content', 0)}%")
                        
                        with row_cols[4]:
                            st.write(record.get("synthesis_date", ""))
                        
                        with row_cols[5]:
                            # 查看详情按钮
                            view_key = f"data_view_synth_{record['id']}_{idx}"
                            if st.button("📋 详情", key=view_key):
                                if f"data_show_detail_{record['id']}" not in st.session_state:
                                    st.session_state[f"data_show_detail_{record['id']}"] = False
                                st.session_state[f"data_show_detail_{record['id']}"] = not st.session_state[f"data_show_detail_{record['id']}"]
                                st.rerun()
                            
                            # 删除按钮
                            delete_key = f"data_delete_synth_{record['id']}_{idx}"
                            if st.button("🗑️ 删除", key=delete_key):
                                st.session_state.synthesis_records = [
                                    r for r in st.session_state.synthesis_records 
                                    if r['id'] != record['id']
                                ]
                                st.success(f"已删除合成实验: {formula}")
                                time.sleep(0.5)
                                st.rerun()
                        
                        # 详细信息（可折叠）
                        if st.session_state.get(f"data_show_detail_{record['id']}", False):
                            with st.expander(f"📋 配方 {formula} 详细信息", expanded=True):
                                # 分页显示详细信息
                                detail_tabs = st.tabs(["基础信息", "反应釜物料", "A料", "B料", "反应参数", "工艺备注"])
                                
                                with detail_tabs[0]:
                                    base_col1, base_col2 = st.columns(2)
                                    with base_col1:
                                        st.markdown("**基础信息**")
                                        st.write(f"**配方编号:** {record.get('formula_id')}")
                                        st.write(f"**操作人:** {record.get('operator')}")
                                        st.write(f"**合成日期:** {record.get('synthesis_date')}")
                                    
                                    with base_col2:
                                        st.markdown("**设计参数**")
                                        st.write(f"**设计固含:** {record.get('design_solid_content')}%")
                                        st.write(f"**起始温度:** {record.get('start_temp')}°C")
                                        st.write(f"**最高温度:** {record.get('max_temp')}°C")
                                        st.write(f"**保温时间:** {record.get('holding_time')}小时")
                                
                                with detail_tabs[1]:
                                    if record.get('reactor_materials'):
                                        st.markdown("**反应釜物料组成**")
                                        reactor_df = pd.DataFrame(record['reactor_materials'])
                                        st.dataframe(reactor_df, use_container_width=True)
                                        # 修复：移除metric的key参数
                                        st.metric("反应釜总用量", f"{record.get('reactor_total_amount', 0):.2f} g")
                                    else:
                                        st.info("暂无反应釜物料数据")
                                
                                with detail_tabs[2]:
                                    if record.get('a_materials'):
                                        st.markdown("**A料组成**")
                                        a_df = pd.DataFrame(record['a_materials'])
                                        st.dataframe(a_df, use_container_width=True)
                                        
                                        a_info_col1, a_info_col2, a_info_col3 = st.columns(3)
                                        with a_info_col1:
                                            # 修复：移除metric的key参数
                                            st.metric("A料总用量", f"{record.get('a_total_amount', 0):.2f} g")
                                        with a_info_col2:
                                            # 修复：移除metric的key参数
                                            st.metric("滴加时间", f"{record.get('a_drip_time', 0)} 分钟")
                                        with a_info_col3:
                                            # 修复：移除metric的key参数
                                            st.metric("滴加速度", f"{record.get('a_drip_speed', 0):.2f} g/min")
                                    else:
                                        st.info("暂无A料数据")
                                
                                with detail_tabs[3]:
                                    if record.get('b_materials'):
                                        st.markdown("**B料组成**")
                                        b_df = pd.DataFrame(record['b_materials'])
                                        st.dataframe(b_df, use_container_width=True)
                                        
                                        b_info_col1, b_info_col2, b_info_col3 = st.columns(3)
                                        with b_info_col1:
                                            # 修复：移除metric的key参数
                                            st.metric("B料总用量", f"{record.get('b_total_amount', 0):.2f} g")
                                        with b_info_col2:
                                            # 修复：移除metric的key参数
                                            st.metric("滴加时间", f"{record.get('b_drip_time', 0)} 分钟")
                                        with b_info_col3:
                                            # 修复：移除metric的key参数
                                            st.metric("滴加速度", f"{record.get('b_drip_speed', 0):.2f} g/min")
                                    else:
                                        st.info("暂无B料数据")
                                
                                with detail_tabs[4]:
                                    st.markdown("**反应参数**")
                                    reaction_cols = st.columns(3)
                                    with reaction_cols[0]:
                                        # 修复：移除metric的key参数
                                        st.metric("起始温度", f"{record.get('start_temp', 0)}°C")
                                    with reaction_cols[1]:
                                        # 修复：移除metric的key参数
                                        st.metric("最高温度", f"{record.get('max_temp', 0)}°C")
                                    with reaction_cols[2]:
                                        # 修复：移除metric的key参数
                                        st.metric("保温时间", f"{record.get('holding_time', 0)}小时")
                                
                                with detail_tabs[5]:
                                    if record.get('process_notes'):
                                        st.markdown("**实验工艺备注**")
                                        st.info(record['process_notes'])
                                    else:
                                        st.info("暂无工艺备注")
                        
                        st.divider()
                
                # 分页控制
                if total_pages > 1:
                    st.markdown("---")
                    pag_col1, pag_col2, pag_col3 = st.columns([2, 1, 2])
                    
                    with pag_col1:
                        prev_key = "data_synthesis_prev"
                        if st.button("⬅️ 上一页", 
                                   disabled=st.session_state.data_syn_page <= 1,
                                   key=prev_key):
                            st.session_state.data_syn_page -= 1
                            st.rerun()
                    
                    with pag_col2:
                        st.markdown(f"**第 {st.session_state.data_syn_page}/{total_pages} 页**")
                    
                    with pag_col3:
                        next_key = "data_synthesis_next"
                        if st.button("下一页 ➡️", 
                                   disabled=st.session_state.data_syn_page >= total_pages,
                                   key=next_key):
                            st.session_state.data_syn_page += 1
                            st.rerun()
            else:
                st.info("没有找到匹配的合成实验记录")
        else:
            st.info("暂无合成实验数据，请添加第一条记录")
    
    # ==================== 成品减水剂模块 ====================
    with tab3:
        st.subheader("📊 成品减水剂管理")
        
        # 初始化成品减水剂数据
        if "products" not in st.session_state:
            st.session_state.products = []
        
        with st.expander("➕ 新增成品减水剂", expanded=True):
            with st.form("add_product_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    product_name = st.text_input("成品名称*", 
                                                placeholder="例如: PC-2024-HP")
                    product_code = st.text_input("产品编号*",
                                                placeholder="例如: PC001-2024")
                    batch_number = st.text_input("生产批号")
                    production_date = st.date_input("生产日期", datetime.now())
                with col2:
                    solid_content = st.number_input("固含(%)*", 
                                                   min_value=0.0, 
                                                   max_value=100.0,
                                                   value=40.0,
                                                   step=0.1)
                    density = st.number_input("密度 (g/cm³)", 
                                             min_value=0.8, 
                                             max_value=2.0,
                                             value=1.05,
                                             step=0.01)
                    ph_value = st.number_input("pH值", 
                                              min_value=0.0, 
                                              max_value=14.0,
                                              value=7.0,
                                              step=0.1)
                
                # 关联配方选项（来自合成实验或已有的成品）
                formula_options = []
                if st.session_state.synthesis_records:
                    formula_options.extend([
                        f"合成实验: {r['formula_id']}" for r in st.session_state.synthesis_records
                    ])
                if st.session_state.products:
                    formula_options.extend([
                        f"成品: {p['product_name']}" for p in st.session_state.products
                    ])
                
                if formula_options:
                    base_formula = st.selectbox("基础配方", 
                                              options=["自定义配方"] + formula_options)
                else:
                    base_formula = "自定义配方"
                
                # 原料组成
                st.markdown("### 原料组成")
                ingredient_cols = st.columns(3)
                ingredients = []
                
                for i in range(3):
                    with ingredient_cols[i]:
                        if raw_material_options:
                            material_name = st.selectbox(
                                f"原料{i+1}",
                                options=[""] + list(raw_material_options.keys()),
                                key=f"product_material_{i}"
                            )
                            if material_name:
                                amount = st.number_input(f"用量 (%)", 
                                                       min_value=0.0,
                                                       max_value=100.0,
                                                       step=0.1,
                                                       key=f"product_amount_{i}")
                                ingredients.append({
                                    "name": material_name,
                                    "amount": amount
                                })
                
                description = st.text_area("产品描述", height=100)
                
                submitted = st.form_submit_button("保存成品", type="primary")
                if submitted:
                    if product_name and product_code:
                        new_product = {
                            "id": len(st.session_state.products) + 1,
                            "product_name": product_name,
                            "product_code": product_code,
                            "batch_number": batch_number,
                            "production_date": production_date.strftime("%Y-%m-%d"),
                            "solid_content": solid_content,
                            "density": density,
                            "ph_value": ph_value,
                            "base_formula": base_formula,
                            "ingredients": ingredients,
                            "description": description,
                            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        st.session_state.products.append(new_product)
                        st.success(f"成品减水剂 '{product_name}' 保存成功！")
                    else:
                        st.error("请填写必填项")
        
        # 成品列表查看
        st.divider()
        if st.session_state.products:
            st.subheader("📋 成品列表")
            for product in st.session_state.products:
                with st.container():
                    col1, col2, col3 = st.columns([2, 2, 1])
                    with col1:
                        st.markdown(f"**{product['product_name']}**")
                        st.caption(f"编号: {product['product_code']}")
                        st.caption(f"批号: {product['batch_number']}")
                    with col2:
                        st.caption(f"固含: {product['solid_content']}%")
                        st.caption(f"密度: {product['density']} g/cm³")
                        st.caption(f"生产日期: {product['production_date']}")
                    with col3:
                        if st.button("查看详情", key=f"view_product_{product['id']}"):
                            if f"show_product_{product['id']}" not in st.session_state:
                                st.session_state[f"show_product_{product['id']}"] = False
                            st.session_state[f"show_product_{product['id']}"] = not st.session_state[f"show_product_{product['id']}"]
                    
                    # 详细信息
                    if st.session_state.get(f"show_product_{product['id']}", False):
                        with st.expander("详细信息", expanded=True):
                            detail_col1, detail_col2 = st.columns(2)
                            with detail_col1:
                                st.markdown("**基础信息**")
                                st.write(f"**基础配方:** {product['base_formula']}")
                                st.write(f"**pH值:** {product['ph_value']}")
                                if product.get('description'):
                                    st.markdown("**描述:**")
                                    st.info(product['description'])
                            
                            with detail_col2:
                                st.markdown("**原料组成**")
                                for ing in product.get('ingredients', []):
                                    if ing.get('name'):
                                        st.write(f"- {ing['name']}: {ing.get('amount', 0)}%")
                        
                    st.divider()
        else:
            st.info("暂无成品减水剂数据")
    
    # ==================== 净浆实验模块 ====================
    with tab4:
        st.subheader("🧫 净浆实验记录")
        
        # 获取可关联的配方选项
        paste_formula_options = []
        if st.session_state.synthesis_records:
            paste_formula_options.extend([
                f"合成实验: {r['formula_id']}" for r in st.session_state.synthesis_records
            ])
        if st.session_state.products:
            paste_formula_options.extend([
                f"成品: {p['product_name']}" for p in st.session_state.products
            ])
        
        with st.form("paste_experiment_form", clear_on_submit=True):
            st.markdown("### 实验设置")
            col1, col2 = st.columns(2)
            with col1:
                if paste_formula_options:
                    formula_name = st.selectbox("关联配方*", 
                                              options=paste_formula_options)
                else:
                    st.warning("请先创建合成实验或成品减水剂")
                    formula_name = None
                
                water_cement_ratio = st.number_input("水胶比*", 
                                                    min_value=0.1, 
                                                    max_value=1.0,
                                                    value=0.29,
                                                    step=0.01)
                
                cement_amount = st.number_input("水泥用量 (g)*", 
                                               min_value=100.0,
                                               value=300.0,
                                               step=1.0)
            
            with col2:
                water_amount = st.number_input("用水量 (g)*", 
                                              min_value=0.0,
                                              value=87.0,
                                              step=0.1)
                
                admixture_dosage = st.number_input("减水剂掺量 (%)*", 
                                                  min_value=0.0,
                                                  max_value=10.0,
                                                  value=0.2,
                                                  step=0.01)
                
                test_date = st.date_input("测试日期", datetime.now())
            
            # 性能指标（可折叠）
            with st.expander("📊 性能指标", expanded=False):
                perf_col1, perf_col2, perf_col3 = st.columns(3)
                with perf_col1:
                    slump_flow = st.number_input("流动度 (mm)", 
                                                min_value=0.0,
                                                value=220.0,
                                                step=1.0)
                    setting_time_initial = st.number_input("初凝时间 (min)", 
                                                          min_value=0.0,
                                                          value=300.0,
                                                          step=1.0)
                with perf_col2:
                    slump_flow_1h = st.number_input("1h流动度 (mm)", 
                                                   min_value=0.0,
                                                   value=200.0,
                                                   step=1.0)
                    setting_time_final = st.number_input("终凝时间 (min)", 
                                                        min_value=0.0,
                                                        value=480.0,
                                                        step=1.0)
                with perf_col3:
                    air_content = st.number_input("含气量 (%)", 
                                                 min_value=0.0,
                                                 max_value=20.0,
                                                 value=2.5,
                                                 step=0.1)
                    bleeding_rate = st.number_input("泌水率 (%)", 
                                                   min_value=0.0,
                                                   max_value=10.0,
                                                   value=0.5,
                                                   step=0.1)
            
            notes = st.text_area("实验备注", height=80)
            
            submitted = st.form_submit_button("保存净浆实验", type="primary")
            if submitted:
                if formula_name and water_cement_ratio > 0:
                    st.success("净浆实验数据保存成功！")
    
    # ==================== 混凝土实验模块 ====================
    with tab6:
        st.subheader("🏢 混凝土实验记录")
        
        # 获取可关联的配方选项
        concrete_formula_options = []
        if st.session_state.synthesis_records:
            concrete_formula_options.extend([
                f"合成实验: {r['formula_id']}" for r in st.session_state.synthesis_records
            ])
        if st.session_state.products:
            concrete_formula_options.extend([
                f"成品: {p['product_name']}" for p in st.session_state.products
            ])
        
        with st.form("concrete_experiment_form", clear_on_submit=True):
            st.markdown("### 配合比设计")
            
            if concrete_formula_options:
                formula_name = st.selectbox("关联减水剂配方*", 
                                          options=concrete_formula_options)
            else:
                st.warning("请先创建合成实验或成品减水剂")
                formula_name = None
            
            # 基础参数
            col1, col2 = st.columns(2)
            with col1:
                water_cement_ratio = st.number_input("水胶比*", 
                                                    min_value=0.1, 
                                                    max_value=1.0,
                                                    value=0.4,
                                                    step=0.01)
                
                sand_ratio = st.number_input("砂率 (%)*", 
                                            min_value=0.0,
                                            max_value=100.0,
                                            value=42.0,
                                            step=0.1)
                
                unit_weight = st.number_input("设计容重 (kg/m³)", 
                                            min_value=2000.0,
                                            max_value=3000.0,
                                            value=2400.0,
                                            step=10.0)
            
            with col2:
                admixture_dosage = st.number_input("减水剂掺量 (%)*", 
                                                  min_value=0.0,
                                                  max_value=5.0,
                                                  value=1.0,
                                                  step=0.05)
                
                sand_moisture = st.number_input("砂含水率 (%)", 
                                               min_value=0.0,
                                               max_value=20.0,
                                               value=3.0,
                                               step=0.1)
                
                stone_moisture = st.number_input("石含水率 (%)", 
                                                min_value=0.0,
                                                max_value=20.0,
                                                value=1.0,
                                                step=0.1)
            
            # 材料用量（可折叠）
            with st.expander("📦 材料用量 (kg/m³)", expanded=True):
                st.markdown("#### 胶凝材料")
                binder_cols = st.columns(4)
                with binder_cols[0]:
                    cement = st.number_input("水泥用量", 
                                           min_value=0.0,
                                           value=300.0,
                                           step=10.0,
                                           key="cement_amount")
                with binder_cols[1]:
                    mineral_admixture1 = st.number_input("矿物外加剂1", 
                                                        min_value=0.0,
                                                        value=50.0,
                                                        step=5.0)
                with binder_cols[2]:
                    mineral_admixture2 = st.number_input("矿物外加剂2", 
                                                        min_value=0.0,
                                                        value=0.0,
                                                        step=5.0)
                with binder_cols[3]:
                    mineral_admixture3 = st.number_input("矿物外加剂3", 
                                                        min_value=0.0,
                                                        value=0.0,
                                                        step=5.0)
                
                st.markdown("#### 骨料")
                aggregate_cols = st.columns(6)
                with aggregate_cols[0]:
                    sand1 = st.number_input("砂1", 
                                          min_value=0.0,
                                          value=800.0,
                                          step=10.0)
                with aggregate_cols[1]:
                    sand2 = st.number_input("砂2", 
                                          min_value=0.0,
                                          value=0.0,
                                          step=10.0)
                with aggregate_cols[2]:
                    sand3 = st.number_input("砂3", 
                                          min_value=0.0,
                                          value=0.0,
                                          step=10.0)
                with aggregate_cols[3]:
                    stone1 = st.number_input("石1", 
                                           min_value=0.0,
                                           value=1100.0,
                                           step=10.0)
                with aggregate_cols[4]:
                    stone2 = st.number_input("石2", 
                                           min_value=0.0,
                                           value=0.0,
                                           step=10.0)
                with aggregate_cols[5]:
                    stone3 = st.number_input("石3", 
                                           min_value=0.0,
                                           value=0.0,
                                           step=10.0)
                
                # 自动计算
                st.markdown("#### 自动计算")
                calc_cols = st.columns(3)
                
                # 计算总胶凝材料
                total_binder = cement + mineral_admixture1 + mineral_admixture2 + mineral_admixture3
                
                # 计算用水量
                water_amount = total_binder * water_cement_ratio
                
                # 计算实际用水量（考虑骨料含水）
                total_sand = sand1 + sand2 + sand3
                total_stone = stone1 + stone2 + stone3
                water_from_sand = total_sand * sand_moisture / 100
                water_from_stone = total_stone * stone_moisture / 100
                actual_water = water_amount - water_from_sand - water_from_stone
                
                # 计算总材料量
                total_materials = (
                    total_binder + 
                    total_sand + 
                    total_stone + 
                    water_amount + 
                    (total_binder * admixture_dosage / 100)
                )
                
                with calc_cols[0]:
                    st.metric("总胶凝材料", f"{total_binder:.1f} kg")
                    st.metric("计算用水量", f"{water_amount:.1f} kg")
                
                with calc_cols[1]:
                    st.metric("实际用水量", f"{actual_water:.1f} kg")
                    st.metric("砂含水引入", f"{water_from_sand:.1f} kg")
                
                with calc_cols[2]:
                    st.metric("石含水引入", f"{water_from_stone:.1f} kg")
                    st.metric("总材料量", f"{total_materials:.1f} kg")
            
            # 性能指标（可折叠）
            with st.expander("📊 混凝土性能指标", expanded=False):
                perf_col1, perf_col2, perf_col3 = st.columns(3)
                with perf_col1:
                    slump = st.number_input("坍落度 (mm)", 
                                          min_value=0.0,
                                          value=180.0,
                                          step=5.0)
                    compressive_7d = st.number_input("7天强度 (MPa)", 
                                                    min_value=0.0,
                                                    value=35.0,
                                                    step=0.1)
                with perf_col2:
                    slump_flow = st.number_input("扩展度 (mm)", 
                                               min_value=0.0,
                                               value=500.0,
                                               step=10.0)
                    compressive_28d = st.number_input("28天强度 (MPa)", 
                                                     min_value=0.0,
                                                     value=50.0,
                                                     step=0.1)
                with perf_col3:
                    air_content = st.number_input("含气量 (%)", 
                                                 min_value=0.0,
                                                 max_value=10.0,
                                                 value=3.0,
                                                 step=0.1)
                    chloride_content = st.number_input("氯离子含量 (%)", 
                                                      min_value=0.0,
                                                      max_value=0.1,
                                                      value=0.01,
                                                      step=0.001)
            
            notes = st.text_area("实验备注", height=100)
            
            submitted = st.form_submit_button("保存混凝土实验", type="primary")
            if submitted:
                if formula_name and water_cement_ratio > 0:
                    st.success("混凝土实验数据保存成功！")