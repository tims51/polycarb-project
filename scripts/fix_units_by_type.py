import sys
import os
import logging
from typing import Dict, List, Any
import json

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from services.data_service import DataService
from core.enums import DataCategory, StockMovementType

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def fix_units_by_type(dry_run: bool = True):
    """
    根据业务类型为库存记录打单位标签。
    不修改 quantity 数值，只修改/新增 unit 字段。
    """
    logger.info(f"开始根据业务类型修复单位标签 (Dry Run: {dry_run})...")
    
    ds = DataService()
    data = ds.load_data()
    
    inventory_records = data.get(DataCategory.INVENTORY_RECORDS.value, [])
    product_records = data.get(DataCategory.PRODUCT_INVENTORY_RECORDS.value, [])
    
    total_fixed = 0

    def process_records(records, label):
        nonlocal total_fixed
        count = 0
        for r in records:
            rtype = r.get("type")
            old_unit = r.get("unit")
            new_unit = None
            
            # Rule 1: 成品/发货侧 -> ton
            if rtype in [StockMovementType.PRODUCE_IN.value, StockMovementType.SHIP_OUT.value]:
                new_unit = "ton"
            
            # Rule 2: 原材料/消耗侧 -> kg
            elif rtype in [StockMovementType.CONSUME_OUT.value, StockMovementType.RETURN_IN.value]:
                new_unit = "kg"
            
            # Rule 3: 其他 (ADJUST 等) -> 跳过
            else:
                continue
                
            if old_unit != new_unit:
                if dry_run:
                    logger.info(f"[{label}] ID {r.get('id')} ({rtype}): {old_unit or 'None'} -> {new_unit}")
                r["unit"] = new_unit
                count += 1
                total_fixed += 1
        return count

    fixed_inv = process_records(inventory_records, "原材料记录")
    fixed_prod = process_records(product_records, "成品记录")
    
    logger.info(f"\n扫描完成：")
    logger.info(f"- 原材料记录修复: {fixed_inv}")
    logger.info(f"- 成品记录修复: {fixed_prod}")
    logger.info(f"- 总计修复: {total_fixed}")
    
    if total_fixed > 0 and not dry_run:
        logger.info("正在保存修改...")
        if ds.save_data(data):
            logger.info("保存成功。")
        else:
            logger.error("保存失败。")
    elif dry_run:
        logger.info("\n注意：当前为预览模式，未保存任何更改。请使用 --run 参数执行实际修复。")

if __name__ == "__main__":
    is_dry_run = True
    if len(sys.argv) > 1 and sys.argv[1] == "--run":
        is_dry_run = False
        
    fix_units_by_type(dry_run=is_dry_run)
