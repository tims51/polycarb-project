
import pytest
from services.inventory_service import InventoryService
from services.data_service import DataService
from core.enums import DataCategory, IssueStatus, StockMovementType, UnitType, MaterialType

def test_post_issue(inventory_service, data_service):
    """测试领料过账"""
    # Setup data
    data = data_service.load_data()
    
    # 1. Create Raw Material
    material = {
        "id": 1,
        "name": "Test Material",
        "stock_quantity": 100.0,
        "unit": UnitType.KG.value
    }
    data[DataCategory.RAW_MATERIALS.value].append(material)
    
    # 2. Create Issue
    issue = {
        "id": 1,
        "issue_code": "ISS-001",
        "status": IssueStatus.DRAFT.value,
        "lines": [
            {
                "item_id": 1,
                "item_name": "Test Material",
                "item_type": MaterialType.RAW_MATERIAL.value,
                "required_qty": 10.0,
                "uom": UnitType.KG.value
            }
        ]
    }
    data[DataCategory.MATERIAL_ISSUES.value].append(issue)
    data_service.save_data(data)
    
    # Action
    success, msg = inventory_service.post_issue(1)
    
    # Assert
    assert success is True, f"Post issue failed: {msg}"
    
    # Verify Stock
    new_data = data_service.load_data()
    mat = new_data[DataCategory.RAW_MATERIALS.value][0]
    assert mat["stock_quantity"] == 90.0
    
    # Verify Record
    records = new_data[DataCategory.INVENTORY_RECORDS.value]
    assert len(records) == 1
    rec = records[0]
    assert rec["material_id"] == 1
    assert rec["quantity"] == 10.0
    assert rec["type"] == StockMovementType.CONSUME_OUT.value

def test_cancel_issue(inventory_service, data_service):
    """测试撤销过账"""
    # Setup data (Already posted state)
    data = data_service.load_data()
    
    material = {
        "id": 1,
        "name": "Test Material",
        "stock_quantity": 90.0,
        "unit": UnitType.KG.value
    }
    data[DataCategory.RAW_MATERIALS.value].append(material)
    
    issue = {
        "id": 1,
        "issue_code": "ISS-001",
        "status": IssueStatus.POSTED.value,
        "lines": [
            {
                "item_id": 1,
                "item_name": "Test Material",
                "item_type": MaterialType.RAW_MATERIAL.value,
                "required_qty": 10.0,
                "uom": UnitType.KG.value
            }
        ]
    }
    data[DataCategory.MATERIAL_ISSUES.value].append(issue)
    
    # Existing record (OUT)
    record = {
        "id": 1,
        "material_id": 1,
        "type": StockMovementType.CONSUME_OUT.value,
        "quantity": 10.0,
        "related_doc_type": "ISSUE",
        "related_doc_id": 1
    }
    data[DataCategory.INVENTORY_RECORDS.value].append(record)
    
    data_service.save_data(data)
    
    # Action
    success, msg = inventory_service.cancel_issue_posting(1)
    
    # Assert
    assert success is True, f"Cancel issue failed: {msg}"
    
    # Verify Stock
    new_data = data_service.load_data()
    mat = new_data[DataCategory.RAW_MATERIALS.value][0]
    assert mat["stock_quantity"] == 100.0
    
    # Verify Record
    records = new_data[DataCategory.INVENTORY_RECORDS.value]
    # Should have new return record (so 2 records total)
    assert len(records) == 2
    return_rec = records[1]
    assert return_rec["type"] == StockMovementType.RETURN_IN.value
    assert return_rec["quantity"] == 10.0
    
    # Verify Issue Status
    iss = new_data[DataCategory.MATERIAL_ISSUES.value][0]
    assert iss["status"] == IssueStatus.DRAFT.value

def test_post_issue_invalid_id(inventory_service):
    """测试异常处理"""
    success, msg = inventory_service.post_issue(999)
    assert success is False
    assert "不存在" in msg
