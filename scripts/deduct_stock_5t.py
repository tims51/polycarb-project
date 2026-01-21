import os
import sys
from datetime import datetime

# 设置项目路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.append(src_path)

from services.data_service import DataService

def run_fix():
    ds = DataService()
    inventory = ds.get_product_inventory()
    records = ds.get_product_inventory_records()
    
    target_found = False
    for item in inventory:
        # 锁定目标：名称包含 "有碱" 且 库存 > 5
        if "有碱" in item.get("product_name", "") and float(item.get("stock_quantity", 0)) > 5:
            old_stock = float(item.get("stock_quantity", 0))
            new_stock = old_stock - 5.0
            item_id = item.get("id")
            item_name = item.get("product_name")
            
            print(f"找到目标产品：ID={item_id}, 名称={item_name}, 当前库存={old_stock:.4f}")
            
            # 执行扣减
            item["stock_quantity"] = new_stock
            item["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 添加流水记录
            new_record = {
                "id": ds._get_next_id(records),
                "date": datetime.now().strftime("%Y-%m-%d"),
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "product_name": item_name,
                "product_type": item.get("type", "速凝剂"),
                "type": "ADJUST_OUT",
                "quantity": 5.0,
                "reason": "修复数据合并导致的重复计算 (扣除多余的5吨)",
                "operator": "SystemFix",
                "snapshot_stock": new_stock
            }
            records.append(new_record)
            
            # 保存数据
            data = ds.load_data()
            data["product_inventory"] = inventory
            data["product_inventory_records"] = records
            if ds.save_data(data):
                print(f"✅ 已成功将 ID={item_id} 的库存从 {old_stock:.4f} 修正为 {new_stock:.4f}")
                target_found = True
            else:
                print(f"❌ 保存失败")
            break
            
    if not target_found:
        print("未找到符合条件的库存记录 (>5吨且包含'有碱')")

if __name__ == "__main__":
    run_fix()
