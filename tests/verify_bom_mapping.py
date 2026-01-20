
import sys
import os

# Add project root and app directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../app')))

from app.core.data_manager import DataManager
from app.services.inventory_service import InventoryService

def verify_bom_mapping():
    print("=== Verifying BOM Production Mode Mapping ===")
    
    # Initialize Service
    dm = DataManager()
    service = InventoryService(dm)
    
    # Get BOM Map
    bom_map = service._get_production_mode_map()
    print(f"Loaded {len(bom_map)} BOM production modes.")
    for name, mode in list(bom_map.items())[:5]:  # Show first 5
        print(f"  - {name}: {mode}")
        
    # Get Inventory with Mapping
    inventory = service.get_products()
    print(f"\nChecking {len(inventory)} inventory items...")
    
    unknown_count = 0
    mapped_count = 0
    
    for item in inventory:
        p_name = item.get("product_name", "Unknown Name")
        p_type = item.get("type", "Unknown")
        
        if p_type == "未知":
            unknown_count += 1
            print(f"[WARN] Product '{p_name}' -> Type: {p_type}")
        else:
            mapped_count += 1
            print(f"[OK]   Product '{p_name}' -> Type: {p_type}")
            
    print("\n=== Summary ===")
    print(f"Total Items: {len(inventory)}")
    print(f"Successfully Mapped: {mapped_count}")
    print(f"Unknown: {unknown_count}")
    
    if unknown_count > 0:
        print("\n[TIP] For 'Unknown' items, ensure a BOM exists with a matching name (or partial match).")

if __name__ == "__main__":
    verify_bom_mapping()
