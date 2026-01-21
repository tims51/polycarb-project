
import sys
import os
from pathlib import Path

# 设置路径，确保可以导入 src 目录下的模块
root_dir = Path(__file__).parent.parent
src_dir = root_dir / "src"
sys.path.append(str(src_dir))

# 模拟 Streamlit 环境，防止 DataService 初始化报错
import streamlit as st
if not hasattr(st, "session_state"):
    st.session_state = {}

try:
    from services.data_service import DataService
    from core.enums import DataCategory
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print(f"请确保在项目根目录下运行此脚本，且 src 目录结构正确。")
    sys.exit(1)

def normalize_product_data():
    print("🔍 开始扫描成品数据字段...")
    ds = DataService()
    data = ds.load_data()
    
    inventory = data.get(DataCategory.PRODUCT_INVENTORY.value, [])
    records = data.get(DataCategory.PRODUCT_INVENTORY_RECORDS.value, [])
    
    inv_count = 0
    rec_count = 0
    
    # 1. 清洗成品库存 (product_inventory)
    for item in inventory:
        modified = False
        # 处理 name -> product_name
        if "name" in item:
            if "product_name" not in item or not item["product_name"]:
                item["product_name"] = item["name"]
            del item["name"]
            modified = True
            
        # 确保 product_name 字段存在
        if "product_name" not in item:
            item["product_name"] = "未命名产品"
            modified = True
            
        if modified:
            inv_count += 1
            
    # 2. 清洗流水记录 (product_inventory_records)
    for record in records:
        modified = False
        if "name" in record:
            if "product_name" not in record or not record["product_name"]:
                record["product_name"] = record["name"]
            del record["name"]
            modified = True
            
        if "product_name" not in record:
            record["product_name"] = "未命名产品"
            modified = True
            
        if modified:
            rec_count += 1
            
    # 3. 保存数据
    if inv_count > 0 or rec_count > 0:
        if ds.save_data(data):
            print(f"✅ 数据清洗完成并已保存！")
            print(f"📊 统计信息：")
            print(f" - 成品库存 (product_inventory): 统一了 {inv_count} 条数据的字段")
            print(f" - 流水记录 (product_inventory_records): 统一了 {rec_count} 条数据的字段")
            print(f"\n💡 现在你可以安全地移除代码中所有针对 'name' 字段的兼容性补丁了。")
        else:
            print(f"❌ 数据保存失败，请检查文件权限。")
    else:
        print(f"✨ 数据已经是规范格式，无需清洗。")

if __name__ == "__main__":
    normalize_product_data()
