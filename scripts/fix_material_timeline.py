import sys
import os
import logging
import argparse
from datetime import datetime
from typing import Dict, List, Any, Tuple

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from services.data_service import DataService
from core.enums import DataCategory, StockMovementType

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def fix_material_timeline(material_keyword: str, start_time_str: str, run: bool = False, delete_mode: bool = False):
    """
    针对特定物料在特定时间点之后的数据进行精准修复或删除。
    """
    logger.info("=" * 60)
    logger.info(f"🚀 开始时间轴精准修复")
    logger.info(f"- 目标物料: {material_keyword}")
    logger.info(f"- 起始时间: {start_time_str}")
    logger.info(f"- 模式: {'删除模式 (DELETE)' if delete_mode else '修复模式 (FIX)'}")
    logger.info(f"- 执行状态: {'正式执行' if run else '预览模式'}")
    logger.info("=" * 60)

    ds = DataService()
    data = ds.load_data()
    
    # 1. 查找物料 ID
    raw_materials = data.get(DataCategory.RAW_MATERIALS.value, [])
    target_material = None
    for m in raw_materials:
        if material_keyword in m.get("name", ""):
            target_material = m
            break
            
    if not target_material:
        logger.error(f"❌ 未找到包含关键字 '{material_keyword}' 的物料。")
        return
        
    mat_id = target_material.get("id")
    mat_name = target_material.get("name")
    logger.info(f"✅ 定位物料: {mat_name} (ID: {mat_id})")

    # 2. 分类记录
    all_records = data.get(DataCategory.INVENTORY_RECORDS.value, [])
    before_records = []
    after_records = []
    
    try:
        cutoff_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        logger.error("❌ 时间格式错误，请使用 'YYYY-MM-DD HH:MM:SS' 格式。")
        return

    for r in all_records:
        if r.get("material_id") != mat_id:
            continue
            
        # 优先使用 created_at，如果没有则尝试使用 date
        r_time_str = r.get("created_at") or r.get("date")
        if not r_time_str:
            continue
            
        try:
            # 尝试解析多种可能的格式
            if len(r_time_str) == 10: # YYYY-MM-DD
                r_time = datetime.strptime(r_time_str, "%Y-%m-%d")
            else:
                r_time = datetime.strptime(r_time_str, "%Y-%m-%d %H:%M:%S")
        except:
            continue
            
        if r_time >= cutoff_time:
            after_records.append(r)
        else:
            before_records.append(r)

    # 3. 计算基准库存 (Cutoff Time 之前的库存)
    # 注意：这里需要根据业务类型累加/扣减
    base_balance = 0.0
    for r in before_records:
        qty = float(r.get("quantity", 0.0))
        rtype = r.get("type")
        
        # 之前的逻辑可能已经有单位了，但为了准确，我们这里简单计算
        # 如果需要更精确，可以引入单位换算逻辑，但对于“基准”我们假设它是正确的
        if rtype in [StockMovementType.IN.value, StockMovementType.RETURN_IN.value, 
                     StockMovementType.PRODUCE_IN.value, StockMovementType.ADJUST_IN.value]:
            base_balance += qty
        else:
            base_balance -= qty
            
    logger.info(f"📈 时间点之前的基准库存: {base_balance:.4f} (基于历史累加)")
    logger.info(f"🔍 发现时间窗内记录数: {len(after_records)}")

    if not after_records:
        logger.info("✨ 未发现需要修复的记录。")
        return

    # 4. 诊断与修复/删除
    logger.info("\n详细记录清单:")
    records_to_save = []
    ids_to_remove = set()
    
    total_qty_change = 0.0
    
    for r in after_records:
        rid = r.get("id")
        rtype = r.get("type")
        qty = float(r.get("quantity", 0.0))
        unit = r.get("unit")
        time = r.get("created_at") or r.get("date")
        
        status_msg = ""
        
        if delete_mode:
            status_msg = " [拟删除]"
            ids_to_remove.add(rid)
        else:
            # 修复逻辑
            new_unit = "kg"
            new_qty = qty
            
            # 关键逻辑：如果标记为 ton，或者数值小于 10 且是消耗/退料类，则放大 1000 倍
            needs_magnification = False
            if unit == "ton":
                needs_magnification = True
            elif qty < 10.0 and rtype in [StockMovementType.CONSUME_OUT.value, StockMovementType.RETURN_IN.value]:
                needs_magnification = True
                
            if needs_magnification:
                new_qty = qty * 1000.0
                status_msg = f" [修正: {qty} -> {new_qty}, 单位: {unit or 'None'} -> kg]"
            else:
                status_msg = f" [仅修正单位: {unit or 'None'} -> kg]"
            
            if run:
                r["unit"] = new_unit
                r["quantity"] = new_qty
                # 如果有 snapshot_stock，也需要标记为脏，或者重新计算（这里我们依赖 recalculate 脚本）
                
        logger.info(f"  - ID: {rid} | 时间: {time} | 类型: {rtype} | 数量: {qty} | 单位: {unit}{status_msg}")

    # 5. 执行保存
    if run:
        logger.info("\n正在创建备份...")
        ds.create_backup()
        
        if delete_mode:
            # 移除记录
            data[DataCategory.INVENTORY_RECORDS.value] = [r for r in all_records if r.get("id") not in ids_to_remove]
            logger.info(f"已从数据库中移除 {len(ids_to_remove)} 条记录。")
        else:
            # 修复模式下，after_records 是直接在 data 里的引用，所以已经修改了
            logger.info(f"已在内存中完成 {len(after_records)} 条记录的修正。")
            
        if ds.save_data(data):
            logger.info("✅ 数据保存成功！")
            logger.info("💡 请务必运行 'python scripts/recalculate_stock.py --run' 以同步物料表库存。")
        else:
            logger.error("❌ 数据保存失败。")
    else:
        logger.info("\n提示: 当前为预览模式。如需执行修改，请增加 '--run' 参数。")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="物料时间轴精准修复脚本")
    parser.add_argument("--material", default="六碳聚醚大单体", help="物料名称关键字")
    parser.add_argument("--start-time", default="2026-01-13 20:53:45", help="起始时间 (YYYY-MM-DD HH:MM:SS)")
    parser.add_argument("--run", action="store_true", help="确认执行保存")
    parser.add_argument("--delete", action="store_true", help="启用删除模式")
    
    args = parser.parse_args()
    
    fix_material_timeline(
        material_keyword=args.material,
        start_time_str=args.start_time,
        run=args.run,
        delete_mode=args.delete
    )
