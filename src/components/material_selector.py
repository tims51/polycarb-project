import streamlit as st
from core.constants import RAW_MATERIAL_CATEGORIES

def render_material_cascade_selector(data_manager, inventory_service=None, key_prefix="mat", include_products=False):
    """
    返回选中的物料 ID, 对象 和 类型 (raw_material/product)
    """
    # 1. 选择类型 (如果包含产品)
    item_type = "raw_material"
    if include_products:
        item_type = st.radio("物料类型", ["原材料", "成品/半成品"], horizontal=True, key=f"{key_prefix}_type_selector")
        item_type = "raw_material" if item_type == "原材料" else "product"

    if item_type == "raw_material":
        # 原材料级联选择
        raw_materials = data_manager.get_all_raw_materials()
        
        usage_col, mat_col = st.columns(2)
        with usage_col:
            selected_usage = st.selectbox(
                "用途分类",
                options=["全部"] + RAW_MATERIAL_CATEGORIES,
                key=f"{key_prefix}_usage_selector"
            )
        
        filtered_mats = raw_materials
        if selected_usage != "全部":
            filtered_mats = [m for m in raw_materials if m.get("usage_category") == selected_usage]
        
        with mat_col:
            if not filtered_mats:
                st.warning("该分类下无物料")
                return None, None, "raw_material"
                
            # 优化标签显示："{name} ({code})" 或 "{name} (ID: {id})"
            def format_mat_label(m):
                name = m.get('name', '未知')
                code = m.get('code') or m.get('material_number')
                if code:
                    return f"{name} ({code})"
                return f"{name} (ID: {m.get('id')})"

            mat_options = {
                format_mat_label(m): m
                for m in filtered_mats
            }
            selected_label = st.selectbox("选择原材料", options=list(mat_options.keys()), key=f"{key_prefix}_mat_selector")
            selected_obj = mat_options[selected_label]
            return selected_obj.get("id"), selected_obj, "raw_material"
    else:
        # 产品选择
        if not inventory_service:
            st.error("未提供库存服务，无法选择产品")
            return None, None, "product"
            
        products = inventory_service.get_products()
        if not products:
            st.warning("暂无产品")
            return None, None, "product"
            
        prod_options = {
            f"{p.get('product_name') or p.get('name')} ({p.get('type', '其他')})": p
            for p in products
        }
        selected_label = st.selectbox("选择产品", options=list(prod_options.keys()), key=f"{key_prefix}_prod_selector")
        selected_obj = prod_options[selected_label]
        return selected_obj.get("id"), selected_obj, "product"
