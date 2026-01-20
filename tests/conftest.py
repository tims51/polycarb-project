
import pytest
import sys
from pathlib import Path
import json
import os

# Add src to python path so we can import modules
root_dir = Path(__file__).parent.parent
src_dir = root_dir / "src"
sys.path.append(str(src_dir))

from services.data_service import DataService
from services.inventory_service import InventoryService
from services.bom_service import BOMService
from core.enums import DataCategory

@pytest.fixture
def mock_data_file(tmp_path):
    """Create a temporary data file for testing."""
    d = tmp_path / "test_data.json"
    
    # Structure based on DataCategory enum and DataService requirements
    initial_data = {
        DataCategory.PROJECTS.value: [],
        DataCategory.EXPERIMENTS.value: [],
        DataCategory.PERFORMANCE_DATA.value: {
            "synthesis": [], "paste": [], "mortar": [], "concrete": []
        },
        DataCategory.RAW_MATERIALS.value: [],
        DataCategory.SYNTHESIS_RECORDS.value: [],
        DataCategory.PRODUCTS.value: [],
        DataCategory.PASTE_EXPERIMENTS.value: [],
        DataCategory.MORTAR_EXPERIMENTS.value: [],
        DataCategory.CONCRETE_EXPERIMENTS.value: [],
        DataCategory.GOODS_RECEIPTS.value: [],
        DataCategory.SHIPPING_ORDERS.value: [],
        DataCategory.INVENTORY_RECORDS.value: [],
        DataCategory.PRODUCTION_ORDERS.value: [],
        DataCategory.BOMS.value: [],
        DataCategory.BOM_VERSIONS.value: [],  # Note: This might be needed if not in initial list but used
        DataCategory.MOTHER_LIQUORS.value: [],
        DataCategory.MATERIAL_ISSUES.value: [],
        DataCategory.USERS.value: [],
        DataCategory.AUDIT_LOGS.value: [],
        DataCategory.PRODUCT_INVENTORY.value: [],
        DataCategory.PRODUCT_INVENTORY_RECORDS.value: []
    }
    
    d.write_text(json.dumps(initial_data), encoding='utf-8')
    return d

@pytest.fixture
def data_service(mock_data_file):
    """Create a DataService instance using the mock file."""
    # We initialize DataService and then point it to our test file
    service = DataService()
    service.data_file = mock_data_file
    
    # Also mock backup dir to avoid creating real backups
    service.backup_dir = mock_data_file.parent / "backups"
    service.backup_dir.mkdir(exist_ok=True)
    
    return service

@pytest.fixture
def inventory_service(data_service):
    """Create an InventoryService instance using the mock data service."""
    return InventoryService(data_service)

@pytest.fixture
def bom_service(data_service):
    """Create a BOMService instance using the mock data service."""
    return BOMService(data_service)
