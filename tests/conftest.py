
import pytest
import sys
from pathlib import Path
import json

# Add project root to path
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

from app.services.data_service import DataService

@pytest.fixture
def mock_data_file(tmp_path):
    """Create a temporary data file for testing."""
    d = tmp_path / "data.json"
    initial_data = {
        "projects": [],
        "experiments": [],
        "performance_data": {
            "synthesis": [],
            "paste": [],
            "mortar": [],
            "concrete": []
        },
        "raw_materials": [],
        "synthesis_records": [],
        "products": [],
        "paste_experiments": [],
        "mortar_experiments": [],
        "concrete_experiments": []
    }
    d.write_text(json.dumps(initial_data), encoding='utf-8')
    return d

@pytest.fixture
def data_service(mock_data_file):
    """Create a DataService instance using the mock file."""
    # We need to monkeypatch the DATA_FILE in config or the class
    # Since config is imported in data_service, patching it might be tricky if not done right.
    # But DataService uses self.data_file initialized in __init__ from config.
    # We can just instantiate and then overwrite self.data_file
    
    service = DataService()
    service.data_file = mock_data_file
    service.backup_dir = mock_data_file.parent / "backups"
    service.backup_dir.mkdir(exist_ok=True)
    
    return service
