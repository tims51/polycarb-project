import logging
import pandas as pd
from datetime import datetime, date
from typing import List, Dict, Any, Tuple, Optional, Union

from core.enums import DataCategory, IssueStatus, StockMovementType, UnitType, MaterialType, ProductCategory
from core.constants import WATER_MATERIAL_ALIASES
from services.data_service import DataService
from utils.unit_helper import convert_quantity, normalize_unit, convert_to_base_unit, BASE_UNIT_RAW_MATERIAL, BASE_UNIT_PRODUCT
from schemas.material import InventoryRecord, InventoryRecordCreate

logger = logging.getLogger(__name__)

class InventoryService:
    # 免库存物料列表 (通常是管道接入的水类)
    UNTRACKED_MATERIALS = set(WATER_MATERIAL_ALIASES)

    def __init__(self, data_service: DataService = None):
        self.data_service = data_service or DataService()

    def get_stock_balance(self, material_id: Optional[int] = None) -> Union[float, Dict[int, float]]:
        """获取原材料库存余额（支持单位换算）"""
        data = self.data_service.load_data()
        records = data.get(DataCategory.INVENTORY_RECORDS.value, [])
        materials = data.get(DataCategory.RAW_MATERIALS.value, [])
        
        # 建立物料基础单位映射
        mat_base_units = {m["id"]: m.get("unit", "kg") for m in materials}
        
        def _get_converted_qty(r, mid):
            qty = float(r.get("quantity", 0.0))
            record_unit = r.get("unit")
            base_unit = normalize_unit(mat_base_units.get(mid, "kg"))
            
            if record_unit:
                record_unit = normalize_unit(record_unit)
                if record_unit != base_unit:
                    if record_unit in ["ton", "吨", "t", "tons"] and base_unit in ["kg", "千克", "kgs"]:
                        qty *= 1000.0
                    elif record_unit in ["kg", "千克", "kgs"] and base_unit in ["ton", "吨", "t", "tons"]:
                        qty /= 1000.0
                    else:
                        factor = get_conversion_factor(record_unit, base_unit)
                        if factor:
                            qty *= factor
            return qty

        # 如果指定了 material_id，只计算该物料
        if material_id:
            balance = 0.0
            for r in records:
                if r.get("material_id") == material_id:
                    qty = _get_converted_qty(r, material_id)
                    rtype = r.get("type", "")
                    if rtype in [StockMovementType.IN.value, StockMovementType.PRODUCE_IN.value, 
                                StockMovementType.ADJUST_IN.value, StockMovementType.RETURN_IN.value]:
                        balance += qty
                    elif rtype in [StockMovementType.OUT.value, StockMovementType.CONSUME_OUT.value, 
                                  StockMovementType.ADJUST_OUT.value, StockMovementType.RETURN_OUT.value,
                                  StockMovementType.SHIP_OUT.value]:
                        balance -= qty
            return balance
        
        # 否则返回所有物料的余额字典
        balances = {m["id"]: 0.0 for m in materials}
        for r in records:
            mid = r.get("material_id")
            if mid not in balances: 
                continue
            
            qty = _get_converted_qty(r, mid)
            rtype = r.get("type", "")
            if rtype in [StockMovementType.IN.value, StockMovementType.PRODUCE_IN.value, 
                        StockMovementType.ADJUST_IN.value, StockMovementType.RETURN_IN.value]:
                balances[mid] += qty
            elif rtype in [StockMovementType.OUT.value, StockMovementType.CONSUME_OUT.value, 
                          StockMovementType.ADJUST_OUT.value, StockMovementType.RETURN_OUT.value,
                          StockMovementType.SHIP_OUT.value]:
                balances[mid] -= qty
        return balances

    def check_stock_availability(self, material_name: str, quantity_needed: float, current_stock: float = None) -> bool:
        """
        检查库存是否充足
        对于免库存物料 (如水)，始终返回 True
        """
        if material_name in self.UNTRACKED_MATERIALS:
            return True
            
        if current_stock is None:
            # 如果未提供当前库存，尝试查询 (需要 material_id，但这里只有 name，略显尴尬)
            # 通常调用方会提供 current_stock。如果不提供，暂且假设调用方负责获取。
            # 为了严谨，如果 quantity_needed <= 0，也是 True
            pass
            
        if quantity_needed <= 0:
            return True
            
        if current_stock is not None:
            return current_stock >= quantity_needed
            
        return False # Fallback

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
        # 自动转换为基准单位 (吨)
        # 假设前端传来的是 UI 显示的单位，通常成品就是吨，但这里强制转换确保一致性
        # 如果 UI 没有传单位，这里假设是吨，或者需要 UI 传参。
        # 鉴于 process_inbound 签名没有单位，且系统默认成品为吨，这里先不做额外转换，
        # 或者假设输入就是吨。
        # 但为了符合 "所有成品...强制统一为吨" 的要求，我们显式确认。
        # 如果未来 UI 支持其他单位，这里需要修改签名接受 unit。
        # 目前保持原逻辑，但确保 add_product_inventory_record 内部逻辑正确。
        
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

    def get_stock_snapshot_at_date(self, target_date: str) -> List[Dict[str, Any]]:
        """
        计算所有原材料在 target_date 结束时的理论库存余额
        """
        data = self.data_service.load_data()
        materials = data.get(DataCategory.RAW_MATERIALS.value, [])
        records = data.get(DataCategory.INVENTORY_RECORDS.value, [])
        
        # Initialize snapshot with 0
        snapshot = {m["id"]: 0.0 for m in materials}
        # Material base units map
        mat_base_units = {m["id"]: m.get("unit", "kg") for m in materials}
        
        # Calculate stock based on records up to target_date
        for r in records:
            r_date = r.get("date", "")
            if not r_date or r_date > target_date:
                continue
                
            mid = r.get("material_id")
            if mid not in snapshot:
                continue
            
            # 查找物料名称以检查是否为免库存物料
            mat_obj = next((m for m in materials if m["id"] == mid), None)
            if mat_obj and mat_obj.get("name") in self.UNTRACKED_MATERIALS:
                snapshot[mid] = 0.0 # 始终保持为 0
                continue
                
            qty = float(r.get("quantity", 0.0))
            rtype = r.get("type")
            
            # --- 标准化换算逻辑 ---
            record_unit = r.get("unit")
            base_unit = normalize_unit(mat_base_units.get(mid, "kg"))
            
            if record_unit:
                record_unit = normalize_unit(record_unit)
                if record_unit != base_unit:
                    if record_unit in ["ton", "吨", "t", "tons"] and base_unit in ["kg", "千克", "kgs"]:
                        qty *= 1000.0
                    elif record_unit in ["kg", "千克", "kgs"] and base_unit in ["ton", "吨", "t", "tons"]:
                        qty /= 1000.0
                    else:
                        factor = get_conversion_factor(record_unit, base_unit)
                        if factor:
                            qty *= factor
            
            # Logic: Add or Subtract
            if rtype in [StockMovementType.IN.value, StockMovementType.RETURN_IN.value, 
                         StockMovementType.PRODUCE_IN.value, StockMovementType.ADJUST_IN.value]:
                snapshot[mid] += qty
            elif rtype in [StockMovementType.OUT.value, StockMovementType.RETURN_OUT.value, 
                           StockMovementType.CONSUME_OUT.value, StockMovementType.ADJUST_OUT.value,
                           StockMovementType.SHIP_OUT.value]:
                snapshot[mid] -= qty
                
        # Build result list
        result = []
        for m in materials:
            mid = m["id"]
            sys_stock = snapshot.get(mid, 0.0)
            
            # Double check for final output
            if m.get("name") in self.UNTRACKED_MATERIALS:
                sys_stock = 0.0
                
            result.append({
                "material_id": mid,
                "material_name": m.get("name"),
                "system_stock": sys_stock,
                "unit": m.get("unit", "kg")
            })
            
        return result

    def adjust_inventory_batch(self, adjustments: List[Dict[str, Any]], target_date: str, operator_name: str, custom_reason: str = None) -> Tuple[bool, str]:
        """
        批量修正库存 (盘点/初始化)
        adjustments: List of {"material_id": int, "actual_stock": float}
        """
        # 1. Get theoretical stock at target date
        snapshot_list = self.get_stock_snapshot_at_date(target_date)
        snapshot_map = {item["material_id"]: item["system_stock"] for item in snapshot_list}
        
        data = self.data_service.load_data()
        records = data.get(DataCategory.INVENTORY_RECORDS.value, [])
        materials = data.get(DataCategory.RAW_MATERIALS.value, [])
        
        new_records_added = False
        
        for adj in adjustments:
            mid = adj.get("material_id")
            actual = float(adj.get("actual_stock", 0.0))
            
            # Theoretical stock
            current = snapshot_map.get(mid, 0.0)
            diff = actual - current
            
            if abs(diff) < 1e-6:
                continue
                
            # Determine type and quantity
            if diff > 0:
                rtype = StockMovementType.ADJUST_IN.value
                qty = diff
            else:
                rtype = StockMovementType.ADJUST_OUT.value
                qty = abs(diff)
            
            # Create Record Data
            rec_data = {
                "material_id": mid,
                "type": rtype,
                "quantity": qty,
                "reason": custom_reason or f"库存初始化/盘点 (操作人: {operator_name})",
                "operator": operator_name,
                "snapshot_stock": actual, # Snapshot after this adjustment at that date
                "date": target_date
            }
            
            # Validate with Pydantic
            try:
                # We need to handle 'date' field manually if using InventoryRecordCreate 
                # because it might not expect date in input or handle it differently.
                # InventoryRecordCreate inherits InventoryRecordBase.
                # InventoryRecordBase doesn't have 'date' field, InventoryRecord does.
                # But we can just validate the base fields first.
                
                # Check Base fields
                InventoryRecordCreate(**rec_data)
                
            except Exception as e:
                logger.error(f"Validation failed for adjustment material {mid}: {e}")
                return False, f"数据校验失败 (ID {mid}): {e}"
            
            # Add to records
            # We need a new ID
            new_id = self.data_service._get_next_id(records)
            
            final_record = rec_data.copy()
            final_record["id"] = new_id
            final_record["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            records.append(final_record)
            new_records_added = True
            
            # Update Current Stock in Material Definition
            # NOTE: If target_date is in the past, simply adding diff to current stock is correct
            # because "Current Stock" = "Initial" + "All Movements".
            # By adding a movement of 'diff', we shift the whole curve up/down by 'diff'.
            for m in materials:
                if m["id"] == mid:
                    old_stock = float(m.get("stock_quantity", 0.0))
                    m["stock_quantity"] = old_stock + diff
                    m["last_stock_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    break
        
        if not new_records_added:
            return True, "没有需要调整的差异"
            
        # Save all
        data[DataCategory.INVENTORY_RECORDS.value] = records
        data[DataCategory.RAW_MATERIALS.value] = materials
        
        if self.data_service.save_data(data):
            return True, "库存盘点调整已保存"
        else:
            return False, "保存失败"

    # ------------------ Issue / Raw Material Methods ------------------

    def add_inventory_record(self, record_data: Union[Dict[str, Any], InventoryRecordCreate], input_unit: str = BASE_UNIT_RAW_MATERIAL) -> Tuple[bool, str]:
        """
        添加原材料库存记录 (入库/出库)
        自动将数量转换为基准单位 (kg)
        """
        # 1. Validate using Pydantic (if dict passed)
        if isinstance(record_data, dict):
            try:
                # Use InventoryRecordCreate for validation (which has positive validator)
                validated_data = InventoryRecordCreate(**record_data)
                rec_dict = validated_data.model_dump(mode='json')
            except Exception as e:
                logger.error(f"Validation error in add_inventory_record: {e}")
                return False, f"数据校验失败: {e}"
        else:
            rec_dict = record_data.model_dump(mode='json')
            
        # 2. Convert to Base Unit (kg)
        qty = rec_dict.get("quantity", 0.0)
        final_qty, success = convert_to_base_unit(qty, input_unit, 'raw_material')
        
        if not success:
            return False, f"单位转换失败: {input_unit} -> {BASE_UNIT_RAW_MATERIAL}"
            
        # Update quantity in record
        rec_dict["quantity"] = final_qty
        
        # Add note about conversion if needed
        if normalize_unit(input_unit) != normalize_unit(BASE_UNIT_RAW_MATERIAL):
            reason = rec_dict.get("reason", "")
            rec_dict["reason"] = f"{reason} (原: {qty} {input_unit})".strip()

        # 3. Call DataService to persist
        return self.data_service.add_inventory_record(rec_dict)

    def post_issue(self, issue_id: int, operator: str = "System") -> Tuple[bool, str]:
        """
        领料过账
        强制将所有消耗转换为基准单位 (Raw->kg, Product->Ton)
        """
        data = self.data_service.load_data()
        issues = data.get(DataCategory.MATERIAL_ISSUES.value, [])
        materials = data.get(DataCategory.RAW_MATERIALS.value, [])
        records = data.get(DataCategory.INVENTORY_RECORDS.value, [])
        products = data.get(DataCategory.PRODUCT_INVENTORY.value, [])
        product_records = data.get(DataCategory.PRODUCT_INVENTORY_RECORDS.value, [])
        orders = data.get(DataCategory.PRODUCTION_ORDERS.value, [])
        
        target_issue = None
        for issue in issues:
            if issue.get("id") == issue_id:
                target_issue = issue
                break
        
        if not target_issue: return False, "领料单不存在"
        if target_issue.get("status") == IssueStatus.POSTED.value: return False, "领料单已过账"
        
        lines = target_issue.get("lines", [])
        if not lines: return False, "领料单明细为空"
        
        # 关联信息
        rel_order_id = target_issue.get("production_order_id")
        rel_bom_id = None
        rel_bom_ver = None
        if rel_order_id:
            ord_obj = next((o for o in orders if o.get("id") == rel_order_id), None)
            if ord_obj:
                rel_bom_id = ord_obj.get("bom_id")
                rel_bom_ver = ord_obj.get("bom_version_id")
        
        for line in lines:
            raw_qty = float(line.get("required_qty", 0.0))
            if raw_qty <= 0: continue
            
            mid = line.get("item_id")
            line_uom = line.get("uom", UnitType.KG.value)
            item_type = line.get("item_type", MaterialType.RAW_MATERIAL.value)
            
            if item_type == MaterialType.PRODUCT.value:
                # ---------------- 成品扣减 (基准单位: 吨) ----------------
                prod_idx = -1
                current_stock = 0.0
                
                # ID Match
                for idx, p in enumerate(products):
                    if p.get("id") == mid:
                        prod_idx = idx
                        current_stock = float(p.get("stock_quantity", 0.0))
                        break
                
                # Name Match Fallback
                if prod_idx == -1:
                    expected_name = str(line.get("item_name", "") or "").strip()
                    if expected_name:
                        for idx, p in enumerate(products):
                            if str(p.get("name", "") or "").strip() == expected_name:
                                prod_idx = idx
                                current_stock = float(p.get("stock_quantity", 0.0))
                                break
                
                if prod_idx != -1:
                    # Convert to Base Unit (Ton)
                    final_qty, success = convert_to_base_unit(raw_qty, line_uom, 'product')
                    
                    if not success:
                        logger.warning(f"Unit conversion failed (product): {raw_qty} {line_uom} -> {BASE_UNIT_PRODUCT}")
                        # Fallback: assume 1:1 if conversion fails? Or raise error?
                        # Safe to continue but log warning, or return False?
                        # Returning False is safer for data integrity.
                        return False, f"单位转换失败: {line_uom} -> {BASE_UNIT_PRODUCT}"
                    
                    new_stock = current_stock - final_qty
                    products[prod_idx]["stock_quantity"] = new_stock
                    products[prod_idx]["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Record
                    reason_note = f"生产领料: {target_issue.get('issue_code')}"
                    if normalize_unit(line_uom) != normalize_unit(BASE_UNIT_PRODUCT):
                        reason_note += f" (原: {raw_qty}{line_uom})"
                    
                    new_rec_id = self.data_service._get_next_id(product_records)
                    product_records.append({
                        "id": new_rec_id,
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "product_name": products[prod_idx].get("product_name") or products[prod_idx].get("name"),
                        "product_type": products[prod_idx].get("type", "其他"),
                        "type": StockMovementType.CONSUME_OUT.value,
                        "quantity": final_qty, # Stored in Tons
                        "reason": reason_note,
                        "operator": operator,
                        "snapshot_stock": new_stock,
                        "related_doc_type": "ISSUE",
                        "related_doc_id": issue_id,
                        "related_order_id": rel_order_id,
                        "related_bom_id": rel_bom_id,
                        "related_bom_version_id": rel_bom_ver
                    })
            else:
                # ---------------- 原材料扣减 (基准单位: kg) ----------------
                mat_idx = -1
                current_stock = 0.0
                is_untracked = False
                
                for idx, m in enumerate(materials):
                    if m.get("id") == mid:
                        current_stock = float(m.get("stock_quantity", 0.0))
                        mat_name = m.get("name", "").strip()
                        is_untracked = mat_name in self.UNTRACKED_MATERIALS
                        mat_idx = idx
                        break
                
                if mat_idx >= 0:
                    # Convert to Base Unit (kg)
                    final_qty, success = convert_to_base_unit(raw_qty, line_uom, 'raw_material')
                    
                    if not success:
                         return False, f"单位转换失败: {line_uom} -> {BASE_UNIT_RAW_MATERIAL}"
    
                    new_stock = current_stock
                    
                    # 检查库存可用性 (虽然这里主要是扣减逻辑，但加上 check 更稳健，尽管业务要求免库存始终充足)
                    if not self.check_stock_availability(materials[mat_idx].get("name", ""), final_qty, current_stock):
                        # 注意：普通物料如果库存不足，是否应该报错？
                        # 当前 post_issue 逻辑允许扣减到负数。
                        # 这里我们保持原有逻辑，只对 untracked 做特殊处理。
                        pass

                    if not is_untracked:
                        new_stock = current_stock - final_qty
                        materials[mat_idx]["stock_quantity"] = new_stock
                        materials[mat_idx]["last_stock_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    reason_note = f"生产领料: {target_issue.get('issue_code')}"
                    if normalize_unit(line_uom) != normalize_unit(BASE_UNIT_RAW_MATERIAL):
                        reason_note += f" (原: {raw_qty}{line_uom})"
                    
                    new_rec_id = self.data_service._get_next_id(records)
                    records.append({
                        "id": new_rec_id,
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "material_id": mid,
                        "type": StockMovementType.CONSUME_OUT.value,
                        "quantity": final_qty, # Stored in kg
                        "reason": reason_note,
                        "operator": operator,
                        "related_doc_type": "ISSUE",
                        "related_doc_id": issue_id,
                        "snapshot_stock": new_stock
                    })
        
        target_issue["status"] = IssueStatus.POSTED.value
        target_issue["posted_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        data[DataCategory.INVENTORY_RECORDS.value] = records
        data[DataCategory.PRODUCT_INVENTORY_RECORDS.value] = product_records
        data[DataCategory.RAW_MATERIALS.value] = materials
        data[DataCategory.PRODUCT_INVENTORY.value] = products
        
        if self.data_service.save_data(data):
            return True, "过账成功"
        return False, "保存失败"

    def cancel_issue_posting(self, issue_id: int, operator: str = "System") -> Tuple[bool, str]:
        """
        撤销领料过账
        """
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
                    # 使用基准单位 (Ton) 计算回滚
                    # 注意：领料时已经转换过了，这里需要重新转换以确保一致
                    final_qty, success = convert_to_base_unit(qty, line_uom, 'product')
                    
                    new_stock = current_stock + final_qty
                    products[prod_idx]["stock_quantity"] = new_stock
                    products[prod_idx]["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    reason_note = f"撤销领料: {target_issue.get('issue_code')}"
                    if normalize_unit(line_uom) != normalize_unit(BASE_UNIT_PRODUCT):
                        reason_note += f" (原: {qty}{line_uom})"
                    
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
                is_untracked = False
                
                for idx, m in enumerate(materials):
                    if m.get("id") == mid:
                        current_stock = float(m.get("stock_quantity", 0.0))
                        mat_name = m.get("name", "").strip()
                        is_untracked = mat_name in self.UNTRACKED_MATERIALS
                        mat_idx = idx
                        break
                
                if mat_idx >= 0:
                    # 使用基准单位 (kg) 计算回滚
                    final_qty, success = convert_to_base_unit(qty, line_uom, 'raw_material')
                    
                    new_stock = current_stock
                    if not is_untracked:
                        new_stock = current_stock + final_qty
                        materials[mat_idx]["stock_quantity"] = new_stock
                        materials[mat_idx]["last_stock_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    reason_note = f"撤销领料: {target_issue.get('issue_code')}"
                    if normalize_unit(line_uom) != normalize_unit(BASE_UNIT_RAW_MATERIAL):
                        reason_note += f" (原: {qty}{line_uom})"
                    
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
