import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'src'))

try:
    from core.data_manager import DataManager
    from core.models import Product, ProductStock, TimelineInfo
    from services.data_service import DataService
    from services.timeline_service import TimelineService
    from core.enums import ProductCategory
    from config import DEFAULT_UNIT
    print("Imports successful")
except Exception as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()
