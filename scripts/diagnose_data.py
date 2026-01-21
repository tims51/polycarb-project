
import sys
import os
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from core.container import ServiceContainer
from core.enums import StockMovementType

def check_raw_material_consistency(container):
    print("\n[1/3] Checking Raw Material Inventory Consistency...")
    
    inventory_service = container.inventory_service
    data_service = container.data_service
    
    materials = data_service.get_all_raw_materials()
    records = data_service.get_inventory_records()
    
    issues = []
    
    # Map material ID to object
    mat_map = {m["id"]: m for m in materials}
    
    # 1. Check for Orphan Records
    print(f"  - Scanning {len(records)} inventory records for orphans...")
    for r in records:
        mid = r.get("material_id")
        if mid not in mat_map:
            issues.append(f"[ORPHAN] Record ID {r.get('id')} references missing Material ID {mid}")
            
    # 2. Check Stock Calculation
    print(f"  - Verifying stock levels for {len(materials)} materials...")
    for mid, mat in mat_map.items():
        # Calculate theoretical stock from records
        calculated_stock = 0.0
        mat_records = [r for r in records if r.get("material_id") == mid]
        
        for r in mat_records:
            qty = float(r.get("quantity", 0.0))
            rtype = r.get("type")
            
            # Logic from InventoryService/DataService
            if rtype in [StockMovementType.IN.value, StockMovementType.PRODUCE_IN.value, 
                        StockMovementType.ADJUST_IN.value, StockMovementType.RETURN_IN.value, "in", "adjust_in"]:
                calculated_stock += qty
            elif rtype in [StockMovementType.OUT.value, StockMovementType.CONSUME_OUT.value, 
                          StockMovementType.ADJUST_OUT.value, "out", "consume_out", "adjust_out"]:
                calculated_stock -= qty
                
        current_stock = float(mat.get("stock_quantity", 0.0))
        
        # Allow small float difference
        if abs(calculated_stock - current_stock) > 0.001:
            issues.append(f"[MISMATCH] Material '{mat.get('name')}' (ID {mid}): System={current_stock}, Calculated={calculated_stock}, Diff={current_stock - calculated_stock}")
            
        # 3. Check Unit (Skill Requirement: Must be kg)
        unit = mat.get("unit", "")
        if unit.lower() not in ["kg", "千克"]:
            issues.append(f"[UNIT_WARNING] Material '{mat.get('name')}' (ID {mid}) unit is '{unit}', expected 'kg'")

    if not issues:
        print("  ✅ Raw Material Data is Consistent.")
    else:
        print(f"  ❌ Found {len(issues)} issues:")
        for i in issues:
            print(f"    - {i}")
            
    return len(issues)

def check_product_inventory_consistency(container):
    print("\n[2/3] Checking Product Inventory Consistency...")
    data_service = container.data_service
    
    products = data_service.get_product_inventory()
    records = data_service.get_product_inventory_records()
    
    issues = []
    prod_map = {p["id"]: p for p in products}
    
    # 1. Check Orphans (by Product Name/Type usually, but let's try matching logic)
    # Product records use product_name and product_type, not ID usually in this system (based on DataService code)
    # But let's check if names exist
    
    known_names = set(p.get("product_name") or p.get("name") for p in products)
    
    print(f"  - Verifying stock levels for {len(products)} products...")
    
    for p in products:
        pid = p.get("id")
        pname = p.get("product_name") or p.get("name")
        ptype = p.get("type")
        
        calculated_stock = 0.0
        
        # Filter records for this product
        # Note: Records link by name/type usually in this codebase
        p_records = [r for r in records if r.get("product_name") == pname and r.get("product_type") == ptype]
        
        for r in p_records:
            qty = float(r.get("quantity", 0.0))
            rtype = r.get("type")
            
            if rtype in [StockMovementType.IN.value, StockMovementType.PRODUCE_IN.value, 
                        StockMovementType.ADJUST_IN.value, StockMovementType.RETURN_IN.value, "in"]:
                calculated_stock += qty
            elif rtype in [StockMovementType.OUT.value, StockMovementType.CONSUME_OUT.value, 
                          StockMovementType.ADJUST_OUT.value, StockMovementType.SHIP_OUT.value, "out"]:
                calculated_stock -= qty
                
        current_stock = float(p.get("stock_quantity") or p.get("current_stock") or 0.0)
        
        if abs(calculated_stock - current_stock) > 0.001:
            issues.append(f"[MISMATCH] Product '{pname}' ({ptype}): System={current_stock}, Calculated={calculated_stock}, Diff={current_stock - calculated_stock}")

    if not issues:
        print("  ✅ Product Inventory Data is Consistent.")
    else:
        print(f"  ❌ Found {len(issues)} issues:")
        for i in issues:
            print(f"    - {i}")
            
    return len(issues)

def check_bom_integrity(container):
    print("\n[3/3] Checking BOM Integrity...")
    data_service = container.data_service
    boms = data_service.get_all_boms()
    versions = data_service.get_all_bom_versions()
    
    issues = []
    
    # Check 1: Versions referencing non-existent BOMs
    bom_ids = set(b["id"] for b in boms)
    for v in versions:
        if v.get("bom_id") not in bom_ids:
            issues.append(f"[ORPHAN] BOM Version ID {v.get('id')} references missing BOM ID {v.get('bom_id')}")
            
    # Check 2: Active BOMs without active versions
    for b in boms:
        if b.get("status") == "active":
            has_active_ver = False
            for v in versions:
                if v.get("bom_id") == b["id"] and v.get("status") == "approved": # Assuming 'approved' is the active status for versions
                    has_active_ver = True
                    break
            # This is just a warning, not strictly an error
            # if not has_active_ver:
            #     issues.append(f"[WARNING] Active BOM '{b.get('bom_code')}' has no approved version")

    if not issues:
        print("  ✅ BOM Data is Consistent.")
    else:
        print(f"  ❌ Found {len(issues)} issues:")
        for i in issues:
            print(f"    - {i}")

    return len(issues)

def main():
    print("="*50)
    print("POLYCARB SYSTEM DATA DIAGNOSIS")
    print("="*50)
    
    container = ServiceContainer()
    
    err_count = 0
    err_count += check_raw_material_consistency(container)
    err_count += check_product_inventory_consistency(container)
    err_count += check_bom_integrity(container)
    
    print("\n" + "="*50)
    if err_count == 0:
        print("🎉 DIAGNOSIS COMPLETE: NO ISSUES FOUND")
    else:
        print(f"⚠️ DIAGNOSIS COMPLETE: FOUND {err_count} ISSUES")
    print("="*50)

if __name__ == "__main__":
    main()
