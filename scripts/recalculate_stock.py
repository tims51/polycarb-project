import sys
import os
import logging
from datetime import datetime

# 将 src 目录添加到模块搜索路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from services.data_service import DataService
from services.inventory_service import InventoryService
from core.enums import DataCategory

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def recalculate_all_stocks(run: bool = False):
    """
    重新计算所有物料的库存数量并更新到原材料表中。
    """
    logger.info(f"开始重新计算库存 (执行模式: {'正式' if run else '预览'})...")
    
    ds = DataService()
    inv_service = InventoryService(data_service=ds)
    
    # 1. 获取最新计算的余额字典 (已包含单位换算逻辑)
    balances = inv_service.get_stock_balance()
    
    # 2. 加载原始数据进行更新
    data = ds.load_data()
    materials = data.get(DataCategory.RAW_MATERIALS.value, [])
    
    update_count = 0
    for mat in materials:
        mat_id = mat.get("id")
        old_stock = float(mat.get("stock_quantity", 0.0))
        new_stock = float(balances.get(mat_id, 0.0))
        
        if abs(old_stock - new_stock) > 1e-6:
            logger.info(f"物料 ID {mat_id} ({mat.get('name')}): {old_stock} -> {new_stock}")
            mat["stock_quantity"] = new_stock
            mat["last_stock_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            update_count += 1
            
    if update_count == 0:
        logger.info("所有物料库存均已是最新，无需更新。")
        return

    logger.info(f"\n共发现 {update_count} 个物料需要更新。")
    
    if run:
        logger.info("正在保存更新到数据库...")
        if ds.save_data(data):
            logger.info("库存更新成功！")
        else:
            logger.error("保存失败，请检查文件权限。")
    else:
        logger.info("\n注意：当前为预览模式，未对数据库进行实际修改。")
        logger.info("如需正式更新，请运行: python scripts/recalculate_stock.py --run")

if __name__ == "__main__":
    is_run = len(sys.argv) > 1 and sys.argv[1] == "--run"
    recalculate_all_stocks(run=is_run)
