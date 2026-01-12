
"""
Data Service Module
Handles all data persistence, loading, and management operations.
"""

import json
import shutil
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
import streamlit as st

from config import DATA_FILE, BACKUP_DIR
from services.timeline_service import TimelineService

logger = logging.getLogger(__name__)

class DataService:
    """Service for managing application data."""
    
    def __init__(self):
        self.data_file = DATA_FILE
        self.backup_dir = BACKUP_DIR
        
        self._ensure_valid_data_file()
        
        # Initialize session state for backup tracking if needed
        if "last_backup_time" not in st.session_state:
            st.session_state.last_backup_time = None

    def _ensure_valid_data_file(self) -> bool:
        """Ensure data file exists and has valid format."""
        try:
            if self.data_file.exists():
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if not isinstance(data, dict):
                    raise ValueError("Data format is incorrect (not a dict)")
                
                self._ensure_data_structure(data)
                return True
        except (json.JSONDecodeError, ValueError, FileNotFoundError) as e:
            logger.warning(f"Data file invalid or missing ({e}), creating initial data...")
            initial_data = self.get_initial_data()
            return self.save_data(initial_data)
        except Exception as e:
            logger.error(f"Unexpected error checking data file: {e}")
            return False
            
        return False

    def _ensure_data_structure(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure all required keys exist in the data dictionary."""
        required_keys = [
            "projects", "experiments", "performance_data",
            "raw_materials", "synthesis_records", "products",
            "paste_experiments", "mortar_experiments", "concrete_experiments"
        ]
        
        for key in required_keys:
            if key not in data:
                if key == "performance_data":
                    data[key] = {"synthesis": [], "paste": [], "mortar": [], "concrete": []}
                else:
                    data[key] = []
        return data

    def load_data(self) -> Dict[str, Any]:
        """Load data from JSON file."""
        try:
            if self.data_file.exists():
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return self._ensure_data_structure(data)
            else:
                return self.get_initial_data()
        except Exception as e:
            logger.error(f"Failed to load data: {e}")
            st.error(f"读取数据失败: {e}")
            return self.get_initial_data()

    def save_data(self, data: Dict[str, Any]) -> bool:
        """Save data to JSON file and create backup."""
        try:
            self.data_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write to temp file first
            temp_file = self.data_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            
            # Atomic replace
            temp_file.replace(self.data_file)
            
            # Check auto backup
            self.check_and_create_auto_backup()
            
            return True
        except Exception as e:
            logger.error(f"Failed to save data: {e}")
            st.error(f"保存数据失败: {e}")
            return False

    def check_and_create_auto_backup(self):
        """Create auto backup if enough time has passed."""
        try:
            now = datetime.now()
            last_backup = st.session_state.get("last_backup_time")
            
            should_backup = False
            if last_backup is None:
                should_backup = True
            elif isinstance(last_backup, datetime):
                if (now - last_backup).total_seconds() > 3600: # 1 hour
                    should_backup = True
            else:
                # Handle legacy string format or other types
                should_backup = True
                
            if should_backup:
                self.create_backup()
                st.session_state.last_backup_time = now
        except Exception as e:
            logger.error(f"Auto backup check failed: {e}")

    def create_backup(self) -> bool:
        """Create a manual backup of the data file."""
        try:
            if self.data_file.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = self.backup_dir / f"data_backup_{timestamp}.json"
                
                shutil.copy2(self.data_file, backup_file)
                self._cleanup_old_backups()
                logger.info(f"Backup created: {backup_file}")
                return True
        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            return False
        return False

    def _cleanup_old_backups(self, max_backups: int = 30):
        """Remove old backups to save space."""
        try:
            backup_files = list(self.backup_dir.glob("data_backup_*.json"))
            if len(backup_files) > max_backups:
                backup_files.sort(key=lambda x: x.stat().st_mtime)
                files_to_delete = backup_files[:-max_backups]
                for file in files_to_delete:
                    file.unlink()
                    logger.info(f"Deleted old backup: {file}")
        except Exception as e:
            logger.error(f"Backup cleanup failed: {e}")

    # -------------------- Initial Data --------------------
    def get_initial_data(self) -> Dict[str, Any]:
        """Return the default data structure."""
        return {
            "projects": [
                {
                    "id": 1,
                    "name": "PC-001合成优化",
                    "leader": "张三",
                    "start_date": "2024-01-01",
                    "end_date": "2024-03-01",
                    "status": "进行中",
                    "progress": 75,
                    "description": "优化聚羧酸合成工艺参数"
                }
            ],
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

    # -------------------- Generic CRUD Helpers --------------------
    def _get_items(self, key: str) -> List[Dict[str, Any]]:
        data = self.load_data()
        return data.get(key, [])

    def _add_item(self, key: str, item: Dict[str, Any]) -> bool:
        data = self.load_data()
        items = data.get(key, [])
        
        # Auto-increment ID
        new_id = max([x.get("id", 0) for x in items], default=0) + 1
        item["id"] = new_id
        
        items.append(item)
        data[key] = items
        return self.save_data(data)

    def _update_item(self, key: str, item_id: int, updates: Dict[str, Any]) -> bool:
        data = self.load_data()
        items = data.get(key, [])
        
        updated = False
        for i, item in enumerate(items):
            if item.get("id") == item_id:
                items[i].update(updates)
                updated = True
                break
        
        if updated:
            data[key] = items
            return self.save_data(data)
        return False

    def _delete_item(self, key: str, item_id: int) -> bool:
        data = self.load_data()
        items = data.get(key, [])
        new_items = [x for x in items if x.get("id") != item_id]
        
        if len(new_items) < len(items):
            data[key] = new_items
            return self.save_data(data)
        return False

    # -------------------- Project Methods --------------------
    def get_all_projects(self) -> List[Dict[str, Any]]:
        return self._get_items("projects")

    def get_project(self, project_id: int) -> Optional[Dict[str, Any]]:
        projects = self.get_all_projects()
        for p in projects:
            if p.get("id") == project_id:
                return p
        return None

    def add_project(self, project_data: Dict[str, Any]) -> bool:
        # Normalize dates
        for date_field in ["start_date", "end_date"]:
            if date_field in project_data and hasattr(project_data[date_field], 'strftime'):
                project_data[date_field] = project_data[date_field].strftime("%Y-%m-%d")
        return self._add_item("projects", project_data)

    def update_project(self, project_id: int, updates: Dict[str, Any]) -> bool:
        return self._update_item("projects", project_id, updates)

    def delete_project(self, project_id: int) -> bool:
        return self._delete_item("projects", project_id)

    def get_project_timeline(self, project_id: int) -> Optional[Dict[str, Any]]:
        project = self.get_project(project_id)
        if not project:
            return None
        return TimelineService.calculate_timeline(project)

    # -------------------- Experiment Methods --------------------
    def get_all_experiments(self) -> List[Dict[str, Any]]:
        return self._get_items("experiments")

    def add_experiment(self, experiment_data: Dict[str, Any]) -> bool:
        # Normalize dates
        for date_field in ["planned_date", "actual_date"]:
            val = experiment_data.get(date_field)
            if val and hasattr(val, 'strftime'):
                experiment_data[date_field] = val.strftime("%Y-%m-%d")
        return self._add_item("experiments", experiment_data)

    def update_experiment(self, experiment_id: int, updates: Dict[str, Any]) -> bool:
        return self._update_item("experiments", experiment_id, updates)

    def delete_experiment(self, experiment_id: int) -> bool:
        return self._delete_item("experiments", experiment_id)

    # -------------------- Raw Materials --------------------
    def get_all_raw_materials(self) -> List[Dict[str, Any]]:
        return self._get_items("raw_materials")

    def add_raw_material(self, material_data: Dict[str, Any]) -> bool:
        material_data["created_date"] = datetime.now().strftime("%Y-%m-%d")
        return self._add_item("raw_materials", material_data)

    def update_raw_material(self, material_id: int, updates: Dict[str, Any]) -> bool:
        return self._update_item("raw_materials", material_id, updates)

    def delete_raw_material(self, material_id: int) -> bool:
        return self._delete_item("raw_materials", material_id)

    # -------------------- Synthesis Records --------------------
    def get_all_synthesis_records(self) -> List[Dict[str, Any]]:
        return self._get_items("synthesis_records")

    def add_synthesis_record(self, record_data: Dict[str, Any]) -> bool:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        record_data["created_at"] = now_str
        record_data["last_modified"] = now_str
        return self._add_item("synthesis_records", record_data)

    def delete_synthesis_record(self, record_id: int) -> bool:
        return self._delete_item("synthesis_records", record_id)
    
    # -------------------- Products --------------------
    def get_all_products(self) -> List[Dict[str, Any]]:
        return self._get_items("products")
        
    def check_product_name_exists(self, name: str, exclude_id: Optional[int] = None) -> bool:
        products = self.get_all_products()
        name_lower = name.strip().lower()
        for p in products:
            if exclude_id is not None and p.get("id") == exclude_id:
                continue
            if p.get("product_name", "").strip().lower() == name_lower:
                return True
        return False

    def add_product(self, product_data: Dict[str, Any]) -> bool:
        if self.check_product_name_exists(product_data.get("product_name", "")):
             raise ValueError(f"Product name '{product_data.get('product_name')}' already exists")
        
        product_data["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return self._add_item("products", product_data)

    def update_product(self, product_id: int, updates: Dict[str, Any]) -> bool:
        if "product_name" in updates:
             if self.check_product_name_exists(updates["product_name"], exclude_id=product_id):
                 raise ValueError(f"Product name '{updates['product_name']}' already exists")
        
        updates["last_modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return self._update_item("products", product_id, updates)

    def delete_product(self, product_id: int) -> bool:
        return self._delete_item("products", product_id)

    # -------------------- Paste/Mortar/Concrete Experiments --------------------
    # These seemed to use similar logic in original code, I'll generalize them
    
    def get_experiments_by_type(self, exp_type: str) -> List[Dict[str, Any]]:
        """
        Get experiments for specific type: 'paste_experiments', 'mortar_experiments', 'concrete_experiments'
        """
        return self._get_items(exp_type)

    def add_typed_experiment(self, exp_type: str, data: Dict[str, Any]) -> bool:
        data["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return self._add_item(exp_type, data)
    
    def update_typed_experiment(self, exp_type: str, exp_id: int, updates: Dict[str, Any]) -> bool:
        updates["last_modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return self._update_item(exp_type, exp_id, updates)
        
    def delete_typed_experiment(self, exp_type: str, exp_id: int) -> bool:
        return self._delete_item(exp_type, exp_id)

    # Legacy wrappers for specific types to maintain compatibility if needed
    def get_all_paste_experiments(self): return self.get_experiments_by_type("paste_experiments")
    def add_paste_experiment(self, data): return self.add_typed_experiment("paste_experiments", data)
    def update_paste_experiment(self, id, updates): return self.update_typed_experiment("paste_experiments", id, updates)
    def delete_paste_experiment(self, id): return self.delete_typed_experiment("paste_experiments", id)
    
    def get_all_mortar_experiments(self): return self.get_experiments_by_type("mortar_experiments")
    def add_mortar_experiment(self, data): return self.add_typed_experiment("mortar_experiments", data)
    def update_mortar_experiment(self, id, updates): return self.update_typed_experiment("mortar_experiments", id, updates)
    def delete_mortar_experiment(self, id): return self.delete_typed_experiment("mortar_experiments", id)
    
    def get_all_concrete_experiments(self): return self.get_experiments_by_type("concrete_experiments")
    def add_concrete_experiment(self, data): return self.add_typed_experiment("concrete_experiments", data)
    def update_concrete_experiment(self, id, updates): return self.update_typed_experiment("concrete_experiments", id, updates)
    def delete_concrete_experiment(self, id): return self.delete_typed_experiment("concrete_experiments", id)
