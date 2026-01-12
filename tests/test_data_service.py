
import pytest
from datetime import datetime
from app.services.data_service import DataService

def test_initial_data_load(data_service):
    """Test that data service loads initial data correctly."""
    projects = data_service.get_all_projects()
    assert isinstance(projects, list)
    assert len(projects) == 0

def test_add_project(data_service):
    """Test adding a project."""
    project = {
        "name": "Test Project",
        "leader": "Tester",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "status": "In Progress"
    }
    result = data_service.add_project(project)
    assert result is True
    
    projects = data_service.get_all_projects()
    assert len(projects) == 1
    assert projects[0]["name"] == "Test Project"
    assert projects[0]["id"] == 1

def test_add_experiment(data_service):
    """Test adding an experiment."""
    exp = {
        "name": "Test Exp",
        "type": "Synthesis",
        "planned_date": "2024-01-01"
    }
    data_service.add_experiment(exp)
    exps = data_service.get_all_experiments()
    assert len(exps) == 1
    assert exps[0]["name"] == "Test Exp"

def test_concrete_experiment_crud(data_service):
    """Test CRUD for concrete experiments."""
    record = {
        "mix_id": "C30-001",
        "slump": 200,
        "strength_28d": 45.5
    }
    # Create
    data_service.add_concrete_experiment(record)
    records = data_service.get_all_concrete_experiments()
    assert len(records) == 1
    assert records[0]["mix_id"] == "C30-001"
    
    # Update
    rec_id = records[0]["id"]
    data_service.update_concrete_experiment(rec_id, {"slump": 210})
    updated = data_service.get_all_concrete_experiments()[0]
    assert updated["slump"] == 210
    
    # Delete
    data_service.delete_concrete_experiment(rec_id)
    assert len(data_service.get_all_concrete_experiments()) == 0

def test_product_unique_name(data_service):
    """Test that product names must be unique."""
    p1 = {"product_name": "Product A", "code": "P001"}
    data_service.add_product(p1)
    
    p2 = {"product_name": "Product A", "code": "P002"}
    with pytest.raises(ValueError):
        data_service.add_product(p2)
