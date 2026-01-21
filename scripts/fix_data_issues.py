import sys
import os
import logging
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from services.data_service import DataService
from core.enums import DataCategory, StockMovementType

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def fix_data_issues(dry_run: bool = True):
    logger.info(f"Starting Data Fix Script (Dry Run: {dry_run})...")
    ds = DataService()
    data = ds.load_data()
    
    raw_materials = data.get(DataCategory.RAW_MATERIALS.value, [])
    inventory_records = data.get(DataCategory.INVENTORY_RECORDS.value, [])
    products = data.get(DataCategory.PRODUCT_INVENTORY.value, [])
    product_records = data.get(DataCategory.PRODUCT_INVENTORY_RECORDS.value, [])
    
    # ---------------------------------------------------------
    # 1. Fix Raw Material Units (Ton -> kg)
    # ---------------------------------------------------------
    logger.info("\n[1/3] Fixing Raw Material Units...")
    fixed_materials = 0
    fixed_records = 0
    
    # Map material IDs to their objects for easy lookup
    mat_map = {m["id"]: m for m in raw_materials}
    
    for mat in raw_materials:
        unit = mat.get("unit", "").lower()
        if unit in ["ton", "吨"]:
            old_stock = float(mat.get("stock_quantity", 0.0))
            new_stock = old_stock * 1000.0
            
            if dry_run:
                logger.info(f"  [PROPOSED] Mat '{mat['name']}' (ID {mat['id']}): Unit {unit}->kg, Stock {old_stock}->{new_stock}")
            else:
                mat["unit"] = "kg"
                mat["stock_quantity"] = new_stock
            
            fixed_materials += 1
            
            # Update associated records
            for rec in inventory_records:
                if rec.get("material_id") == mat["id"]:
                    old_qty = float(rec.get("quantity", 0.0))
                    new_qty = old_qty * 1000.0
                    
                    if dry_run:
                        # logger.info(f"    [PROPOSED] Record {rec['id']}: {old_qty}->{new_qty}")
                        pass
                    else:
                        rec["quantity"] = new_qty
                        # Update snapshot if present
                        if "snapshot_stock" in rec:
                            rec["snapshot_stock"] = float(rec["snapshot_stock"]) * 1000.0
                    
                    fixed_records += 1

    logger.info(f"  -> Materials to fix: {fixed_materials}")
    logger.info(f"  -> Records to fix: {fixed_records}")

    # ---------------------------------------------------------
    # 2. Fix Product Stock Mismatch (Backfill Records)
    # ---------------------------------------------------------
    logger.info("\n[2/3] Fixing Product Stock Mismatches...")
    fixed_products = 0
    
    # Calculate current ledger balance for products
    prod_ledger_balance = {}
    for r in product_records:
        pid = None
        pname = r.get("product_name")
        ptype = r.get("product_type")
        
        # Find matching product ID
        found_p = None
        for p in products:
            if p.get("product_name") == pname and p.get("type") == ptype:
                found_p = p
                break
            if not found_p and p.get("name") == pname and p.get("type") == ptype:
                found_p = p
                break
        
        if found_p:
            pid = found_p.get("id")
            if pid not in prod_ledger_balance: prod_ledger_balance[pid] = 0.0
            
            qty = float(r.get("quantity", 0.0))
            rtype = r.get("type")
            if rtype in [StockMovementType.IN.value, StockMovementType.PRODUCE_IN.value, StockMovementType.ADJUST_IN.value, StockMovementType.RETURN_IN.value]:
                prod_ledger_balance[pid] += qty
            elif rtype in [StockMovementType.OUT.value, StockMovementType.CONSUME_OUT.value, StockMovementType.ADJUST_OUT.value, StockMovementType.SHIP_OUT.value]:
                prod_ledger_balance[pid] -= qty

    # Check against system stock
    for p in products:
        pid = p.get("id")
        sys_stock = float(p.get("stock_quantity") or p.get("current_stock") or 0.0)
        calc_stock = prod_ledger_balance.get(pid, 0.0)
        
        diff = sys_stock - calc_stock
        if abs(diff) > 1e-6:
            if dry_run:
                logger.info(f"  [PROPOSED] Product '{p.get('product_name')}' (ID {pid}): System={sys_stock}, Ledger={calc_stock}, Diff={diff}. Will create adjustment.")
            else:
                new_id = ds._get_next_id(product_records)
                # Increment locally for safety
                
                rec = {
                    "id": new_id,
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "product_name": p.get("product_name") or p.get("name"),
                    "product_type": p.get("type"),
                    "type": StockMovementType.ADJUST_IN.value if diff > 0 else StockMovementType.ADJUST_OUT.value,
                    "quantity": abs(diff),
                    "reason": "系统自动校准: 修复历史台账缺失",
                    "operator": "System",
                    "snapshot_stock": sys_stock,
                    "related_doc_type": "SYSTEM_FIX"
                }
                product_records.append(rec)
                fixed_products += 1

    logger.info(f"  -> Products to fix: {fixed_products}")

    # ---------------------------------------------------------
    # 3. Fix Raw Material Stock Mismatch (Backfill Records)
    # ---------------------------------------------------------
    logger.info("\n[3/3] Fixing Raw Material Stock Mismatches...")
    fixed_raw_materials_mismatch = 0
    
    # Calculate current ledger balance for raw materials
    # We must use the updated 'inventory_records' from Step 1
    raw_ledger_balance = {}
    
    for r in inventory_records:
        mid = r.get("material_id")
        if not mid: continue
        
        if mid not in raw_ledger_balance: raw_ledger_balance[mid] = 0.0
        
        qty = float(r.get("quantity", 0.0))
        rtype = r.get("type")
        
        # Logic matching InventoryService / Diagnose
        if rtype in [StockMovementType.IN.value, StockMovementType.PRODUCE_IN.value, 
                    StockMovementType.ADJUST_IN.value, StockMovementType.RETURN_IN.value, "in", "adjust_in"]:
            raw_ledger_balance[mid] += qty
        elif rtype in [StockMovementType.OUT.value, StockMovementType.CONSUME_OUT.value, 
                      StockMovementType.ADJUST_OUT.value, "out", "consume_out", "adjust_out"]:
            raw_ledger_balance[mid] -= qty

    # Check against system stock (which might have been updated in Step 1)
    for mat in raw_materials:
        mid = mat.get("id")
        sys_stock = float(mat.get("stock_quantity", 0.0))
        calc_stock = raw_ledger_balance.get(mid, 0.0)
        
        diff = sys_stock - calc_stock
        
        if abs(diff) > 1e-6:
            if dry_run:
                logger.info(f"  [PROPOSED] Material '{mat.get('name')}' (ID {mid}): System={sys_stock}, Ledger={calc_stock}, Diff={diff}. Will create adjustment.")
            else:
                new_id = ds._get_next_id(inventory_records)
                
                rec = {
                    "id": new_id,
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "material_id": mid,
                    "type": StockMovementType.ADJUST_IN.value if diff > 0 else StockMovementType.ADJUST_OUT.value,
                    "quantity": abs(diff),
                    "reason": "系统自动校准: 修复历史台账缺失",
                    "operator": "System",
                    "snapshot_stock": sys_stock,
                    "related_doc_type": "SYSTEM_FIX"
                }
                inventory_records.append(rec)
                fixed_raw_materials_mismatch += 1

    logger.info(f"  -> Raw Materials Mismatches to fix: {fixed_raw_materials_mismatch}")
    
    # ---------------------------------------------------------
    # Save
    # ---------------------------------------------------------
    if dry_run:
        logger.info("\n[DRY RUN] No changes saved.")
    else:
        logger.info("\nSaving changes to database...")
        data[DataCategory.RAW_MATERIALS.value] = raw_materials
        data[DataCategory.INVENTORY_RECORDS.value] = inventory_records
        data[DataCategory.PRODUCT_INVENTORY_RECORDS.value] = product_records
        
        if ds.save_data(data):
            logger.info("✅ Successfully saved fixed data.")
        else:
            logger.error("❌ Failed to save data.")

if __name__ == "__main__":
    is_dry_run = True
    if len(sys.argv) > 1 and sys.argv[1] == "--run":
        is_dry_run = False
    fix_data_issues(dry_run=is_dry_run)