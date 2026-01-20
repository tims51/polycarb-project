import logging
import pandas as pd
from datetime import datetime, date
from typing import List, Dict, Any, Tuple, Optional, Union

from core.enums import DataCategory, IssueStatus, StockMovementType, UnitType, MaterialType, ProductCategory
from services.data_service import DataService
from utils.unit_helper import convert_quantity, normalize_unit

logger = logging.getLogger(__name__)

class InventoryService:
    def __init__(self, data_service: DataService = None):
        self.data_service = data_service or DataService()

    def get_stock_balance(self, material_id: Optional[int] = None) -> Union[float, Dict[int, float]]:
        """获取原材料库存余额"""
        return self.data_service.get_stock_balance(material_id)

    # ------------------ Product Inventory Methods (For UI) ------------------

    def get_products(self) -> List[Dict[str, Any]]:
        """获取所有成品信息"""
        return self.data_service.get_product_inventory()

    def get_inventory_summary(self, low_stock_threshold: float = 10.0) -> Dict[str, Any]:
        """获取成品库存概览（用于看板）"""
        products = self.get_products()
        total_stock = sum(float(p.get("stock_quantity", 0.0) or p.get("current_stock", 0.0)) for p in products)
        product_count = len(products)
        
        low_stock_items = []
        stock_dist = []
        
        for p in products:
            qty = float(p.get("stock_quantity", 0.0) or p.get("current_stock", 0.0))
            name = p.get("product_name") or p.get("name")
            
            if qty < low_stock_threshold:
                low_stock_items.append({
                    "product_name": name,
                    "type": p.get("type"),
                    "current_stock": qty,
                    "unit": p.get("unit", "吨")
                })
            
            stock_dist.append({
                "product_name": name,
                "current_stock": qty,
                "type": p.get("type")
            })
            
        return {
            "total_stock": total_stock,
            "product_count": product_count,
            "low_stock_items": low_stock_items,
            "stock_distribution": pd.DataFrame(stock_dist) if stock_dist else pd.DataFrame(columns=["product_name", "current_stock", "type"])
        }

    def process_inbound(self, product_name: str, product_type: str, quantity: float, batch_no: str, operator: str, date_str: str) -> Tuple[bool, str]:
        """处理成品入库"""
        record = {
            "product_name": product_name,
            "product_type": product_type,
            "type": StockMovementType.PRODUCE_IN.value, 
            "quantity": quantity,
            "reason": f"手动入库: {batch_no}",
            "operator": operator,
            "date": date_str,
            "batch_number": batch_no
        }
        return self.data_service.add_product_inventory_record(record)

    def process_outbound(self, product_name: str, quantity: float, customer: str, remark: str, operator: str, date_str: str) -> Tuple[bool, str]:
        """处理成品出库"""
        record = {
            "product_name": product_name,
            "type": StockMovementType.OUT.value,
            "quantity": quantity,
            "reason": f"销售出库: {customer} {remark}",
            "operator": operator,
            "date": date_str,
            "related_doc_type": "SHIPPING"
        }
        return self.data_service.add_product_inventory_record(record)

    def calibrate_stock(self, product_name: str, actual_stock: float, reason: str, operator: str) -> Tuple[bool, str]:
        """校准成品库存"""
        products = self.get_products()
        target = next((p for p in products if (p.get("product_name") or p.get("name")) == product_name), None)
        
        if not target:
            return False, "产品不存在"
        
        current = float(target.get("stock_quantity", 0.0) or target.get("current_stock", 0.0))
        diff = actual_stock - current
        
        if abs(diff) < 1e-6:
            return True, "无差异"
        
        rtype = StockMovementType.ADJUST_IN.value if diff > 0 else StockMovementType.ADJUST_OUT.value
        qty = abs(diff)
        
        record = {
            "product_name": product_name,
            "type": rtype,
            "quantity": qty,
            "reason": f"库存校准: {reason} (账面: {current} -> 实盘: {actual_stock})",
            "operator": operator,
            "date": datetime.now().strftime("%Y-%m-%d")
        }
        return self.data_service.add_product_inventory_record(record)

    def get_inventory_history(self, start_date: date, end_date: date, product_type: str, search_term: str) -> pd.DataFrame:
        """获取成品库存历史记录"""
        records = self.data_service.get_product_inventory_records()
        
        # Filter
        filtered = []
        s_str = start_date.strftime("%Y-%m-%d")
        e_str = end_date.strftime("%Y-%m-%d")
        
        for r in records:
            r_date = r.get("date", "")
            if not (s_str <= r_date <= e_str):
                continue
                
            if product_type != "全部" and product_type != "All":
                 if r.get("product_type") != product_type:
                     continue
            
            if search_term:
                term = search_term.lower()
                if (term not in str(r.get("product_name", "")).lower() and 
                    term not in str(r.get("reason", "")).lower() and 
                    term not in str(r.get("batch_number", "")).lower()):
                    continue
            
            filtered.append(r)
            
        return pd.DataFrame(filtered) if filtered else pd.DataFrame()

    # ------------------ Issue / Raw Material Methods ------------------

    def post_issue(self, issue_id: int, operator: str = "System") -> Tuple[bool, str]:
        """
        领料过账
        委托给 DataService，但保留此处的逻辑层（如果有额外业务校验）
        目前 DataService.post_issue 已经包含了完整逻辑，直接调用即可。
        """
        return self.data_service.post_issue(issue_id, operator)

    def cancel_issue_posting(self, issue_id: int, operator: str = "System") -> Tuple[bool, str]:
        """
        撤销领料过账
        """
        # DataService 没有 cancel_issue_posting？
        # 我之前的 Read output 显示 DataService 没有 cancel_issue_posting。
        # 也就是这个逻辑必须保留在 Service 层，或者迁移到 DataService。
        # 原来的 DataManager 有，现在我要么把 DataManager 的逻辑搬到 DataService，要么在这里实现。
        # 这里是 InventoryService，处理库存回滚是合适的。
        # 但 InventoryService.cancel_issue_posting 在之前的 Read 中是有的。
        # 所以我必须保留它。
        
        # Wait, if I overwrite this file, I need to make sure I include the existing logic for cancel_issue_posting!
        # The previous Read output for InventoryService ALREADY had the full implementation of cancel_issue_posting.
        # So I should copy that logic back in.
        
        # Since I am rewriting the file, I need to include the previously read logic.
        # I will paste the logic from the previous Read.
        
        data = self.data_service.load_data()
        issues = data.get(DataCategory.MATERIAL_ISSUES.value, [])
        orders = data.get(DataCategory.PRODUCTION_ORDERS.value, [])
        products = data.get(DataCategory.PRODUCT_INVENTORY.value, [])
        product_records = data.get(DataCategory.PRODUCT_INVENTORY_RECORDS.value, [])
        
        target_issue = None
        for issue in issues:
            if issue.get("id") == issue_id:
                target_issue = issue
                break
        
        if not target_issue: return False, "领料单不存在"
        if target_issue.get("status") != IssueStatus.POSTED.value: return False, "只有已过账的领料单可以撤销"
        
        records = data.get(DataCategory.INVENTORY_RECORDS.value, [])
        materials = data.get(DataCategory.RAW_MATERIALS.value, [])
        
        for line in target_issue.get("lines", []):
            qty = float(line.get("required_qty", 0.0))
            if qty <= 0: continue
            
            mid = line.get("item_id")
            line_uom = line.get("uom", UnitType.KG.value)
            item_type = line.get("item_type", MaterialType.RAW_MATERIAL.value)
            
            if item_type == MaterialType.PRODUCT.value:
                prod_idx = -1
                current_stock = 0.0
                expected_name = str(line.get("item_name", "") or "").strip()
                
                # 简化逻辑，优先匹配ID
                for idx, p in enumerate(products):
                    if p.get("id") == mid:
                        prod_idx = idx
                        current_stock = float(p.get("stock_quantity", 0.0))
                        break
                
                if prod_idx == -1 and expected_name:
                    for idx, p in enumerate(products):
                        if str(p.get("name", "") or "").strip() == expected_name:
                            prod_idx = idx
                            current_stock = float(p.get("stock_quantity", 0.0))
                            break
                            
                if prod_idx >= 0:
                    stock_unit = products[prod_idx].get("unit", UnitType.TON.value)
                    final_qty, success = convert_quantity(qty, line_uom, stock_unit)
                    
                    new_stock = current_stock + final_qty
                    products[prod_idx]["stock_quantity"] = new_stock
                    products[prod_idx]["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    reason_note = f"撤销领料: {target_issue.get('issue_code')}"
                    if normalize_unit(line_uom) != normalize_unit(stock_unit):
                        reason_note += f" (原: {qty}{line_uom})"
                    
                    # Safe ID generation
                    new_rec_id = self.data_service._get_next_id(product_records)
                    
                    rel_order_id = target_issue.get("production_order_id")
                    rel_bom_id = None
                    rel_bom_ver = None
                    if rel_order_id:
                        ord_obj = next((o for o in orders if o.get("id") == rel_order_id), None)
                        if ord_obj:
                            rel_bom_id = ord_obj.get("bom_id")
                            rel_bom_ver = ord_obj.get("bom_version_id")

                    product_records.append({
                        "id": new_rec_id,
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "product_name": products[prod_idx].get("name"),
                        "product_type": products[prod_idx].get("type", "其他"),
                        "type": StockMovementType.RETURN_IN.value,
                        "quantity": final_qty,
                        "reason": reason_note,
                        "operator": operator,
                        "snapshot_stock": new_stock,
                        "related_doc_type": "ISSUE_CANCEL",
                        "related_doc_id": issue_id,
                        "related_order_id": rel_order_id,
                        "related_bom_id": rel_bom_id,
                        "related_bom_version_id": rel_bom_ver
                    })
            else:
                mat_idx = -1
                current_stock = 0.0
                is_water = False
                
                for idx, m in enumerate(materials):
                    if m.get("id") == mid:
                        current_stock = float(m.get("stock_quantity", 0.0))
                        mat_name = m.get("name", "").strip()
                        # Use alias list from DataService or define here
                        # Simpler to hardcode or import
                        is_water = mat_name in ["水", "自来水", "纯水", "去离子水", "工业用水", "生产用水"]
                        mat_idx = idx
                        break
                
                if mat_idx >= 0:
                    stock_unit = materials[mat_idx].get("unit", UnitType.KG.value)
                    final_qty, success = convert_quantity(qty, line_uom, stock_unit)
                    
                    new_stock = current_stock
                    if not is_water:
                        new_stock = current_stock + final_qty
                        materials[mat_idx]["stock_quantity"] = new_stock
                        materials[mat_idx]["last_stock_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    reason_note = f"撤销领料: {target_issue.get('issue_code')}"
                    if normalize_unit(line_uom) != normalize_unit(stock_unit):
                        reason_note += f" (原: {qty}{line_uom})"
                    
                    # Safe ID generation
                    new_rec_id = self.data_service._get_next_id(records)
                    
                    records.append({
                        "id": new_rec_id,
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "material_id": mid,
                        "type": StockMovementType.RETURN_IN.value,
                        "quantity": final_qty,
                        "reason": reason_note,
                        "operator": operator,
                        "related_doc_type": "ISSUE_CANCEL",
                        "related_doc_id": issue_id,
                        "snapshot_stock": new_stock
                    })
        
        target_issue["status"] = IssueStatus.DRAFT.value
        target_issue["last_modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Mark previous OUT records as cancelled
        for r in product_records:
            if (r.get("type") == StockMovementType.OUT.value or r.get("type") == StockMovementType.CONSUME_OUT.value) \
               and r.get("related_doc_type") == "ISSUE" \
               and r.get("related_doc_id") == issue_id:
                r["related_doc_type"] = "ISSUE_CANCEL"
                if r.get("reason"):
                    r["reason"] = f"{r['reason']} (已撤销)"
                else:
                    r["reason"] = "生产领料出库 (已撤销)"
        
        data["inventory_records"] = records
        data["raw_materials"] = materials
        data["product_inventory"] = products
        data["product_inventory_records"] = product_records
        
        if self.data_service.save_data(data):
            return True, "撤销成功，库存已恢复"
        return False, "保存失败"
