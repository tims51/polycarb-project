
import pytest
from services.bom_service import BOMService
from services.data_service import DataService
from core.enums import DataCategory, UnitType, MaterialType

def test_explode_bom(bom_service, data_service):
    """测试BOM展开计算"""
    data = data_service.load_data()
    
    # 1. Create BOM Version
    bom_version = {
        "id": 1,
        "bom_id": 101,
        "version": "v1.0",
        "yield_base": 1000.0,
        "lines": [
            {
                "item_id": 1,
                "item_name": "Material A",
                "item_type": MaterialType.RAW_MATERIAL.value,
                "qty": 10.0,
                "uom": UnitType.KG.value
            },
            {
                "item_id": 2,
                "item_name": "Material B",
                "item_type": MaterialType.RAW_MATERIAL.value,
                "qty": 5.0,
                "uom": UnitType.KG.value
            }
        ]
    }
    
    # Ensure BOM_VERSIONS list exists in mock data (conftest handles initialization but good to be safe)
    if DataCategory.BOM_VERSIONS.value not in data:
        data[DataCategory.BOM_VERSIONS.value] = []
        
    data[DataCategory.BOM_VERSIONS.value].append(bom_version)
    data_service.save_data(data)
    
    # Action: Target 2000 (Ratio = 2.0)
    result = bom_service.explode_bom(1, target_qty=2000.0)
    
    # Assert
    assert len(result) == 2
    
    # Verify items
    item_a = next((x for x in result if x["item_id"] == 1), None)
    item_b = next((x for x in result if x["item_id"] == 2), None)
    
    assert item_a is not None, "Item A not found in result"
    assert item_a["required_qty"] == 20.0, f"Expected 20.0, got {item_a['required_qty']}"
    
    assert item_b is not None, "Item B not found in result"
    assert item_b["required_qty"] == 10.0, f"Expected 10.0, got {item_b['required_qty']}"

def test_explode_bom_not_found(bom_service):
    """测试不存在的BOM版本"""
    result = bom_service.explode_bom(999, 1000)
    assert result == []
