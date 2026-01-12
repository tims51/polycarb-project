import streamlit as st
import uuid

class PasteFluidityWidget:
    """
    净浆流动度指标功能模块 (组件化设计)
    
    Features:
    - 基础功能：初始流动度 (固定)
    - 扩展机制：动态添加时间序列流动度，支持自定义时间点
    - 响应式设计
    """
    
    def __init__(self, key_prefix: str):
        self.key_prefix = key_prefix
        # 初始流动度总是存在，不需要存储在动态列表中
        
        # 动态数据点列表
        # 结构: [{"id": "uuid", "time_label": "10min", "value": 0.0, "std_value": 0.0}]
        self.dynamic_rows_key = f"{self.key_prefix}_dynamic_rows"
        if self.dynamic_rows_key not in st.session_state:
            st.session_state[self.dynamic_rows_key] = []
            
    def load_defaults(self, defaults: dict):
        """
        加载默认值（例如来自标准样品历史数据）
        这将重置或填充动态行
        """
        # 清空现有动态行
        st.session_state[self.dynamic_rows_key] = []
        
        # 预定义排序顺序，以便加载时按逻辑顺序排列
        order_map = {
            "初始": 0, "Initial": 0, "initial": 0, 
            "10min": 1, "30min": 2, "60min": 3, "1h": 3, 
            "90min": 4, "1.5h": 4, "120min": 5, "2h": 5
        }
        
        # 筛选出非 initial 的键
        time_points = []
        for key, value in defaults.items():
            # 1. 忽略非数值类型 (防止 "自定义/无" 等字符串导致错误)
            if not isinstance(value, (int, float)):
                continue
                
            # 2. 忽略不需要处理的键
            if key in ["standard_sample_name"]:
                continue
            
            # 3. 忽略标准样品的历史数据 (我们只关心当时"测样"的数据作为新的标准)
            if key.startswith("std_"):
                continue
                
            # 尝试从 key 中提取时间标签
            label = key
            
            # 处理初始流动度
            if key == "initial" or key == "flow_initial_mm":
                label = "初始"
            elif key.startswith("flow_") and key.endswith("_mm"):
                label = key[5:-3] # remove flow_ and _mm
                
            time_points.append({"label": label, "value": value})
            
        # 排序
        time_points.sort(key=lambda x: order_map.get(x["label"], 999))
        
        # 添加到状态
        for pt in time_points:
            self.add_row(label=pt["label"], value=0.0, std_value=pt["value"])
            
    def add_row(self, label="", value=0.0, std_value=0.0):
        st.session_state[self.dynamic_rows_key].append({
            "id": str(uuid.uuid4()),
            "time_label": label,
            "value": value,
            "std_value": std_value
        })

    def render_input_section(self, experiment_purpose: str, standard_sample_defaults: dict = None):
        """
        渲染输入界面
        Args:
            experiment_purpose: 实验目的 ("性能对比测试" 或 "生产检测")
            standard_sample_defaults: 标准样品默认值 (仅用于兼容性，实际加载由load_defaults处理)
        """
        is_production = (experiment_purpose == "生产检测")
        
        st.markdown("##### 📏 净浆流动度测量")
        
        # --- 动态数据区域 ---
        # 按照时间顺序渲染
        rows = st.session_state[self.dynamic_rows_key]
        indices_to_remove = []
        
        # 定义排序逻辑（如果需要的话，但目前 rows 的顺序是添加顺序或加载顺序）
        # 这里直接渲染 rows
        
        for idx, row in enumerate(rows):
            row_id = row["id"]
            
            # 使用 expander 或者直接渲染行
            # 为了整齐，使用和初始流动度类似的列布局
            
            # 如果是生产检测，显示4列：时间点 | 标样值 | 测样值 | 删除
            # 否则显示3列：时间点 | 测样值 | 删除
            
            # 统一布局：与基础指标对齐
            # 基础指标是 st.columns(3)，分别占 1/3
            # 如果是生产检测，基础指标第一列是标样，第二列是测样，第三列空
            # 这里我们调整为：
            # 生产检测: 时间点(左) | 标样(中) | 测样(右) + 删除
            # 性能对比: 时间点(左) | (空) | 测样(右) + 删除
            
            cols = st.columns(3)
            
            # 1. 时间点 (左侧)
            with cols[0]:
                # 显示为类似基础指标的样式，但作为标题
                # 使用 text_input 修改时间点
                new_label = st.text_input(
                    f"时间点 ({idx+1})", 
                    value=row["time_label"], 
                    key=f"{self.key_prefix}_label_{row_id}",
                    placeholder="如: 1h"
                )
                rows[idx]["time_label"] = new_label
            
            # 2. 中间列 (标样 - 仅生产检测)
            with cols[1]:
                if is_production:
                    # 安全获取数值
                    try:
                        std_val_float = float(row.get("std_value", 0.0))
                    except (ValueError, TypeError):
                        std_val_float = 0.0
                        
                    new_std = st.number_input(
                        "标样流动度 (mm)",
                        min_value=0.0,
                        value=std_val_float,
                        step=1.0,
                        key=f"{self.key_prefix}_std_val_{row_id}"
                    )
                    rows[idx]["std_value"] = new_std
                else:
                    st.empty() # 占位
            
            # 3. 右侧列 (测样 + 删除)
            with cols[2]:
                try:
                    val_float = float(row["value"])
                except (ValueError, TypeError):
                    val_float = 0.0
                
                # 为了把删除按钮放在旁边，这里再分列
                sub_c1, sub_c2 = st.columns([4, 1])
                with sub_c1:
                    new_val = st.number_input(
                        "测样流动度 (mm)" if is_production else "流动度 (mm)",
                        min_value=0.0,
                        value=val_float,
                        step=1.0,
                        key=f"{self.key_prefix}_val_{row_id}"
                    )
                    rows[idx]["value"] = new_val
                
                with sub_c2:
                    st.write("") # 垂直对齐
                    st.write("") 
                    if st.button("🗑️", key=f"{self.key_prefix}_del_{row_id}"):
                        indices_to_remove.append(idx)
        
        # Remove deleted rows
        if indices_to_remove:
            for idx in sorted(indices_to_remove, reverse=True):
                del st.session_state[self.dynamic_rows_key][idx]
            st.rerun()
            
        st.markdown("---")
        
        # --- 3. 新增数据区域 ---
        st.markdown("###### ➕ 添加新时间点数据")
        
        # 新增数据的临时 key
        new_label_key = f"{self.key_prefix}_new_label"
        new_std_key = f"{self.key_prefix}_new_std"
        new_val_key = f"{self.key_prefix}_new_val"
        
        # Define callback for adding data
        error_key = f"{self.key_prefix}_add_error"
        
        def on_add_click():
            label_val = st.session_state.get(new_label_key, "").strip()
            val_val = st.session_state.get(new_val_key, 0.0)
            std_val = st.session_state.get(new_std_key, 0.0) if is_production else 0.0
            
            if label_val:
                self.add_row(label=label_val, value=val_val, std_value=std_val)
                st.session_state[new_label_key] = ""
                st.session_state[new_val_key] = 0.0
                if is_production:
                    st.session_state[new_std_key] = 0.0
            else:
                st.session_state[error_key] = "请输入时间点"

        # Show error if any
        if st.session_state.get(error_key):
            st.warning(st.session_state[error_key])
            del st.session_state[error_key]

        # 布局 - 保持与上方一致的3列布局
        cols_new = st.columns(3)
            
        with cols_new[0]:
            st.text_input("新时间点", key=new_label_key, placeholder="如: 1h")
            
        with cols_new[1]:
            if is_production:
                st.number_input("标样流动度 (mm)", min_value=0.0, step=1.0, key=new_std_key)
            else:
                st.empty()
                
        with cols_new[2]:
            sub_c1, sub_c2 = st.columns([4, 1])
            with sub_c1:
                st.number_input("测样流动度 (mm)" if is_production else "流动度 (mm)", min_value=0.0, step=1.0, key=new_val_key)
            with sub_c2:
                st.write("")
                st.write("")
                # 确认添加按钮
                st.button("✅", key=f"{self.key_prefix}_add_btn", on_click=on_add_click, help="点击添加")

    def get_data(self):
        """获取收集的数据"""
        data = {}
        
        # 1. 动态数据 (不再区分初始和动态，全部统一处理)
        # 尝试映射回标准字段 flow_X_mm 以兼容旧数据
        rows = st.session_state.get(self.dynamic_rows_key, [])
        for row in rows:
            label = row["time_label"].strip()
            if not label:
                continue
                
            # 处理特殊标签映射 (保持数据兼容性)
            if label in ["初始", "Initial", "initial", "0", "0min"]:
                key_name = "flow_initial_mm"
                std_key_name = "std_flow_initial_mm"
            else:
                # 构建键名 (移除非法字符)
                safe_label = "".join(c for c in label if c.isalnum() or c in "_")
                key_name = f"flow_{safe_label}_mm"
                std_key_name = f"std_flow_{safe_label}_mm"
            
            data[key_name] = row["value"]
            
            # 标准样品数据
            if "std_value" in row:
                data[std_key_name] = row["std_value"]
                
        return data
