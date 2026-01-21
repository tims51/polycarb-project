import sys
import os
import logging
import argparse
from datetime import datetime
from typing import Dict, List, Any, Tuple

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from services.data_service import DataService
from core.enums import DataCategory, StockMovementType, MaterialType

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def rebuild_ledger(run: bool = False):
    """
    重构脚本：清空当前库存流水，根据源单据重新生成。
    """
    logger.info("=" * 60)
    logger.info("🛠️ 开始执行账本彻底重构")
    logger.info(f"执行模式: {'正式执行' if run else '预览模式'}")
    logger.info("=" * 60)
    
    logger.warning("⚠️ 警告：手动盘点记录 (ADJUST) 将会丢失，因为它们没有源单据支撑。")
    
    ds = DataService()
    data = ds.load_data()
    
    if run:
        logger.info("正在创建安全备份...")
        ds.create_backup()

    # --- 1. 清零阶段 ---
    logger.info("\n[1/5] 清零阶段 (Reset)...")
    
    raw_materials = data.get(DataCategory.RAW_MATERIALS.value, [])
    for m in raw_materials:
        m["stock_quantity"] = 0.0
        m["last_stock_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
    product_inventory = data.get(DataCategory.PRODUCT_INVENTORY.value, [])
    for p in product_inventory:
        p["stock_quantity"] = 0.0
        if "current_stock" in p:
            p["current_stock"] = 0.0
        p["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
    # 清空流水
    data[DataCategory.INVENTORY_RECORDS.value] = []
    data[DataCategory.PRODUCT_INVENTORY_RECORDS.value] = []
    
    inv_records = data[DataCategory.INVENTORY_RECORDS.value]
    prod_records = data[DataCategory.PRODUCT_INVENTORY_RECORDS.value]
    
    # 辅助工具：获取下一个 ID
    def get_next_inv_id():
        return len(inv_records) + 1
    def get_next_prod_id():
        return len(prod_records) + 1

    # 建立 BOM 映射
    boms = data.get("boms", [])
    bom_map = {}
    for b in boms:
        # 拼接产品名称，如 ST-60A
        full_name = f"{b.get('bom_code')}-{b.get('bom_name')}"
        bom_map[b.get("id")] = full_name

    # --- 2. 重放：原材料入库 (Replay Raw Material In) ---
    logger.info("[2/5] 重放：原材料入库 (Goods Receipts)...")
    goods_receipts = data.get(DataCategory.GOODS_RECEIPTS.value, [])
    gr_count = 0
    for gr in goods_receipts:
        if gr.get("status") not in ["completed", "received"]:
            continue
            
        for item in gr.get("items", []):
            mid = item.get("material_id")
            qty = float(item.get("quantity", 0.0))
            
            # 强制规则：如果数量很小且没有明确单位，或者 remark 提示是吨，则 * 1000
            # 这里简单判断：如果数量 < 100 且物料是原材料，极大概率是吨
            remark = item.get("remark", "").lower()
            if qty < 100.0 or "ton" in remark or "吨" in remark:
                qty *= 1000.0
                
            inv_records.append({
                "id": get_next_inv_id(),
                "material_id": mid,
                "type": StockMovementType.IN.value,
                "quantity": qty,
                "unit": "kg",
                "reason": f"采购入库 (单号: {gr.get('receipt_code')})",
                "date": gr.get("date"),
                "created_at": gr.get("created_at"),
                "related_doc_type": "GOODS_RECEIPT",
                "related_doc_id": gr.get("id")
            })
            
            # 更新库存
            for m in raw_materials:
                if m["id"] == mid:
                    m["stock_quantity"] += qty
                    break
            gr_count += 1
    logger.info(f"   - 已重放 {gr_count} 条入库明细。")

    # --- 3. 重放：生产消耗 (Replay Consumption) ---
    logger.info("[3/5] 重放：生产消耗 (Material Issues)...")
    material_issues = data.get(DataCategory.MATERIAL_ISSUES.value, [])
    issue_count = 0
    for issue in material_issues:
        if issue.get("status") != "posted":
            continue
            
        for line in issue.get("lines", []):
            item_id = line.get("item_id")
            item_type = line.get("item_type", MaterialType.RAW_MATERIAL.value)
            qty = float(line.get("required_qty", 0.0))
            
            if item_type == MaterialType.PRODUCT.value:
                # 扣减成品库存 (基准: 吨)
                # 如果单据上是 kg，则 / 1000
                if line.get("uom") == "kg":
                    qty /= 1000.0
                    
                prod_records.append({
                    "id": get_next_prod_id(),
                    "product_name": line.get("item_name"),
                    "type": StockMovementType.CONSUME_OUT.value,
                    "quantity": qty,
                    "unit": "ton",
                    "reason": f"生产领料 (单号: {issue.get('issue_code')})",
                    "date": issue.get("posted_at", "").split(" ")[0],
                    "created_at": issue.get("posted_at"),
                    "related_doc_type": "MATERIAL_ISSUE",
                    "related_doc_id": issue.get("id")
                })
                # 更新库存
                for p in product_inventory:
                    if p.get("id") == item_id or p.get("product_name") == line.get("item_name"):
                        p["stock_quantity"] -= qty
                        if "current_stock" in p: p["current_stock"] -= qty
                        break
            else:
                # 扣减原材料库存 (基准: kg)
                inv_records.append({
                    "id": get_next_inv_id(),
                    "material_id": item_id,
                    "type": StockMovementType.CONSUME_OUT.value,
                    "quantity": qty,
                    "unit": "kg",
                    "reason": f"生产领料 (单号: {issue.get('issue_code')})",
                    "date": issue.get("posted_at", "").split(" ")[0],
                    "created_at": issue.get("posted_at"),
                    "related_doc_type": "MATERIAL_ISSUE",
                    "related_doc_id": issue.get("id")
                })
                # 更新库存
                for m in raw_materials:
                    if m["id"] == item_id:
                        m["stock_quantity"] -= qty
                        break
            issue_count += 1
    logger.info(f"   - 已重放 {issue_count} 条领料明细。")

    # --- 4. 重放：生产产出 (Replay Production) ---
    logger.info("[4/5] 重放：生产产出 (Production Orders)...")
    production_orders = data.get(DataCategory.PRODUCTION_ORDERS.value, [])
    prod_order_count = 0
    for order in production_orders:
        if order.get("status") != "finished":
            continue
            
        qty = float(order.get("actual_quantity") or order.get("plan_qty") or 0.0)
        # 强制规则：如果数量 > 100 且单位是成品，极大概率原单填的是 kg
        if qty > 100.0:
            qty /= 1000.0
            
        p_name = order.get("product_name") or bom_map.get(order.get("bom_id"))
        if not p_name:
            logger.warning(f"     [跳过] 生产订单 {order.get('order_code')} 缺少产品名称且无法通过 BOM 关联。")
            continue
            
        # 查找或创建成品
        target_p = next((p for p in product_inventory if p.get("product_name") == p_name), None)
        if not target_p:
            new_p_id = len(product_inventory) + 1
            target_p = {
                "id": new_p_id,
                "product_name": p_name,
                "stock_quantity": 0.0,
                "unit": "吨"
            }
            product_inventory.append(target_p)
            logger.info(f"     [自动创建成品] {p_name}")

        prod_records.append({
            "id": get_next_prod_id(),
            "product_name": p_name,
            "type": StockMovementType.PRODUCE_IN.value,
            "quantity": qty,
            "unit": "ton",
            "reason": f"生产完工 (单号: {order.get('order_code')})",
            "date": order.get("finished_at", "").split(" ")[0],
            "created_at": order.get("finished_at"),
            "related_doc_type": "PRODUCTION_ORDER",
            "related_doc_id": order.get("id")
        })
        # 更新库存
        target_p["stock_quantity"] += qty
        if "current_stock" in target_p: target_p["current_stock"] += qty
        prod_order_count += 1
    logger.info(f"   - 已重放 {prod_order_count} 个生产订单。")

    # --- 5. 重放：发货出库 (Replay Shipping) ---
    logger.info("[5/5] 重放：发货出库 (Shipping Orders)...")
    shipping_orders = data.get(DataCategory.SHIPPING_ORDERS.value, [])
    ship_count = 0
    for ship in shipping_orders:
        if ship.get("status") not in ["shipped", "completed"]:
            continue
            
        for item in ship.get("items", []):
            p_name = item.get("product_name")
            qty = float(item.get("quantity", 0.0))
            
            # 强制规则：如果数量 > 100，极大概率是 kg
            if qty > 100.0:
                qty /= 1000.0
                
            prod_records.append({
                "id": get_next_prod_id(),
                "product_name": p_name,
                "type": StockMovementType.SHIP_OUT.value,
                "quantity": qty,
                "unit": "ton",
                "reason": f"销售发货 (单号: {ship.get('shipping_code')})",
                "date": ship.get("date"),
                "created_at": ship.get("created_at"),
                "related_doc_type": "SHIPPING_ORDER",
                "related_doc_id": ship.get("id")
            })
            
            # 更新库存
            for p in product_inventory:
                if p.get("product_name") == p_name:
                    p["stock_quantity"] -= qty
                    if "current_stock" in p: p["current_stock"] -= qty
                    break
            ship_count += 1
    logger.info(f"   - 已重放 {ship_count} 条发货明细。")

    # --- 总结与保存 ---
    logger.info("\n" + "=" * 60)
    logger.info("🏁 重构完成！")
    logger.info(f"- 生成原材料流水: {len(inv_records)} 条")
    logger.info(f"- 生成成品流水: {len(prod_records)} 条")
    
    if run:
        logger.info("正在保存结果到数据库...")
        if ds.save_data(data):
            logger.info("✅ 账本重构成功！所有库存已根据源单据对齐。")
        else:
            logger.error("❌ 保存失败。")
    else:
        logger.info("\n注意：当前为预览模式，未写入文件。")
        logger.info("确认逻辑无误后，请执行: python scripts/rebuild_ledger.py --run")
    logger.info("=" * 60)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="账本重构脚本")
    parser.add_argument("--run", action="store_true", help="执行保存操作")
    args = parser.parse_args()
    
    rebuild_ledger(run=args.run)
