
import sys
import os
import logging
from datetime import datetime
import json

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from services.data_service import DataService
from core.enums import DataCategory

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def inspect_inventory_period(start_date: str, end_date: str):
    logger.info(f"Inspecting Inventory Records between {start_date} and {end_date}...")
    
    ds = DataService()
    data = ds.load_data()
    
    records = data.get(DataCategory.INVENTORY_RECORDS.value, [])
    materials = {m['id']: m for m in data.get(DataCategory.RAW_MATERIALS.value, [])}
    
    # Filter records
    target_records = []
    for r in records:
        r_date = r.get("date")
        if not r_date and r.get("created_at"):
            r_date = r.get("created_at")[:10]
            
        if r_date and start_date <= r_date <= end_date:
            target_records.append(r)
            
    if not target_records:
        logger.info("No records found in this period.")
        return

    logger.info(f"Found {len(target_records)} records.")
    
    # Analyze
    issues = []
    manual_entries = []
    
    for r in target_records:
        mid = r.get("material_id")
        mat_name = materials.get(mid, {}).get("name", f"Unknown({mid})")
        qty = float(r.get("quantity", 0.0))
        reason = r.get("reason", "")
        
        # Check for manual entry indicators
        if "手动" in reason or "初始化" in reason or r.get("type") == "adjust_in":
            manual_entries.append(f"[{r.get('date')}] {mat_name}: {qty} kg (Reason: {reason})")
            
        # Check for potential unit anomalies (e.g., very small quantities for bulk items if not fixed)
        # Since we ran the fixer, units should be kg. 
        # But let's check for "ton" mentions in reason vs actual qty
        
        logger.info(f"  - {r.get('date')} | {mat_name:<20} | {r.get('type'):<10} | {qty:>10.3f} kg | {reason}")

    logger.info("-" * 50)
    if manual_entries:
        logger.info("Manual/Initialization Entries Found:")
        for entry in manual_entries:
            logger.info(f"  * {entry}")
    else:
        logger.info("No explicit manual initialization entries found in this period.")

if __name__ == "__main__":
    # Range: 2026-01-03 to 2026-01-12 (Assuming user meant this year based on env date 2026-01-21)
    inspect_inventory_period("2026-01-03", "2026-01-12")
