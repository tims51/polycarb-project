import sys
import os
import logging
from typing import Dict, List, Any, Tuple
import json

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from services.data_service import DataService
from core.enums import DataCategory, StockMovementType, UnitType

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def tag_inventory_units(dry_run: bool = True):
    """
    清洗库存记录，根据业务类型补全单位标记。
    目标是解决计算混乱，但不修改用户输入的原始数字。
    """
    logger.info(f"开始执行库存单位补全脚本 (Dry Run: {dry_run})...")
    
    ds = DataService()
    # 强制重新加载数据
    data = ds.load_data()
    
    # 需要处理的记录类别
    categories = [
        (DataCategory.INVENTORY_RECORDS.value, "原材料库存记录 (inventory_records)"),
        (DataCategory.PRODUCT_INVENTORY_RECORDS.value, "成品库存记录 (product_inventory_records)")
    ]
    
    total_processed = 0
    total_updated = 0
    
    for cat_key, cat_name in categories:
        records = data.get(cat_key, [])
        if not records:
            logger.info(f"\n未发现 {cat_name}。")
            continue
            
        logger.info(f"\n正在处理 {cat_name} (共 {len(records)} 条记录)...")
        
        cat_updated = 0
        for record in records:
            total_processed += 1
            rec_type = record.get("type")
            rec_qty = float(record.get("quantity", 0.0))
            old_unit = record.get("unit")
            
            new_unit = None
            log_msg = ""
            
            # 1. SHIP_OUT (发货) 或 PRODUCE_IN (生产入库) -> ton
            if rec_type in [StockMovementType.SHIP_OUT.value, StockMovementType.PRODUCE_IN.value]:
                new_unit = "ton"
                log_msg = f"根据业务类型 [{rec_type}] 标记为 ton"
            
            # 2. CONSUME_OUT (投料消耗) -> kg
            elif rec_type == StockMovementType.CONSUME_OUT.value:
                new_unit = "kg"
                log_msg = f"根据业务类型 [{rec_type}] 标记为 kg"
            
            # 3. 其他类型 (IN, OUT, ADJUSTMENT 等) -> 根据数值判断
            else:
                if abs(rec_qty) < 10.0:
                    new_unit = "ton"
                    log_msg = f"类型 [{rec_type}] 且数量 < 10 ({rec_qty})，标记为 ton"
                else:
                    new_unit = "kg"
                    log_msg = f"类型 [{rec_type}] 且数量 >= 10 ({rec_qty})，标记为 kg"
                
                # 提示人工确认
                logger.info(f"[人工确认提示] 记录 ID {record.get('id')} ({rec_type}): 数量={rec_qty} -> 自动标记为 '{new_unit}'")

            # 如果检测到单位变化或缺失
            if new_unit and old_unit != new_unit:
                record["unit"] = new_unit
                cat_updated += 1
                total_updated += 1
                if dry_run:
                    logger.info(f"  [预修补] ID {record.get('id')}: {old_unit or 'None'} -> {new_unit} ({log_msg})")

        logger.info(f"{cat_name} 处理完毕：更新了 {cat_updated} 条记录。")

    # 总结
    logger.info("\n" + "-" * 50)
    logger.info("任务完成！")
    logger.info(f"扫描记录总数: {total_processed}")
    logger.info(f"建议/执行更新总数: {total_updated}")
    
    if dry_run:
        logger.info("\n注意：当前为预览模式 (Dry Run)，未对数据库进行实际修改。")
        logger.info("如需正式执行，请运行: python scripts/tag_inventory_units.py --run")
    else:
        logger.info("\n正在将修改保存到数据库...")
        if ds.save_data(data):
            logger.info("成功保存单位标记。")
        else:
            logger.error("保存失败！请检查文件权限。")

if __name__ == "__main__":
    is_dry_run = True
    if len(sys.argv) > 1 and sys.argv[1] == "--run":
        is_dry_run = False
        
    tag_inventory_units(dry_run=is_dry_run)
