import sys
import os
import logging
from collections import defaultdict
from typing import Dict, List, Any

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from services.data_service import DataService
from core.enums import DataCategory, StockMovementType

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def diagnose_cancellations():
    """
    诊断脚本：排查生产领料与撤销过程中的数据异常。
    """
    logger.info("=" * 60)
    logger.info("🔍 开始诊断：生产单领料与撤销异常排查")
    logger.info("=" * 60)
    
    ds = DataService()
    data = ds.load_data()
    
    raw_materials = data.get(DataCategory.RAW_MATERIALS.value, [])
    mat_map = {m.get("id"): m.get("name") for m in raw_materials}
    
    # 1. 收集记录
    # 原材料侧
    inv_records = data.get(DataCategory.INVENTORY_RECORDS.value, [])
    # 成品/半成品侧
    prod_inv_records = data.get(DataCategory.PRODUCT_INVENTORY_RECORDS.value, [])
    
    # 2. 分组记录 (按 Related Doc ID 或 Order ID)
    # key: (doc_id, order_id), value: { "issues": [], "returns": [] }
    # 考虑到有些记录可能只有 doc_id 或只有 order_id，我们使用一个复合 Key
    chains = defaultdict(lambda: {"issues": [], "returns": []})
    
    def process_records(records, is_product=False):
        for r in records:
            rtype = r.get("type")
            doc_id = r.get("related_doc_id")
            order_id = r.get("related_order_id")
            
            # 只有领料和撤销才进入诊断
            if rtype not in [StockMovementType.CONSUME_OUT.value, StockMovementType.RETURN_IN.value]:
                continue
                
            # 标记物料名
            if is_product:
                r["_item_name"] = r.get("product_name", "Unknown Product")
            else:
                mid = r.get("material_id")
                r["_item_name"] = mat_map.get(mid, f"Unknown Material(ID:{mid})")
            
            # 归类
            # 优先使用 related_doc_id (领料单ID) 作为分组依据
            group_key = doc_id if doc_id else f"order_{order_id}"
            
            if rtype == StockMovementType.CONSUME_OUT.value:
                chains[group_key]["issues"].append(r)
            else:
                chains[group_key]["returns"].append(r)

    process_records(inv_records, is_product=False)
    process_records(prod_inv_records, is_product=True)
    
    # 3. 分析并打印报告
    anomaly_count = 0
    total_chains = 0
    
    for group_id, content in chains.items():
        issues = content["issues"]
        returns = content["returns"]
        
        if not issues and not returns:
            continue
            
        total_chains += 1
        
        # 如果有撤销但没有领料记录，或者有领料但没有撤销（且涉及撤销业务），打印出来
        # 这里重点看“有撤销”的链条
        if not returns:
            continue
            
        logger.info(f"\n📄 业务链条: [单据ID/Key: {group_id}]")
        
        # 记录已处理的物料对，防止重复分析
        processed_items = set()
        
        # 尝试按物料配对
        all_items = set([r["_item_name"] for r in issues] + [r["_item_name"] for r in returns])
        
        for item_name in all_items:
            item_issues = [r for r in issues if r["_item_name"] == item_name]
            item_returns = [r for r in returns if r["_item_name"] == item_name]
            
            issue_qty = sum(float(r.get("quantity", 0.0)) for r in item_issues)
            return_qty = sum(float(r.get("quantity", 0.0)) for r in item_returns)
            
            issue_units = set([r.get("unit") for r in item_issues])
            return_units = set([r.get("unit") for r in item_returns])
            
            has_anomaly = False
            anomaly_msgs = []
            
            # 异常 1: 数量不匹配
            if abs(issue_qty - return_qty) > 1e-4:
                has_anomaly = True
                anomaly_msgs.append(f"❌ 数量不匹配: 领料 {issue_qty} vs 撤销 {return_qty}")
            
            # 异常 2: 单位不一致
            if issue_units != return_units:
                has_anomaly = True
                anomaly_msgs.append(f"⚠️ 单位不一致: 领料 {list(issue_units)} vs 撤销 {list(return_units)}")
            
            # 异常 3: 数值过小 (疑似单位错误)
            for r in item_issues:
                qty = float(r.get("quantity", 0.0))
                unit = r.get("unit")
                # 原材料侧（不是 product），且数量 < 10 且 unit 不是 kg
                is_prod_record = "product_name" in r
                if not is_prod_record and qty < 10.0 and unit != "kg":
                    has_anomaly = True
                    anomaly_msgs.append(f"💡 疑似单位错误: 领料 ID {r.get('id')} 数量为 {qty}, 但单位标记为 {unit or 'None'}")

            # 打印详细对比
            prefix = "  [!] " if has_anomaly else "  [✓] "
            logger.info(f"{prefix}物料: {item_name}")
            
            for r in item_issues:
                logger.info(f"      - 领料: ID={r.get('id')}, 日期={r.get('date')}, 数量={r.get('quantity')}, 单位={r.get('unit')}")
            for r in item_returns:
                logger.info(f"      - 撤销: ID={r.get('id')}, 日期={r.get('date')}, 数量={r.get('quantity')}, 单位={r.get('unit')}")
            
            if has_anomaly:
                anomaly_count += 1
                for msg in anomaly_msgs:
                    logger.info(f"        >>> {msg}")

    logger.info("\n" + "=" * 60)
    logger.info(f"📊 诊断总结:")
    logger.info(f"- 扫描业务链条总数: {total_chains}")
    logger.info(f"- 发现异常物料对: {anomaly_count}")
    logger.info("=" * 60)

if __name__ == "__main__":
    diagnose_cancellations()
