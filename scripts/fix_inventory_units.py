
import sys
import os
import logging
from typing import Dict, List, Any
import json

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from services.data_service import DataService
from core.enums import DataCategory, StockMovementType, UnitType
from utils.unit_helper import BASE_UNIT_RAW_MATERIAL

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def fix_inventory_units(dry_run: bool = True):
    """
    Fix inventory units for raw materials.
    
    Logic:
    1. Load all data.
    2. Iterate through each raw material.
    3. Replay its inventory history (ledger).
    4. Detect anomalies: If a record is related to an ISSUE, and the issue UOM was 'Ton',
       but the quantity is small (< 10), it likely wasn't converted to kg.
    5. Fix the record quantity (* 1000).
    6. Recalculate running balance and final stock.
    7. Update material stock quantity.
    """
    
    logger.info(f"Starting Inventory Unit Fix Script (Dry Run: {dry_run})...")
    
    ds = DataService()
    # Force load data to ensure we have the latest
    data = ds.load_data()
    
    raw_materials = data.get(DataCategory.RAW_MATERIALS.value, [])
    inventory_records = data.get(DataCategory.INVENTORY_RECORDS.value, [])
    material_issues = data.get(DataCategory.MATERIAL_ISSUES.value, [])
    
    # Map issues by ID for quick lookup
    issues_map = {issue.get("id"): issue for issue in material_issues}
    
    total_records_fixed = 0
    total_stock_diff = 0.0
    
    # Process each material
    for material in raw_materials:
        mat_id = material.get("id")
        mat_name = material.get("name")
        old_stock = float(material.get("stock_quantity", 0.0))
        
        # Get records for this material
        mat_records = [r for r in inventory_records if r.get("material_id") == mat_id]
        
        # Sort by created_at to ensure chronological order
        # Fallback to date if created_at missing, then ID (as string)
        mat_records.sort(key=lambda x: (
            x.get("created_at", ""), 
            x.get("date", ""), 
            str(x.get("id", ""))
        ))
        
        calculated_stock = 0.0
        material_fixed_count = 0
        
        for record in mat_records:
            rec_id = record.get("id")
            rec_type = record.get("type")
            rec_qty = float(record.get("quantity", 0.0))
            related_doc_type = record.get("related_doc_type")
            related_doc_id = record.get("related_doc_id")
            
            # Check for fix needed
            fixed = False
            original_qty = rec_qty
            
            if related_doc_type == "ISSUE" and related_doc_id:
                issue = issues_map.get(related_doc_id)
                if issue:
                    # Find the line item for this material to check UOM
                    # Note: An issue might have multiple lines for same material, but usually aggregated or separate records?
                    # The record usually corresponds to a line. But we don't store line_id in record.
                    # We check the issue's general UOM or try to find the line matching this material.
                    
                    matched_line = None
                    for line in issue.get("lines", []):
                        if line.get("item_id") == mat_id:
                            matched_line = line
                            break
                    
                    if matched_line:
                        line_uom = matched_line.get("uom", UnitType.KG.value)
                        line_qty = float(matched_line.get("required_qty", 0.0))
                        
                        # Detection Logic 1: UOM is Ton, but stored quantity is small (< 10)
                        # Implies stored as Ton, should be kg.
                        if line_uom in [UnitType.TON.value, "ton", "Ton", "吨"] and abs(rec_qty) < 10.0 and rec_qty > 0:
                            new_qty = rec_qty * 1000.0
                            record["quantity"] = new_qty
                            rec_qty = new_qty
                            
                            reason = record.get("reason", "")
                            if "(Fix: Ton->kg)" not in reason:
                                record["reason"] = f"{reason} (Fix: Ton->kg)"
                            
                            fixed = True
                            material_fixed_count += 1
                            total_records_fixed += 1
                            
                            if dry_run:
                                logger.info(f"[FIX PROPOSED] Record #{rec_id} (Mat: {mat_name}): {original_qty} -> {new_qty} (Source: {line_uom}, Val < 10)")

                        # Detection Logic 2: UOM is kg, but stored quantity is ~1/1000 of line quantity
                        # Implies stored as Ton (by mistake?), should be kg.
                        elif line_uom in [UnitType.KG.value, "kg", "Kg", "KG"] and line_qty > 0:
                             if abs(rec_qty * 1000.0 - line_qty) < 0.1: # Allow small float error
                                new_qty = rec_qty * 1000.0
                                record["quantity"] = new_qty
                                rec_qty = new_qty
                                
                                reason = record.get("reason", "")
                                if "(Fix: Scale x1000)" not in reason:
                                    record["reason"] = f"{reason} (Fix: Scale x1000)"
                                
                                fixed = True
                                material_fixed_count += 1
                                total_records_fixed += 1
                                
                                if dry_run:
                                    logger.info(f"[FIX PROPOSED] Record #{rec_id} (Mat: {mat_name}): {original_qty} -> {new_qty} (Source: {line_uom}, Qty Mismatch)")

            # Update Running Balance (Replay Ledger)
            # Movements that ADD to stock
            if rec_type in [StockMovementType.IN.value, StockMovementType.RETURN_IN.value, 
                           StockMovementType.PRODUCE_IN.value, StockMovementType.ADJUST_IN.value]:
                calculated_stock += rec_qty
                
            # Movements that SUBTRACT from stock
            elif rec_type in [StockMovementType.OUT.value, StockMovementType.CONSUME_OUT.value, 
                             StockMovementType.ADJUST_OUT.value, StockMovementType.SHIP_OUT.value]:
                calculated_stock -= rec_qty
            
            # Update snapshot if changed or just to be safe/consistent
            # record["snapshot_stock"] = calculated_stock # Optional: update snapshot history? 
            # The prompt didn't explicitly ask to rewrite all snapshots, but it's good practice. 
            # However, to minimize side effects on 'Dry Run' display, let's just track the final.
            if fixed and not dry_run:
                 record["snapshot_stock"] = calculated_stock

        # End of records loop
        
        # Check if stock changed
        if abs(calculated_stock - old_stock) > 1e-6:
            diff = calculated_stock - old_stock
            total_stock_diff += diff
            if dry_run:
                logger.info(f"[STOCK DIFF] Material '{mat_name}' (ID {mat_id}): {old_stock} -> {calculated_stock} (Diff: {diff})")
            
            # Apply to material
            material["stock_quantity"] = calculated_stock
            # material["last_stock_update"] = ... # Keep original timestamp or update? Better keep original or update only if changed.

    # Summary
    logger.info("-" * 50)
    logger.info(f"Scan Complete.")
    logger.info(f"Records to be fixed: {total_records_fixed}")
    logger.info(f"Total Stock Difference (Net): {total_stock_diff}")
    
    if dry_run:
        logger.info("This was a DRY RUN. No changes were saved.")
    else:
        logger.info("Saving changes to database...")
        if ds.save_data(data):
            logger.info("Successfully saved corrected data.")
        else:
            logger.error("Failed to save data!")

if __name__ == "__main__":
    # Check for argument to run for real
    is_dry_run = True
    if len(sys.argv) > 1 and sys.argv[1] == "--run":
        is_dry_run = False
        
    fix_inventory_units(dry_run=is_dry_run)
