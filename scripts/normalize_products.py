
import os
import sys
import argparse

# Add src directory to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.append(src_path)

from services.data_service import DataService
from core.enums import DataCategory

from datetime import datetime

def normalize_products(run: bool = False):
    """
    Merges product aliases and ensures essential products exist.
    """
    print("Initializing DataService...")
    ds = DataService()

    # 1. Normalize product aliases
    print("Running product alias normalization...")
    try:
        merge_report, updated_ledgers_count = ds.normalize_product_aliases()
        
        if merge_report:
            print("\n--- Alias Merge Report ---")
            for report_line in merge_report:
                print(report_line)
            print(f"\nUpdated {updated_ledgers_count} related ledger entries.")
        else:
            print("No product aliases needed merging.")

    except Exception as e:
        print(f"An error occurred during alias normalization: {e}")
        return

    # 2. Ensure essential products exist
    print("\nChecking for essential products...")
    try:
        data = ds.load_data()
        inventory = data.get(DataCategory.PRODUCT_INVENTORY.value, [])
        products = data.get(DataCategory.PRODUCTS.value, [])
        
        essential_products = {
            "PC-001母液": "聚羧酸减水剂母液",
            "YJSNJ-有碱速凝剂": "速凝剂",
            "WJSNJ-无碱速凝剂": "速凝剂"
        }
        
        inventory_product_names = {item.get('product_name') for item in inventory}
        
        added_count = 0
        for name, category in essential_products.items():
            # 1. Check if product exists in 'products' master list
            product_id = None
            for p in products:
                if p.get('product_name') == name:
                    product_id = p.get('id')
                    break
            
            if product_id is None:
                # Create product definition if missing
                product_id = ds._get_next_id(products)
                new_product = {
                    "id": product_id,
                    "product_name": name,
                    "type": category,
                    "description": "系统初始化产品",
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                products.append(new_product)
                print(f"Added missing product definition: '{name}' (ID: {product_id})")

            # 2. Check if product exists in inventory
            if name not in inventory_product_names:
                new_entry = {
                    "id": ds._get_next_id(inventory),
                    "product_id": product_id,
                    "product_name": name,
                    "type": category,
                    "stock_quantity": 0.0,
                    "unit": "吨",
                    "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
                inventory.append(new_entry)
                added_count += 1
                print(f"Initialized missing inventory entry: '{name}'")

        if added_count > 0 or any(p.get('description') == "系统初始化产品" for p in products):
            data[DataCategory.PRODUCT_INVENTORY.value] = inventory
            data[DataCategory.PRODUCTS.value] = products
            if run:
                print(f"\nSaving {added_count} new essential product(s) to the database...")
                ds.save_data(data)
            else:
                print(f"\n--dry-run-- Would have added {added_count} essential product(s).")
        else:
            print("All essential products already exist in the inventory.")

    except Exception as e:
        print(f"An error occurred while ensuring essential products: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Normalize product data in the database.")
    parser.add_argument(
        '--dry-run', 
        action='store_true', 
        help='Run the script without saving changes.'
    )
    args = parser.parse_args()

    run_mode = not args.dry_run
    if not run_mode:
        print("--- Running in DRY RUN mode. No changes will be saved. ---")
    else:
        print("--- Running in EXECUTE mode. Changes will be saved. ---")
    
    normalize_products(run=run_mode)
    print("\nScript finished.")
