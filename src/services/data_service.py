"""
Data Service Module
Handles all data persistence, loading, and management operations.
"""

import json
import shutil
import logging
import secrets
import os
from datetime import datetime, date
from typing import Dict, List, Any, Optional, Union, Tuple
from pathlib import Path
import streamlit as st

from config import DATA_FILE, BACKUP_DIR
from services.timeline_service import TimelineService
from utils.unit_helper import convert_quantity, normalize_unit
from core.models import (
    Project, Experiment, User, BaseModelWithConfig, TimelineInfo,
    RawMaterial, SynthesisRecord, Product, PasteExperiment, MortarExperiment, ConcreteExperiment,
    GoodsReceipt, ShippingOrder, InventoryRecord, BOM, ProductionOrder, MotherLiquor, BOMVersion,
    ProductInventoryRecord, GoodsReceiptItem, ShippingOrderItem, BOMExplosionItem
)
from core.enums import (
    ProjectStatus, ExperimentStatus, UserRole, DataCategory, BOMStatus, UnitType,
    StockMovementType, ProductCategory, IssueStatus, ProductionOrderStatus, MaterialType,
    ReceiptStatus, ShippingStatus, PermissionAction
)
from core.constants import (
    DATE_FORMAT, DATETIME_FORMAT, DEFAULT_UNIT_KG, WATER_MATERIAL_ALIASES, 
    PRODUCT_NAME_WJSNJ, PRODUCT_NAME_YJSNJ, BACKUP_INTERVAL_SECONDS
)
from utils.file_lock import file_lock

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
            DataCategory.PROJECTS.value, 
            DataCategory.EXPERIMENTS.value, 
            DataCategory.PERFORMANCE_DATA.value,
            DataCategory.RAW_MATERIALS.value, 
            DataCategory.SYNTHESIS_RECORDS.value, 
            DataCategory.PRODUCTS.value,
            DataCategory.PASTE_EXPERIMENTS.value, 
            DataCategory.MORTAR_EXPERIMENTS.value, 
            DataCategory.CONCRETE_EXPERIMENTS.value,
            DataCategory.GOODS_RECEIPTS.value,
            DataCategory.SHIPPING_ORDERS.value,
            DataCategory.INVENTORY_RECORDS.value,
            DataCategory.PRODUCTION_ORDERS.value,
            DataCategory.BOMS.value,
            DataCategory.MOTHER_LIQUORS.value
        ]
        
        for key in required_keys:
            if key not in data:
                if key == DataCategory.PERFORMANCE_DATA.value:
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
        """Save data to JSON file with atomic write and locking."""
        try:
            self.data_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Use file lock to prevent concurrent write conflicts
            with file_lock(self.data_file, timeout=10):
                # 1. Force Backup (Pre-write)
                self.create_backup(force=True)
                
                # 2. Atomic Write
                temp_file = self.data_file.with_suffix('.tmp')
                
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                    f.flush()
                    os.fsync(f.fileno())
                
                # Atomic Replace
                if temp_file.exists():
                    try:
                        os.replace(temp_file, self.data_file)
                    except OSError:
                        if os.name == 'nt' and self.data_file.exists():
                            os.remove(self.data_file)
                            os.rename(temp_file, self.data_file)
                        else:
                            raise
            
            # Update backup timestamp
            st.session_state.last_backup_time = datetime.now()
            
            return True
        except Exception as e:
            logger.error(f"Failed to save data: {e}")
            st.error(f"Data save failed: {e}")
            return False

    def check_and_create_auto_backup(self) -> None:
        """Create auto backup if enough time has passed."""
        try:
            now = datetime.now()
            last_backup = st.session_state.get("last_backup_time")
            
            should_backup = False
            if last_backup is None:
                should_backup = True
            elif isinstance(last_backup, datetime):
                if (now - last_backup).total_seconds() > BACKUP_INTERVAL_SECONDS: # 1 hour
                    should_backup = True
            else:
                should_backup = True
                
            if should_backup:
                self.create_backup()
                st.session_state.last_backup_time = now
        except Exception as e:
            logger.error(f"Auto backup check failed: {e}")

    def create_backup(self, force: bool = False) -> bool:
        """Create a manual backup of the data file."""
        try:
            if not self.data_file.exists():
                return False
                
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            backup_file = self.backup_dir / f"data_backup_{timestamp}.json"
            
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.data_file, backup_file)
            
            self._cleanup_old_backups(max_backups=50)
            logger.info(f"Backup created: {backup_file}")
            return True
        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            return False

    def _cleanup_old_backups(self, max_backups: int = 50) -> None:
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
            DataCategory.PROJECTS.value: [
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
            DataCategory.EXPERIMENTS.value: [],
            DataCategory.PERFORMANCE_DATA.value: {
                "synthesis": [],
                "paste": [],
                "mortar": [],
                "concrete": []
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
            DataCategory.MOTHER_LIQUORS.value: [],
            DataCategory.MATERIAL_ISSUES.value: [],
            DataCategory.PRODUCT_INVENTORY.value: [],
            DataCategory.PRODUCT_INVENTORY_RECORDS.value: []
        }

    # -------------------- Generic CRUD Helpers --------------------
    def _get_items(self, key: str) -> List[Dict[str, Any]]:
        data = self.load_data()
        return data.get(key, [])

    def _get_next_id(self, items: List[Dict[str, Any]]) -> int:
        """Safely calculate the next integer ID, ignoring non-integer IDs."""
        ids = []
        for item in items:
            val = item.get("id")
            if isinstance(val, int):
                ids.append(val)
            elif isinstance(val, str) and val.isdigit():
                try:
                    ids.append(int(val))
                except:
                    pass
        return max(ids, default=0) + 1

    def _add_item(self, key: str, item: Dict[str, Any]) -> bool:
        data = self.load_data()
        items = data.get(key, [])
        
        # Auto-increment ID
        new_id = self._get_next_id(items)
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
        return self._get_items(DataCategory.PROJECTS.value)

    def get_project(self, project_id: int) -> Optional[Dict[str, Any]]:
        projects = self.get_all_projects()
        for p in projects:
            if p.get("id") == project_id:
                return p
        return None

    def add_project(self, project_data: Union[Dict[str, Any], Project]) -> bool:
        # Normalize dates
        if isinstance(project_data, Project):
            proj_dict = project_data.model_dump(mode='json')
        else:
            proj_dict = project_data.copy()
            for date_field in ["start_date", "end_date"]:
                if date_field in proj_dict and hasattr(proj_dict[date_field], 'strftime'):
                    proj_dict[date_field] = proj_dict[date_field].strftime("%Y-%m-%d")
        return self._add_item(DataCategory.PROJECTS.value, proj_dict)

    def update_project(self, project_id: int, updates: Dict[str, Any]) -> bool:
        return self._update_item(DataCategory.PROJECTS.value, project_id, updates)

    def delete_project(self, project_id: int) -> bool:
        return self._delete_item(DataCategory.PROJECTS.value, project_id)

    def get_project_timeline(self, project_id: int) -> Optional[TimelineInfo]:
        project = self.get_project(project_id)
        if not project:
            return None
        # Convert dict to Project model if needed, but TimelineManager handles it
        return TimelineService.calculate_timeline(project)

    # -------------------- Experiment Methods --------------------
    def get_all_experiments(self) -> List[Dict[str, Any]]:
        return self._get_items(DataCategory.EXPERIMENTS.value)

    def add_experiment(self, experiment_data: Union[Dict[str, Any], Experiment]) -> bool:
        # Normalize dates
        if isinstance(experiment_data, Experiment):
            exp_dict = experiment_data.model_dump(mode='json')
        else:
            exp_dict = experiment_data.copy()
            for date_field in ["planned_date", "actual_date"]:
                val = exp_dict.get(date_field)
                if val and hasattr(val, 'strftime'):
                    exp_dict[date_field] = val.strftime("%Y-%m-%d")
        return self._add_item(DataCategory.EXPERIMENTS.value, exp_dict)

    def update_experiment(self, experiment_id: int, updates: Dict[str, Any]) -> bool:
        return self._update_item(DataCategory.EXPERIMENTS.value, experiment_id, updates)

    def delete_experiment(self, experiment_id: int) -> bool:
        return self._delete_item(DataCategory.EXPERIMENTS.value, experiment_id)

    # -------------------- Raw Materials --------------------
    def get_all_raw_materials(self) -> List[Dict[str, Any]]:
        return self._get_items(DataCategory.RAW_MATERIALS.value)

    def add_raw_material(self, material_data: Union[Dict[str, Any], RawMaterial]) -> bool:
        if isinstance(material_data, RawMaterial):
            if not material_data.created_date:
                material_data.created_date = datetime.now().strftime("%Y-%m-%d")
            mat_dict = material_data.model_dump(mode='json')
        else:
            mat_dict = material_data.copy()
            if "created_date" not in mat_dict:
                mat_dict["created_date"] = datetime.now().strftime("%Y-%m-%d")
        return self._add_item(DataCategory.RAW_MATERIALS.value, mat_dict)

    def update_raw_material(self, material_id: int, updates: Dict[str, Any]) -> bool:
        return self._update_item(DataCategory.RAW_MATERIALS.value, material_id, updates)

    def delete_raw_material(self, material_id: int) -> bool:
        return self._delete_item(DataCategory.RAW_MATERIALS.value, material_id)

    # -------------------- Synthesis Records --------------------
    def get_all_synthesis_records(self) -> List[Dict[str, Any]]:
        return self._get_items(DataCategory.SYNTHESIS_RECORDS.value)

    def add_synthesis_record(self, record_data: Union[Dict[str, Any], SynthesisRecord]) -> bool:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(record_data, SynthesisRecord):
             if not record_data.created_at:
                 record_data.created_at = now_str
             if not record_data.last_modified:
                 record_data.last_modified = now_str
             rec_dict = record_data.model_dump(mode='json')
        else:
            rec_dict = record_data.copy()
            if "created_at" not in rec_dict:
                rec_dict["created_at"] = now_str
            if "last_modified" not in rec_dict:
                rec_dict["last_modified"] = now_str
        return self._add_item(DataCategory.SYNTHESIS_RECORDS.value, rec_dict)

    def delete_synthesis_record(self, record_id: int) -> bool:
        return self._delete_item(DataCategory.SYNTHESIS_RECORDS.value, record_id)
    
    # -------------------- Products --------------------
    def get_all_products(self) -> List[Dict[str, Any]]:
        return self._get_items(DataCategory.PRODUCTS.value)
        
    def check_product_name_exists(self, name: str, exclude_id: Optional[int] = None) -> bool:
        products = self.get_all_products()
        name_lower = name.strip().lower()
        for p in products:
            if exclude_id is not None and p.get("id") == exclude_id:
                continue
            if p.get("product_name", "").strip().lower() == name_lower:
                return True
        return False

    def add_product(self, product_data: Union[Dict[str, Any], Product]) -> bool:
        if isinstance(product_data, Product):
            if not product_data.created_at:
                product_data.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            prod_dict = product_data.model_dump(mode='json')
        else:
             prod_dict = product_data.copy()
             if "created_at" not in prod_dict:
                prod_dict["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if self.check_product_name_exists(prod_dict.get("product_name", "")):
             raise ValueError(f"Product name '{prod_dict.get('product_name')}' already exists")
        
        return self._add_item(DataCategory.PRODUCTS.value, prod_dict)

    def update_product(self, product_id: int, updates: Dict[str, Any]) -> bool:
        if "product_name" in updates:
             if self.check_product_name_exists(updates["product_name"], exclude_id=product_id):
                 raise ValueError(f"Product name '{updates['product_name']}' already exists")
        
        updates["last_modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return self._update_item(DataCategory.PRODUCTS.value, product_id, updates)

    def delete_product(self, product_id: int) -> bool:
        return self._delete_item(DataCategory.PRODUCTS.value, product_id)

    # -------------------- Paste/Mortar/Concrete Experiments --------------------
    
    def get_experiments_by_type(self, exp_type: str) -> List[Dict[str, Any]]:
        """
        Get experiments for specific type: 'paste_experiments', 'mortar_experiments', 'concrete_experiments'
        """
        return self._get_items(exp_type)

    def add_typed_experiment(self, exp_type: str, data: Union[Dict[str, Any], BaseModelWithConfig]) -> bool:
        if isinstance(data, BaseModelWithConfig):
             if hasattr(data, 'created_at') and not data.created_at:
                 data.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
             item_dict = data.model_dump(mode='json')
        else:
            item_dict = data.copy()
            if "created_at" not in item_dict:
                item_dict["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return self._add_item(exp_type, item_dict)
    
    def update_typed_experiment(self, exp_type: str, exp_id: int, updates: Dict[str, Any]) -> bool:
        updates["last_modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return self._update_item(exp_type, exp_id, updates)
        
    def delete_typed_experiment(self, exp_type: str, exp_id: int) -> bool:
        return self._delete_item(exp_type, exp_id)

    # Wrappers for specific types
    def get_all_paste_experiments(self) -> List[Dict[str, Any]]:
        return self.get_experiments_by_type(DataCategory.PASTE_EXPERIMENTS.value)
    def add_paste_experiment(self, data: Union[Dict[str, Any], PasteExperiment]) -> bool:
        return self.add_typed_experiment(DataCategory.PASTE_EXPERIMENTS.value, data)
    def update_paste_experiment(self, id: int, updates: Dict[str, Any]) -> bool:
        return self.update_typed_experiment(DataCategory.PASTE_EXPERIMENTS.value, id, updates)
    def delete_paste_experiment(self, id: int) -> bool:
        return self.delete_typed_experiment(DataCategory.PASTE_EXPERIMENTS.value, id)
    
    def get_all_mortar_experiments(self) -> List[Dict[str, Any]]:
        return self.get_experiments_by_type(DataCategory.MORTAR_EXPERIMENTS.value)
    def add_mortar_experiment(self, data: Union[Dict[str, Any], MortarExperiment]) -> bool:
        return self.add_typed_experiment(DataCategory.MORTAR_EXPERIMENTS.value, data)
    def update_mortar_experiment(self, id: int, updates: Dict[str, Any]) -> bool:
        return self.update_typed_experiment(DataCategory.MORTAR_EXPERIMENTS.value, id, updates)
    def delete_mortar_experiment(self, id: int) -> bool:
        return self.delete_typed_experiment(DataCategory.MORTAR_EXPERIMENTS.value, id)
    
    def get_all_concrete_experiments(self) -> List[Dict[str, Any]]:
        return self.get_experiments_by_type(DataCategory.CONCRETE_EXPERIMENTS.value)
    def add_concrete_experiment(self, data: Union[Dict[str, Any], ConcreteExperiment]) -> bool:
        return self.add_typed_experiment(DataCategory.CONCRETE_EXPERIMENTS.value, data)
    def update_concrete_experiment(self, id: int, updates: Dict[str, Any]) -> bool:
        return self.update_typed_experiment(DataCategory.CONCRETE_EXPERIMENTS.value, id, updates)
    def delete_concrete_experiment(self, id: int) -> bool:
        return self.delete_typed_experiment(DataCategory.CONCRETE_EXPERIMENTS.value, id)

    # -------------------- Goods Receipt & Shipping --------------------
    def get_all_goods_receipts(self) -> List[Dict[str, Any]]:
        return self._get_items(DataCategory.GOODS_RECEIPTS.value)

    def add_goods_receipt(self, receipt_data: Union[Dict[str, Any], GoodsReceipt]) -> bool:
        if isinstance(receipt_data, GoodsReceipt):
            rec_dict = receipt_data.model_dump(mode='json')
        else:
            rec_dict = receipt_data.copy()
            if isinstance(rec_dict.get("date"), (date, datetime)):
                rec_dict["date"] = rec_dict["date"].strftime("%Y-%m-%d")
        
        if "created_at" not in rec_dict:
             rec_dict["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if "status" not in rec_dict:
             rec_dict["status"] = "draft"
             
        return self._add_item(DataCategory.GOODS_RECEIPTS.value, rec_dict)

    def get_all_shipping_orders(self) -> List[Dict[str, Any]]:
        return self._get_items(DataCategory.SHIPPING_ORDERS.value)

    def add_shipping_order(self, order_data: Union[Dict[str, Any], ShippingOrder]) -> bool:
        if isinstance(order_data, ShippingOrder):
            ord_dict = order_data.model_dump(mode='json')
        else:
            ord_dict = order_data.copy()
            if isinstance(ord_dict.get("date"), (date, datetime)):
                ord_dict["date"] = ord_dict["date"].strftime("%Y-%m-%d")
                
        if "created_at" not in ord_dict:
             ord_dict["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if "status" not in ord_dict:
             ord_dict["status"] = "draft"
             
        return self._add_item(DataCategory.SHIPPING_ORDERS.value, ord_dict)

    # -------------------- BOM Management --------------------
    def get_all_boms(self) -> List[Dict[str, Any]]:
        return self._get_items(DataCategory.BOMS.value)

    def add_bom(self, bom_data: Union[Dict[str, Any], BOM]) -> Optional[int]:
        data = self.load_data()
        boms = data.get(DataCategory.BOMS.value, [])
        
        new_id = max([b.get("id", 0) for b in boms], default=0) + 1
        
        if isinstance(bom_data, BOM):
            bom_data.id = new_id
            if not bom_data.created_at:
                bom_data.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if not bom_data.last_modified:
                bom_data.last_modified = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            final_bom = bom_data.model_dump(mode='json')
        else:
            bom_data["id"] = new_id
            if "created_at" not in bom_data:
                bom_data["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if "last_modified" not in bom_data:
                bom_data["last_modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            try:
                BOM(**bom_data)
            except Exception as e:
                logger.warning(f"BOM validation warning: {e}")
            final_bom = bom_data
        
        boms.append(final_bom)
        data[DataCategory.BOMS.value] = boms
        if self.save_data(data):
            return new_id
        return None

    def update_bom(self, bom_id: int, updated_fields: Dict[str, Any]) -> bool:
        data = self.load_data()
        boms = data.get(DataCategory.BOMS.value, [])
        updated = False
        for i, bom in enumerate(boms):
            if bom.get("id") == bom_id:
                boms[i].update(updated_fields)
                boms[i]["last_modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                updated = True
                break
        if updated:
            data[DataCategory.BOMS.value] = boms
            return self.save_data(data)
        return False
        
    def delete_bom(self, bom_id: int) -> bool:
        data = self.load_data()
        boms = data.get(DataCategory.BOMS.value, [])
        versions = data.get(DataCategory.BOM_VERSIONS.value, [])
        
        new_versions = [v for v in versions if v.get("bom_id") != bom_id]
        new_boms = [b for b in boms if b.get("id") != bom_id]
        
        if len(new_boms) < len(boms):
            data[DataCategory.BOMS.value] = new_boms
            data[DataCategory.BOM_VERSIONS.value] = new_versions
            return self.save_data(data)
        return False

    def get_bom_versions(self, bom_id: int) -> List[Dict[str, Any]]:
        data = self.load_data()
        versions = data.get(DataCategory.BOM_VERSIONS.value, [])
        return [v for v in versions if v.get("bom_id") == bom_id]

    def get_all_bom_versions(self) -> List[Dict[str, Any]]:
        return self._get_items(DataCategory.BOM_VERSIONS.value)

    def get_effective_bom_version(self, bom_id: int, as_of_date: Optional[date] = None) -> Optional[Dict[str, Any]]:
        versions = self.get_bom_versions(bom_id)
        if not versions:
            return None

        if as_of_date is None:
            as_of_date = datetime.now().date()

        def _parse_date(v):
            d = v.get("effective_from")
            if not d:
                return None
            try:
                return datetime.strptime(str(d), "%Y-%m-%d").date()
            except Exception:
                return None

        candidates = []
        for v in versions:
            status = v.get("status")
            if status in ["pending", "rejected"]:
                continue
            if not v.get("lines"):
                continue
            eff = _parse_date(v)
            if eff is None or eff > as_of_date:
                continue
            candidates.append((eff, int(v.get("id", 0)), v))

        if not candidates:
            with_lines = []
            for v in versions:
                status = v.get("status")
                if status in ["pending", "rejected"]:
                    continue
                if v.get("lines"):
                    with_lines.append(v)
            if not with_lines:
                return None
            return sorted(with_lines, key=lambda x: int(x.get("id", 0)), reverse=True)[0]

        candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
        return candidates[0][2]

    def add_bom_version(self, version_data: Union[Dict[str, Any], BOMVersion]) -> Optional[int]:
        data = self.load_data()
        versions = data.get(DataCategory.BOM_VERSIONS.value, [])
        
        user = None
        try:
            if hasattr(st, "session_state"):
                user = st.session_state.get("current_user")
        except Exception:
            user = None

        new_id = max([v.get("id", 0) for v in versions], default=0) + 1
        
        if isinstance(version_data, BOMVersion):
            version_data.id = new_id
            if not version_data.created_at:
                version_data.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            if user:
                if not version_data.created_by:
                    version_data.created_by = user.get("username")
            
            if version_data.status == BOMStatus.PENDING:
                 if user and user.get("role") == UserRole.ADMIN.value:
                      version_data.status = BOMStatus.ACTIVE

            final_ver = version_data.model_dump(mode='json')
            if user:
                final_ver["created_role"] = user.get("role")
        else:
            if "status" not in version_data:
                if user and user.get("role") == UserRole.ADMIN.value:
                    version_data["status"] = BOMStatus.ACTIVE.value
                else:
                    version_data["status"] = BOMStatus.PENDING.value
            if user and "created_by" not in version_data:
                version_data["created_by"] = user.get("username")
                version_data["created_role"] = user.get("role")

            version_data["id"] = new_id
            if "created_at" not in version_data:
                version_data["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            try:
                BOMVersion(**version_data)
            except Exception as e:
                logger.warning(f"BOMVersion validation warning: {e}")
            final_ver = version_data
        
        versions.append(final_ver)
        data[DataCategory.BOM_VERSIONS.value] = versions
        if self.save_data(data):
            return new_id
        return None

    def update_bom_version(self, version_id: int, updated_fields: Dict[str, Any]) -> bool:
        data = self.load_data()
        versions = data.get(DataCategory.BOM_VERSIONS.value, [])
        updated = False
        for i, v in enumerate(versions):
            if v.get("id") == version_id:
                versions[i].update(updated_fields)
                updated = True
                break
        if updated:
            data[DataCategory.BOM_VERSIONS.value] = versions
            return self.save_data(data)
        return False

    def delete_bom_version(self, version_id: int) -> Tuple[bool, str]:
        data = self.load_data()
        versions = data.get(DataCategory.BOM_VERSIONS.value, [])
        orders = data.get(DataCategory.PRODUCTION_ORDERS.value, [])
        target = None
        for v in versions:
            if v.get("id") == version_id:
                target = v
                break
        if not target:
            return False, "BOM版本不存在"
        for o in orders:
            if o.get("bom_version_id") == version_id:
                return False, "存在引用该版本的生产单，无法删除"
        new_versions = [v for v in versions if v.get("id") != version_id]
        data[DataCategory.BOM_VERSIONS.value] = new_versions
        if self.save_data(data):
            return True, "删除成功"
        return False, "保存失败"

    def explode_bom(self, bom_version_id: Union[int, str], target_qty: float = 1000.0) -> List[Dict[str, Any]]:
        """
        BOM 展开计算
        Args:
            bom_version_id: 版本ID
            target_qty: 目标产量
        Returns:
            list: [{item_id, item_name, item_type, required_qty, uom, ...}]
        """
        data = self.load_data()
        versions = data.get(DataCategory.BOM_VERSIONS.value, [])
        
        # 兼容 ID 类型比较 (int vs str)
        target_version = None
        for v in versions:
            if str(v.get("id")) == str(bom_version_id):
                target_version = v
                break
        
        if not target_version:
            logger.warning(f"Explode BOM failed: Version ID {bom_version_id} not found.")
            return []
            
        base_qty = float(target_version.get("yield_base", 1000.0) or 1000.0)
        if base_qty <= 0: base_qty = 1000.0
        
        ratio = target_qty / base_qty
        
        result = []
        lines = target_version.get("lines", [])
        
        if not lines:
            logger.warning(f"Explode BOM: Version {bom_version_id} has no lines.")
            
        for line in lines:
            qty = float(line.get("qty", 0.0) or 0.0) * ratio
            item_type = line.get("item_type")
            item_id = line.get("item_id")
            
            # 基础信息
            item_info = {
                "item_id": item_id,
                "item_type": item_type,
                "required_qty": qty,
                "uom": line.get("uom", UnitType.KG.value),
                "phase": line.get("phase", ""),
                "item_name": line.get("item_name", "Unknown")
            }
            
            result.append(item_info)
            
        return result

    # -------------------- Production & Inventory Extensions (M3) --------------------
    def get_stock_balance(self, material_id: Optional[int] = None) -> Union[float, Dict[int, float]]:
        """获取库存余额（通过汇总台账）"""
        data = self.load_data()
        records = data.get(DataCategory.INVENTORY_RECORDS.value, [])
        
        # 如果指定了 material_id，只计算该物料
        if material_id:
            balance = 0.0
            for r in records:
                if r.get("material_id") == material_id:
                    qty = float(r.get("quantity", 0.0))
                    rtype = r.get("type", "")
                    if rtype in [StockMovementType.IN.value, StockMovementType.PRODUCE_IN.value, StockMovementType.ADJUST_IN.value, StockMovementType.RETURN_IN.value]:
                        balance += qty
                    elif rtype in [StockMovementType.OUT.value, StockMovementType.CONSUME_OUT.value, StockMovementType.ADJUST_OUT.value]:
                        balance -= qty
            return balance
        
        # 否则返回所有物料的余额字典
        balances = {}
        for r in records:
            mid = r.get("material_id")
            if mid not in balances: balances[mid] = 0.0
            
            qty = float(r.get("quantity", 0.0))
            rtype = r.get("type", "")
            if rtype in [StockMovementType.IN.value, StockMovementType.PRODUCE_IN.value, StockMovementType.ADJUST_IN.value, StockMovementType.RETURN_IN.value]:
                balances[mid] += qty
            elif rtype in [StockMovementType.OUT.value, StockMovementType.CONSUME_OUT.value, StockMovementType.ADJUST_OUT.value]:
                balances[mid] -= qty
        return balances

    def get_all_production_orders(self) -> List[Dict[str, Any]]:
        return self._get_items(DataCategory.PRODUCTION_ORDERS.value)

    def add_production_order(self, order_data: Union[Dict[str, Any], ProductionOrder]) -> Optional[int]:
        """添加生产单"""
        data = self.load_data()
        orders = data.get(DataCategory.PRODUCTION_ORDERS.value, [])
        
        new_id = self._get_next_id(orders)
        
        if isinstance(order_data, ProductionOrder):
            order_data.id = new_id
            if not order_data.created_at:
                order_data.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            final_order = order_data.model_dump(mode='json')
        else:
            order_data["id"] = new_id
            if "created_at" not in order_data:
                order_data["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            try:
                ProductionOrder(**order_data)
            except Exception as e:
                logger.warning(f"ProductionOrder validation warning: {e}")
            final_order = order_data
        
        orders.append(final_order)
        data[DataCategory.PRODUCTION_ORDERS.value] = orders
        if self.save_data(data):
            return new_id
        return None

    def update_production_order(self, order_id: int, updated_fields: Dict[str, Any]) -> bool:
        """更新生产单"""
        data = self.load_data()
        orders = data.get(DataCategory.PRODUCTION_ORDERS.value, [])
        updated = False
        for i, order in enumerate(orders):
            if order.get("id") == order_id:
                orders[i].update(updated_fields)
                orders[i]["last_modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                updated = True
                break
        if updated:
            data[DataCategory.PRODUCTION_ORDERS.value] = orders
            return self.save_data(data)
        return False

    def delete_production_order(self, order_id: int) -> Tuple[bool, str]:
        """删除生产单（及其关联的领料单）"""
        data = self.load_data()
        orders = data.get(DataCategory.PRODUCTION_ORDERS.value, [])
        issues = data.get(DataCategory.MATERIAL_ISSUES.value, [])
        
        # 检查是否可以删除
        order = next((o for o in orders if o.get("id") == order_id), None)
        if not order: return False, "生产单不存在"
        
        # 如果已经有领料单过账，则不允许删除
        related_issues = [i for i in issues if i.get("production_order_id") == order_id]
        for issue in related_issues:
            if issue.get("status") == IssueStatus.POSTED.value:
                return False, "无法删除：存在已过账的领料单"
        
        # 删除生产单
        new_orders = [o for o in orders if o.get("id") != order_id]
        # 删除关联的草稿领料单
        new_issues = [i for i in issues if i.get("production_order_id") != order_id]
        
        if len(new_orders) < len(orders):
            data[DataCategory.PRODUCTION_ORDERS.value] = new_orders
            data[DataCategory.MATERIAL_ISSUES.value] = new_issues
            if self.save_data(data):
                return True, "删除成功"
            return False, "保存失败"
        return False, "删除未生效"

    def finish_production_order(self, order_id: int, operator: str = "User") -> Tuple[bool, str]:
        """
        生产单完工入库：
        1. 更新生产单状态为 finished
        2. 根据 BOM 自动生成/更新成品库存 (单位转换: kg -> 吨)
        3. 记录成品入库流水
        """
        data = self.load_data()
        orders = data.get(DataCategory.PRODUCTION_ORDERS.value, [])
        boms = data.get(DataCategory.BOMS.value, [])
        inventory = data.get(DataCategory.PRODUCT_INVENTORY.value, [])
        records = data.get(DataCategory.PRODUCT_INVENTORY_RECORDS.value, [])
        
        target_order = None
        target_idx = -1
        for i, o in enumerate(orders):
            if o.get("id") == order_id:
                target_order = o
                target_idx = i
                break
        
        if not target_order: return False, "生产单不存在"
        if target_order.get("status") == ProductionOrderStatus.FINISHED.value: return False, "生产单已完工"
        
        # 获取计划产量 (这里简化为实际产量=计划产量)
        plan_qty = float(target_order.get("plan_qty", 0.0))
        if plan_qty <= 0: return False, "计划产量无效"
        
        # 查找对应的 BOM 信息以确定产品名称和类型
        bom_id = target_order.get("bom_id")
        target_bom = next((b for b in boms if b.get("id") == bom_id), None)
        
        if not target_bom: return False, "关联 BOM 不存在"
        
        # 构造产品名称
        bom_code = target_bom.get("bom_code", "").strip()
        bom_name = target_bom.get("bom_name", "").strip()
        
        if bom_code:
            product_name = f"{bom_code}-{bom_name}"
        else:
            product_name = bom_name

        product_type = target_bom.get("bom_type", "其他")
        
        # 在 product_inventory 中查找对应产品
        target_prod_idx = -1
        
        # 智能匹配
        candidate_names = [product_name]
        if "-" in product_name:
            candidate_names.append(product_name.split("-", 1)[1])
        
        if product_name == "无碱速凝剂":
            candidate_names.append(PRODUCT_NAME_WJSNJ)
        elif product_name == "有碱速凝剂":
            candidate_names.append(PRODUCT_NAME_YJSNJ)
            
        for i, p in enumerate(inventory):
            if p.get("name") in candidate_names:
                target_prod_idx = i
                break
        
        # 如果产品不存在，自动创建
        if target_prod_idx == -1:
            new_prod_id = self._get_next_id(inventory)
            new_prod = {
                "id": new_prod_id,
                "name": product_name,
                "type": product_type,
                "stock_quantity": 0.0,
                "unit": "吨", # 默认单位
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            inventory.append(new_prod)
            target_prod_idx = len(inventory) - 1
        
        # 更新库存
        prod_unit = inventory[target_prod_idx].get("unit", "吨")
        final_qty, success = convert_quantity(plan_qty, "kg", prod_unit)
        
        if not success:
             logger.warning(f"Finish production unit conversion failed: {plan_qty} kg -> {prod_unit}")
             final_qty = plan_qty
        
        current_stock = float(inventory[target_prod_idx].get("stock_quantity", 0.0))
        new_stock = current_stock + final_qty
        inventory[target_prod_idx]["stock_quantity"] = new_stock
        inventory[target_prod_idx]["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 记录流水
        new_rec_id = self._get_next_id(records)
        records.append({
            "id": new_rec_id,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "product_name": inventory[target_prod_idx]["name"],
            "product_type": product_type,
            "type": StockMovementType.PRODUCE_IN.value,
            "quantity": final_qty,
            "reason": f"生产完工: {target_order.get('order_code')}",
            "operator": operator,
            "snapshot_stock": new_stock,
            "batch_number": target_order.get('order_code')
        })
        
        # 更新订单状态
        orders[target_idx]["status"] = ProductionOrderStatus.FINISHED.value
        orders[target_idx]["finished_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        data[DataCategory.PRODUCTION_ORDERS.value] = orders
        data[DataCategory.PRODUCT_INVENTORY.value] = inventory
        data[DataCategory.PRODUCT_INVENTORY_RECORDS.value] = records
        
        if self.save_data(data):
            return True, f"完工入库成功，库存增加 {final_qty:.3f} {prod_unit}"
        return False, "保存失败"

    def create_issue_from_order(self, order_id: int) -> Optional[int]:
        """根据生产单创建领料单"""
        data = self.load_data()
        orders = data.get(DataCategory.PRODUCTION_ORDERS.value, [])
        order = next((o for o in orders if o.get("id") == order_id), None)
        
        if not order: return None
        
        bom_version_id = order.get("bom_version_id")
        plan_qty = float(order.get("plan_qty", 0.0))
        
        # 计算物料需求
        lines = self.explode_bom(bom_version_id, plan_qty)
        
        # 创建领料单
        issues = data.get(DataCategory.MATERIAL_ISSUES.value, [])
        new_id = max([i.get("id", 0) for i in issues], default=0) + 1
        
        issue_data = {
            "id": new_id,
            "issue_code": f"ISS-{datetime.now().strftime('%Y%m%d')}-{new_id:03d}",
            "production_order_id": order_id,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": IssueStatus.DRAFT.value,
            "lines": lines
        }
        
        issues.append(issue_data)
        data[DataCategory.MATERIAL_ISSUES.value] = issues
        
        if self.save_data(data):
            return new_id
        return None

    def get_material_issues(self) -> List[Dict[str, Any]]:
        return self._get_items(DataCategory.MATERIAL_ISSUES.value)

    def update_material_issue(self, issue_id: int, updated_fields: Dict[str, Any]) -> bool:
        """更新领料单"""
        data = self.load_data()
        issues = data.get(DataCategory.MATERIAL_ISSUES.value, [])
        updated = False
        for i, issue in enumerate(issues):
            if issue.get("id") == issue_id:
                issues[i].update(updated_fields)
                issues[i]["last_modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                updated = True
                break
        if updated:
            data[DataCategory.MATERIAL_ISSUES.value] = issues
            return self.save_data(data)
        return False

    def post_issue(self, issue_id: int, operator: str = "User") -> Tuple[bool, str]:
        """
        领料过账：
        1. 检查状态
        2. 遍历行项目，扣减库存
        3. 记录台账
        4. 更新领料单状态
        """
        data = self.load_data()
        issues = data.get(DataCategory.MATERIAL_ISSUES.value, [])
        materials = data.get(DataCategory.RAW_MATERIALS.value, [])
        records = data.get(DataCategory.INVENTORY_RECORDS.value, [])
        products = data.get(DataCategory.PRODUCT_INVENTORY.value, [])
        product_records = data.get(DataCategory.PRODUCT_INVENTORY_RECORDS.value, [])
        orders = data.get(DataCategory.PRODUCTION_ORDERS.value, [])
        
        target_issue = None
        for issue in issues:
            if issue.get("id") == issue_id:
                target_issue = issue
                break
        
        if not target_issue: return False, "领料单不存在"
        if target_issue.get("status") == IssueStatus.POSTED.value: return False, "领料单已过账"
        
        lines = target_issue.get("lines", [])
        if not lines: return False, "领料单明细为空" # 禁止空过账 (Rule)
        
        # 关联信息
        rel_order_id = target_issue.get("production_order_id")
        rel_bom_id = None
        rel_bom_ver = None
        if rel_order_id:
            ord = next((o for o in orders if o.get("id") == rel_order_id), None)
            if ord:
                rel_bom_id = ord.get("bom_id")
                rel_bom_ver = ord.get("bom_version_id")
        
        for line in lines:
            qty = float(line.get("required_qty", 0.0))
            if qty <= 0: continue
            
            mid = line.get("item_id")
            line_uom = line.get("uom", UnitType.KG.value)
            item_type = line.get("item_type", MaterialType.RAW_MATERIAL.value)
            
            # 区分原材料和成品（半成品）扣减
            if item_type == MaterialType.PRODUCT.value:
                # 处理成品库存扣减 (如领用速凝剂、母液等)
                prod_idx = -1
                current_stock = 0.0
                
                # 尝试通过 ID 匹配
                for idx, p in enumerate(products):
                    if p.get("id") == mid:
                        prod_idx = idx
                        current_stock = float(p.get("stock_quantity", 0.0))
                        break
                
                # 如果 ID 匹配失败，尝试名称匹配 (容错)
                if prod_idx == -1:
                    expected_name = str(line.get("item_name", "") or "").strip()
                    if expected_name:
                         # 这里的模糊匹配逻辑可以简化，或者直接依赖 ID
                        for idx, p in enumerate(products):
                            if str(p.get("name", "") or "").strip() == expected_name:
                                prod_idx = idx
                                current_stock = float(p.get("stock_quantity", 0.0))
                                break
                
                if prod_idx == -1:
                    logger.warning(f"Post issue: Product item {mid} ({line.get('item_name')}) not found in inventory. Skipping stock deduction.")
                    # 也可以选择报错 return False, ...
                else:
                    # 单位转换
                    stock_unit = products[prod_idx].get("unit", UnitType.TON.value)
                    final_qty, success = convert_quantity(qty, line_uom, stock_unit)
                    
                    if not success and normalize_unit(line_uom) != normalize_unit(stock_unit):
                        logger.warning(f"Unit conversion failed in post_issue (product): {qty} {line_uom} -> {stock_unit}")
                    
                    new_stock = current_stock - final_qty
                    products[prod_idx]["stock_quantity"] = new_stock
                    products[prod_idx]["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # 记录成品出库台账
                    reason_note = f"生产领料: {target_issue.get('issue_code')}"
                    if normalize_unit(line_uom) != normalize_unit(stock_unit):
                        reason_note += f" (原: {qty}{line_uom})"
                    
                    new_rec_id = max([r.get("id", 0) for r in product_records], default=0) + 1
                    product_records.append({
                        "id": new_rec_id,
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "product_name": products[prod_idx]["name"],
                        "product_type": products[prod_idx].get("type", "其他"),
                        "type": StockMovementType.CONSUME_OUT.value,
                        "quantity": final_qty,
                        "reason": reason_note,
                        "operator": operator,
                        "snapshot_stock": new_stock,
                        "related_doc_type": "ISSUE",
                        "related_doc_id": issue_id,
                        "related_order_id": rel_order_id,
                        "related_bom_id": rel_bom_id,
                        "related_bom_version_id": rel_bom_ver
                    })
            
            else:
                # 处理原材料库存扣减
                current_stock = 0.0
                mat_idx = -1
                is_water = False
                
                for idx, m in enumerate(materials):
                    if m.get("id") == mid:
                        current_stock = float(m.get("stock_quantity", 0.0))
                        mat_name = m.get("name", "").strip()
                        is_water = mat_name in WATER_MATERIAL_ALIASES
                        mat_idx = idx
                        break
                
                if mat_idx >= 0:
                    stock_unit = materials[mat_idx].get("unit", UnitType.KG.value)
                    final_qty, success = convert_quantity(qty, line_uom, stock_unit)
                    
                    if not success and normalize_unit(line_uom) != normalize_unit(stock_unit):
                         logger.warning(f"Unit conversion failed in post_issue: {qty} {line_uom} -> {stock_unit}")
    
                    new_stock = current_stock
                    if not is_water:
                        new_stock = current_stock - final_qty
                        materials[mat_idx]["stock_quantity"] = new_stock
                        materials[mat_idx]["last_stock_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # 写入台账
                    reason_note = f"生产领料: {target_issue.get('issue_code')}"
                    if normalize_unit(line_uom) != normalize_unit(stock_unit):
                        reason_note += f" (原: {qty}{line_uom})"
                    
                    # Safe ID generation
                    new_rec_id = self._get_next_id(records)
                    records.append({
                        "id": new_rec_id,
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "material_id": mid,
                        "type": StockMovementType.CONSUME_OUT.value,
                        "quantity": final_qty,
                        "reason": reason_note,
                        "operator": operator,
                        "related_doc_type": "ISSUE",
                        "related_doc_id": issue_id,
                        "snapshot_stock": new_stock
                    })
        
        # 更新领料单状态
        target_issue["status"] = IssueStatus.POSTED.value
        target_issue["posted_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        data[DataCategory.INVENTORY_RECORDS.value] = records
        data[DataCategory.PRODUCT_INVENTORY_RECORDS.value] = product_records
        data[DataCategory.RAW_MATERIALS.value] = materials
        data[DataCategory.PRODUCT_INVENTORY.value] = products
        # material_issues updated via reference
        
        if self.save_data(data):
            return True, "过账成功"
        return False, "保存失败"

    def repair_material_issues(self) -> bool:
        """修复领料单BOM版本和行项目"""
        data = self.load_data()
        issues = data.get(DataCategory.MATERIAL_ISSUES.value, [])
        orders = data.get(DataCategory.PRODUCTION_ORDERS.value, [])
        versions = data.get(DataCategory.BOM_VERSIONS.value, [])
        updated = False
        for i, issue in enumerate(issues):
            if issue.get("status") != IssueStatus.DRAFT.value:
                continue
            oid = issue.get("production_order_id")
            order = next((o for o in orders if o.get("id") == oid), None)
            if not order:
                continue
            bom_ver_id = order.get("bom_version_id")
            bom_id = order.get("bom_id")
            plan_qty = float(order.get("plan_qty", 0.0))
            lines = self.explode_bom(bom_ver_id, plan_qty)
            if not lines:
                same_bom_versions = []
                for v in versions:
                    if str(v.get("bom_id")) != str(bom_id):
                        continue
                    status = v.get("status")
                    if status in [BOMStatus.PENDING.value, BOMStatus.REJECTED.value]:
                        continue
                    same_bom_versions.append(v)
                fallback_ver = None
                for v in reversed(same_bom_versions):
                    if v.get("lines"):
                        fallback_ver = v
                        break
                if fallback_ver:
                    for j, o in enumerate(orders):
                        if o.get("id") == oid:
                            orders[j]["bom_version_id"] = fallback_ver["id"]
                            orders[j]["last_modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            break
                    data[DataCategory.PRODUCTION_ORDERS.value] = orders
                    lines = self.explode_bom(fallback_ver["id"], plan_qty)
            if lines:
                for line in lines:
                    if "item_type" not in line:
                        line["item_type"] = MaterialType.RAW_MATERIAL.value
                issues[i]["lines"] = lines
                issues[i]["last_modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                updated = True
        if updated:
            data[DataCategory.MATERIAL_ISSUES.value] = issues
            return self.save_data(data)
        return True

    # -------------------- 母液管理CRUD操作 --------------------
    def get_all_mother_liquors(self) -> List[Dict[str, Any]]:
        """获取所有母液"""
        data = self.load_data()
        return data.get(DataCategory.MOTHER_LIQUORS.value, [])
    
    def get_mother_liquor(self, ml_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取单个母液"""
        mls = self.get_all_mother_liquors()
        for ml in mls:
            if ml.get("id") == ml_id:
                return ml
        return None

    def add_mother_liquor(self, ml_data: Union[Dict[str, Any], MotherLiquor]) -> bool:
        """添加新母液"""
        data = self.load_data()
        mls = data.get(DataCategory.MOTHER_LIQUORS.value, [])
        
        # 生成新ID
        new_id = self._get_next_id(mls)
        
        if isinstance(ml_data, MotherLiquor):
            ml_data.id = new_id
            if not ml_data.created_at:
                ml_data.created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
            final_ml = ml_data.model_dump(mode='json')
        else:
            ml_data["id"] = new_id
            
            # Validation attempt
            try:
                MotherLiquor(**ml_data)
            except Exception as e:
                logger.warning(f"MotherLiquor validation warning: {e}")
                
            final_ml = ml_data
        
        mls.append(final_ml)
        data[DataCategory.MOTHER_LIQUORS.value] = mls
        return self.save_data(data)

    def update_mother_liquor(self, ml_id: int, updated_fields: Dict[str, Any]) -> bool:
        """更新母液信息"""
        data = self.load_data()
        mls = data.get(DataCategory.MOTHER_LIQUORS.value, [])
        
        updated = False
        for i, ml in enumerate(mls):
            if ml.get("id") == ml_id:
                # 更新字段
                mls[i].update(updated_fields)
                mls[i]["last_modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                updated = True
                break
        
        if updated:
            data[DataCategory.MOTHER_LIQUORS.value] = mls
            return self.save_data(data)
        return False

    def delete_mother_liquor(self, ml_id: int) -> bool:
        """删除母液"""
        data = self.load_data()
        mls = data.get(DataCategory.MOTHER_LIQUORS.value, [])
        
        new_mls = [m for m in mls if m.get("id") != ml_id]
        
        if len(new_mls) < len(mls):
            data[DataCategory.MOTHER_LIQUORS.value] = new_mls
            return self.save_data(data)
        return False

    # -------------------- 原材料库存管理 --------------------
    def get_all_raw_materials(self) -> List[Dict[str, Any]]:
        """获取所有原材料"""
        data = self.load_data()
        return data.get(DataCategory.RAW_MATERIALS.value, [])
    
    def add_raw_material(self, material_data: Union[Dict[str, Any], RawMaterial]) -> tuple[bool, str]:
        """添加新原材料"""
        data = self.load_data()
        materials = data.get(DataCategory.RAW_MATERIALS.value, [])
        
        # Determine name to check for duplicates
        if isinstance(material_data, RawMaterial):
            name = material_data.name
        else:
            name = material_data.get("name")
        
        # 检查名称是否重复
        if name:
            for m in materials:
                if m.get("name") == name:
                    return False, f"原材料名称 '{name}' 已存在"
        
        # 生成新ID
        new_id = self._get_next_id(materials)
        
        if isinstance(material_data, RawMaterial):
            material_data.id = new_id
            if not material_data.created_date:
                material_data.created_date = datetime.now().strftime("%Y-%m-%d")
            mat_dict = material_data.model_dump(mode='json')
        else:
            material_data["id"] = new_id
            material_data["created_date"] = datetime.now().strftime("%Y-%m-%d")
            
            # Try validation
            try:
                RawMaterial(**material_data)
            except Exception as e:
                logger.warning(f"RawMaterial validation warning: {e}")
                
            mat_dict = material_data
        
        materials.append(mat_dict)
        data[DataCategory.RAW_MATERIALS.value] = materials
        if self.save_data(data):
            return True, "添加成功"
        return False, "保存失败"
    
    def update_raw_material(self, material_id: int, updated_fields: Dict[str, Any]) -> tuple[bool, str]:
        """更新原材料信息"""
        try:
            data = self.load_data()
            materials = data.get(DataCategory.RAW_MATERIALS.value, [])
            
            # 验证名称唯一性
            new_name = updated_fields.get("name")
            if new_name:
                # 检查是否有其他原材料使用了该名称
                for m in materials:
                    if m.get("id") != material_id and m.get("name") == new_name:
                        msg = f"原材料名称 '{new_name}' 已存在"
                        logger.warning(f"Update failed: {msg}")
                        return False, msg
            
            old_name = None
            updated = False
            for i, material in enumerate(materials):
                if material.get("id") == material_id:
                    old_name = material.get("name")
                    # 更新字段
                    materials[i].update(updated_fields)
                    updated = True
                    break
            
            if updated:
                # 如果名称发生了变化，更新所有引用该名称的记录
                if new_name and old_name and new_name != old_name:
                    logger.info(f"Raw material renamed from '{old_name}' to '{new_name}'. Updating references...")
                    self._update_raw_material_references(data, old_name, new_name)
                
                data[DataCategory.RAW_MATERIALS.value] = materials
                if self.save_data(data):
                    logger.info(f"Raw material {material_id} updated successfully.")
                    return True, "更新成功"
                else:
                    msg = "保存数据失败"
                    logger.error(f"{msg} after updating raw material {material_id}.")
                    return False, msg
            
            msg = f"原材料 ID {material_id} 未找到"
            logger.warning(msg)
            return False, msg
        except Exception as e:
            msg = f"系统错误: {e}"
            logger.error(f"Error updating raw material {material_id}: {e}")
            return False, msg
    
    def _update_raw_material_references(self, data: Dict[str, Any], old_name: str, new_name: str) -> None:
        """更新所有引用旧原材料名称的记录"""
        try:
            count = 0
            # 1. 更新合成实验记录
            records = data.get(DataCategory.SYNTHESIS_RECORDS.value, [])
            for record in records:
                modified = False
                # 检查所有物料列表
                for key in ["reactor_materials", "a_materials", "b_materials"]:
                    items = record.get(key, [])
                    if items:
                        for item in items:
                            if item.get("material_name") == old_name:
                                item["material_name"] = new_name
                                modified = True
                                count += 1
                
                if modified:
                    record["last_modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 2. 更新成品减水剂配方
            products = data.get(DataCategory.PRODUCTS.value, [])
            for product in products:
                modified = False
                # Check "ingredients" (standard) and "composition" (legacy)
                for key in ["ingredients", "composition"]:
                    items = product.get(key, [])
                    if items:
                        for item in items:
                            if item.get("name") == old_name:
                                item["name"] = new_name
                                modified = True
                                count += 1
                
                if modified:
                    product["last_modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            if count > 0:
                logger.info(f"Updated {count} references from '{old_name}' to '{new_name}'")
            else:
                logger.info(f"No references found for '{old_name}'")
                
        except Exception as e:
            logger.error(f"Error updating references: {e}")
    
    def delete_raw_material(self, material_id: int) -> tuple[bool, str]:
        """删除原材料"""
        try:
            data = self.load_data()
            materials = data.get(DataCategory.RAW_MATERIALS.value, [])
            
            # 获取要删除的原材料名称
            material_to_delete = next((m for m in materials if m.get("id") == material_id), None)
            if not material_to_delete:
                logger.warning(f"Delete failed: Raw material ID {material_id} not found.")
                return False, "原材料不存在"
            
            material_name = material_to_delete.get("name")
            
            # 检查引用
            # 1. 检查合成实验记录
            records = data.get(DataCategory.SYNTHESIS_RECORDS.value, [])
            for record in records:
                for key in ["reactor_materials", "a_materials", "b_materials"]:
                    items = record.get(key, [])
                    for item in items:
                        if item.get("material_name") == material_name:
                            msg = f"无法删除：该原材料在合成实验配方 {record.get('formula_id', '未知')} 中被使用"
                            logger.warning(f"Delete blocked: {msg}")
                            return False, msg
            
            # 2. 检查成品减水剂
            products = data.get(DataCategory.PRODUCTS.value, [])
            for product in products:
                # 检查 ingredients
                ingredients = product.get("ingredients", [])
                for item in ingredients:
                    if item.get("name") == material_name:
                        msg = f"无法删除：该原材料在成品 {product.get('product_name', '未知')} 中被使用"
                        logger.warning(f"Delete blocked: {msg}")
                        return False, msg
                
                # 检查 composition (兼容旧数据)
                composition = product.get("composition", [])
                for item in composition:
                    if item.get("name") == material_name:
                        msg = f"无法删除：该原材料在成品 {product.get('product_name', '未知')} 中被使用"
                        logger.warning(f"Delete blocked: {msg}")
                        return False, msg

            new_materials = [m for m in materials if m.get("id") != material_id]
            
            if len(new_materials) < len(materials):
                data[DataCategory.RAW_MATERIALS.value] = new_materials
                if self.save_data(data):
                    logger.info(f"Raw material {material_id} ({material_name}) deleted successfully.")
                    return True, "删除成功"
                else:
                    logger.error(f"Failed to save data after deleting raw material {material_id}.")
                    return False, "保存数据失败"
            
            logger.warning(f"Delete failed: Raw material {material_id} deletion not effective.")
            return False, "删除操作未生效"
            
        except Exception as e:
            logger.error(f"Error deleting raw material {material_id}: {e}")
            return False, f"系统错误: {str(e)}"

    def add_inventory_record(self, record_data: Union[Dict[str, Any], InventoryRecord], update_master_stock: bool = True) -> tuple[bool, str]:
        """添加库存变动记录"""
        try:
            data = self.load_data()
            
            # Convert model to dict if necessary
            if isinstance(record_data, InventoryRecord):
                 rec_dict = record_data.model_dump(mode='json')
            else:
                 rec_dict = record_data

            # 1. Update Stock in Raw Material
            materials = data.get(DataCategory.RAW_MATERIALS.value, [])
            material_found = False
            current_stock = 0.0
            
            material_id = rec_dict.get("material_id")
            if isinstance(material_id, str) and material_id.isdigit():
                material_id = int(material_id)
            
            for i, m in enumerate(materials):
                if m.get("id") == material_id:
                    # Check if material is "Water" (no stock tracking)
                    mat_name = m.get("name", "").strip()
                    is_water = mat_name in WATER_MATERIAL_ALIASES
                    
                    if not is_water:
                        current_stock = float(m.get("stock_quantity", 0.0))
                        
                        if update_master_stock:
                            change = float(rec_dict.get("quantity", 0.0))
                            
                            # Use Enum or string
                            rec_type = rec_dict.get("type")
                            if rec_type == "out" or rec_type == StockMovementType.OUT:
                                current_stock -= change
                            else:
                                current_stock += change
                            
                            materials[i]["stock_quantity"] = current_stock
                            materials[i]["last_stock_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    material_found = True
                    break
            
            if not material_found:
                return False, "原材料不存在"

            # 2. Add Record to Ledger
            records = data.get(DataCategory.INVENTORY_RECORDS.value, [])
            # Safe ID generation: Ignore string IDs (UUIDs) to prevent comparison errors
            new_id = self._get_next_id(records)
            
            if isinstance(record_data, InventoryRecord):
                record_data.id = new_id
                record_data.snapshot_stock = current_stock
                if not record_data.created_at:
                    record_data.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                final_record = record_data.model_dump(mode='json')
            else:
                rec_dict["id"] = new_id
                rec_dict["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                rec_dict["snapshot_stock"] = current_stock
                
                # Validation attempt
                try:
                    InventoryRecord(**rec_dict)
                except Exception as e:
                    logger.warning(f"InventoryRecord validation warning: {e}")
                
                final_record = rec_dict
            
            records.append(final_record)
            
            data[DataCategory.RAW_MATERIALS.value] = materials
            data[DataCategory.INVENTORY_RECORDS.value] = records
            
            if self.save_data(data):
                return True, "库存更新成功"
            return False, "保存失败"
        except Exception as e:
            logger.error(f"Error adding inventory record: {e}")
            return False, f"系统错误: {str(e)}"

    def get_inventory_records(self, material_id: Optional[Union[int, str]] = None) -> List[Dict[str, Any]]:
        """获取库存记录"""
        data = self.load_data()
        records = data.get(DataCategory.INVENTORY_RECORDS.value, [])
        if material_id:
            if isinstance(material_id, str) and material_id.isdigit():
                material_id = int(material_id)
            return [r for r in records if r.get("material_id") == material_id]
        return records

    # -------------------- 成品库存管理 --------------------
    def get_product_inventory(self) -> List[Dict[str, Any]]:
        """获取所有成品库存"""
        data = self.load_data()
        return data.get(DataCategory.PRODUCT_INVENTORY.value, [])

    def add_product_inventory_record(self, record_data: Union[Dict[str, Any], ProductInventoryRecord], update_master_stock: bool = True) -> Tuple[bool, str]:
        """添加成品库存变动记录"""
        data = self.load_data()
        
        # 兼容 Pydantic
        if isinstance(record_data, ProductInventoryRecord):
            rec_dict = record_data.model_dump(mode='json')
        else:
            rec_dict = record_data
            
        product_name = rec_dict.get("product_name")
        product_type = rec_dict.get("product_type", "其他")
        qty = float(rec_dict.get("quantity", 0.0))
        op_type = rec_dict.get("type")
        
        inventory = data.get(DataCategory.PRODUCT_INVENTORY.value, [])
        records = data.get(DataCategory.PRODUCT_INVENTORY_RECORDS.value, [])
        
        # 1. 更新主库存
        target_item = None
        target_idx = -1
        
        # 智能匹配
        candidate_names = [product_name]
        if "-" in product_name:
            candidate_names.append(product_name.split("-", 1)[1])
        
        for i, item in enumerate(inventory):
            if item.get("product_name") in candidate_names:
                target_item = item
                target_idx = i
                break
        
        DEFAULT_UNIT = "吨"
        
        if not target_item:
            # 新增产品
            if op_type == StockMovementType.OUT.value:
                return False, "库存不足 (产品不存在)"
            
            target_item = {
                "id": self._get_next_id(inventory),
                "product_name": product_name,
                "type": product_type,
                "stock_quantity": qty,
                "unit": DEFAULT_UNIT,
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            inventory.append(target_item)
        else:
            # 更新现有产品
            current_val = float(target_item.get("stock_quantity") or target_item.get("current_stock") or 0.0)
            
            if update_master_stock:
                if op_type in [StockMovementType.IN.value, StockMovementType.PRODUCE_IN.value, StockMovementType.RETURN_IN.value, StockMovementType.ADJUST_IN.value]:
                    current_val += qty
                elif op_type in [StockMovementType.OUT.value, StockMovementType.SHIP_OUT.value, StockMovementType.CONSUME_OUT.value, StockMovementType.ADJUST_OUT.value]:
                    current_val -= qty
                
                target_item["stock_quantity"] = current_val
                if "current_stock" in target_item:
                    del target_item["current_stock"]
                
                target_item["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
        # 2. 添加流水记录
        new_rec_id = self._get_next_id(records)
        rec_dict["id"] = new_rec_id
        if "created_at" not in rec_dict:
            rec_dict["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        rec_dict["snapshot_stock"] = target_item.get("stock_quantity")
        
        # 再次校验完整性（可选）
        if isinstance(record_data, ProductInventoryRecord):
             # 如果输入是对象，更新对象ID
             record_data.id = new_rec_id
             record_data.snapshot_stock = rec_dict["snapshot_stock"]
             if not record_data.created_at:
                 record_data.created_at = rec_dict["created_at"]
        
        records.append(rec_dict)
        
        data[DataCategory.PRODUCT_INVENTORY.value] = inventory
        data[DataCategory.PRODUCT_INVENTORY_RECORDS.value] = records
        
        if self.save_data(data):
            return True, "库存更新成功"
        return False, "保存失败"

    def update_product_inventory_item(self, product_id: int, updates: Dict[str, Any]) -> Tuple[bool, str]:
        """更新产品信息（支持级联更新名称和类型）"""
        data = self.load_data()
        inventory = data.get(DataCategory.PRODUCT_INVENTORY.value, [])
        records = data.get(DataCategory.PRODUCT_INVENTORY_RECORDS.value, [])
        
        target_item = None
        target_idx = -1
        
        for i, item in enumerate(inventory):
            if item.get("id") == product_id:
                target_item = item
                target_idx = i
                break
        
        if target_item:
            # 检查是否需要级联更新
            old_name = target_item.get("product_name") or target_item.get("name")
            old_type = target_item.get("type")
            new_name = updates.get("product_name", old_name)
            new_type = updates.get("type", old_type)
            
            need_cascade = (new_name != old_name) or (new_type != old_type)
            
            # 更新主数据
            inventory[target_idx].update(updates)
            if "product_name" in updates and "name" in inventory[target_idx]:
                 del inventory[target_idx]["name"]
            
            inventory[target_idx]["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            if need_cascade:
                count = 0
                for record in records:
                    if record.get("product_name") == old_name and record.get("product_type") == old_type:
                        record["product_name"] = new_name
                        record["product_type"] = new_type
                        count += 1
                if count > 0:
                    logger.info(f"Cascaded update for product {product_id}: {count} records updated.")

            data[DataCategory.PRODUCT_INVENTORY.value] = inventory
            data[DataCategory.PRODUCT_INVENTORY_RECORDS.value] = records 
            if self.save_data(data):
                return True, "更新成功"
            return False, "保存失败"
        return False, "未找到指定产品"
            
    def get_product_inventory_records(self) -> List[Dict[str, Any]]:
        """获取产品库存流水"""
        data = self.load_data()
        return data.get(DataCategory.PRODUCT_INVENTORY_RECORDS.value, [])
    
    def ensure_raw_material_from_product(self, product_name: str, unit_target: str = UnitType.KG.value) -> Tuple[bool, str]:
        data = self.load_data()
        inventory = data.get(DataCategory.PRODUCT_INVENTORY.value, [])
        materials = data.get(DataCategory.RAW_MATERIALS.value, [])
        records = data.get(DataCategory.INVENTORY_RECORDS.value, [])
        
        prod = next((p for p in inventory if str(p.get("product_name") or p.get("name") or "").strip() == str(product_name).strip()), None)
        
        if not prod:
            return False, f"未找到成品库存：{product_name}"
        # 检查原材料是否已存在
        mat = next((m for m in materials if str(m.get("name", "")).strip() == str(product_name).strip()), None)
        if not mat:
            new_id = self._get_next_id(materials)
            mat = {
                "id": new_id,
                "name": product_name,
                "supplier": "",
                "spec": "",
                "unit": unit_target,
                "stock_quantity": 0.0,
                "created_date": datetime.now().strftime("%Y-%m-%d"),
                "last_stock_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            materials.append(mat)
        # 同步库存：将成品库存数量换算为原材料库存
        qty_ton = float(prod.get("stock_quantity") or prod.get("current_stock") or 0.0)
        prod_unit = prod.get("unit", UnitType.TON.value)
        final_qty, success = convert_quantity(qty_ton, prod_unit, unit_target)
        if not success and normalize_unit(prod_unit) != normalize_unit(unit_target):
            logger.warning(f"Unit conversion failed when migrating product to raw: {qty_ton} {prod_unit} -> {unit_target}")
            # 默认换算：吨->kg
            if normalize_unit(prod_unit) in ["ton", "吨"] and normalize_unit(unit_target) in ["kg", "千克"]:
                final_qty = qty_ton * 1000.0
            else:
                final_qty = qty_ton
        # 更新原材料库存为换算后的值
        for i, m in enumerate(materials):
            if m.get("name") == product_name:
                materials[i]["stock_quantity"] = final_qty
                materials[i]["last_stock_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                break
        # 生成一条台账记录以体现初始同步（adjust_in）
        new_rec_id = self._get_next_id(records)
        records.append({
            "id": new_rec_id,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "material_id": mat.get("id"),
            "type": StockMovementType.ADJUST_IN.value,
            "quantity": final_qty,
            "unit": unit_target,
            "reason": f"迁移自成品库存: {product_name}",
            "operator": "System",
            "snapshot_stock": final_qty
        })
        data[DataCategory.RAW_MATERIALS.value] = materials
        data[DataCategory.INVENTORY_RECORDS.value] = records
        self.save_data(data)
        return True, "迁移成功"
    
    def cleanup_migrated_raw_materials(self, names: List[str]) -> Tuple[bool, str]:
        data = self.load_data()
        materials = data.get(DataCategory.RAW_MATERIALS.value, [])
        records = data.get(DataCategory.INVENTORY_RECORDS.value, [])
        name_set = set(str(n).strip() for n in names if n)
        target_ids = [m.get("id") for m in materials if str(m.get("name", "")).strip() in name_set]
        new_materials = [m for m in materials if str(m.get("name", "")).strip() not in name_set]
        new_records = []
        for r in records:
            mid = r.get("material_id")
            reason = str(r.get("reason", "") or "")
            if mid in target_ids and reason.startswith("迁移自成品库存:"):
                continue
            new_records.append(r)
        data[DataCategory.RAW_MATERIALS.value] = new_materials
        data[DataCategory.INVENTORY_RECORDS.value] = new_records
        self.save_data(data)
        return True, f"已清除 {len(target_ids)} 项及相关台账"

    def delete_product_inventory_item(self, product_id: int) -> bool:
        """删除产品库存条目"""
        data = self.load_data()
        inventory = data.get(DataCategory.PRODUCT_INVENTORY.value, [])
        
        new_inventory = [item for item in inventory if item.get("id") != product_id]
        
        if len(new_inventory) < len(inventory):
            data[DataCategory.PRODUCT_INVENTORY.value] = new_inventory
            return self.save_data(data)
        return False

    # -------------------- User/Audit Methods --------------------
    def get_admin_password(self) -> Optional[str]:
        data = self.load_data()
        settings = data.get("system_settings") or {}
        salt = settings.get("admin_password_salt")
        pwd_hash = settings.get("admin_password_hash")
        if salt and pwd_hash:
            return None
        try:
            val = os.environ.get("APP_ADMIN_PASSWORD")
            if val:
                return val
        except Exception:
            pass
        try:
            sec = getattr(st, "secrets", None)
            if sec and "admin_password" in sec:
                return sec["admin_password"]
        except Exception:
            pass
        return "admin"
    
    def verify_admin_password(self, password: str) -> bool:
        if not password:
            return False
        data = self.load_data()
        settings = data.get("system_settings") or {}
        salt = settings.get("admin_password_salt")
        pwd_hash = settings.get("admin_password_hash")
        if salt and pwd_hash:
            calc = self._hash_password(str(password), str(salt))
            return secrets.compare_digest(str(calc), str(pwd_hash))
        expected = self.get_admin_password()
        return secrets.compare_digest(str(password), str(expected))
    
    def set_admin_password(self, password: str) -> bool:
        data = self.load_data()
        settings = data.get("system_settings") or {}
        salt = secrets.token_hex(16)
        pwd_hash = self._hash_password(str(password), str(salt))
        settings["admin_password_salt"] = salt
        settings["admin_password_hash"] = pwd_hash
        data["system_settings"] = settings
        return self.save_data(data)
    
    def _hash_password(self, password: str, salt: str) -> str:
        import hashlib
        return hashlib.sha256((password + salt).encode()).hexdigest()

    def audit_and_fix_product_consumption_mismatch(self) -> List[Dict[str, Any]]:
        data = self.load_data()
        records = data.get(DataCategory.PRODUCT_INVENTORY_RECORDS.value, [])
        issues = data.get(DataCategory.MATERIAL_ISSUES.value, [])
        inventory = data.get(DataCategory.PRODUCT_INVENTORY.value, [])
        issue_map = {}
        for iss in issues:
            code = iss.get("issue_code")
            if code:
                issue_map[code] = iss
        def parse_issue_code(reason):
            s = str(reason or "")
            if "生产领料:" in s:
                part = s.split("生产领料:", 1)[1].strip()
                part = part.split("(", 1)[0].strip()
                return part
            return ""
        def expect_norm(name):
            n = str(name or "").strip()
            if n.startswith("YJSNJ-") or n in ["有碱速凝剂", "碱速凝剂"]:
                return "YJSNJ-有碱速凝剂", "有碱速凝剂"
            if n.startswith("WJSNJ-") or n in ["无碱速凝剂"]:
                return "WJSNJ-无碱速凝剂", "无碱速凝剂"
            return n, ""
        def find_item_idx(nm, tp):
            for i, it in enumerate(inventory):
                if str(it.get("product_name") or it.get("name") or "") == nm and str(it.get("type", "")) == tp:
                    return i
            return -1
        before_snapshot = { (it.get("product_name") or it.get("name"), it.get("type")): float(it.get("stock_quantity") or it.get("current_stock") or 0.0) for it in inventory }
        fixed = []
        for i, r in enumerate(records):
            if r.get("type") != StockMovementType.OUT.value:
                continue
            pname = r.get("product_name")
            ptype = r.get("product_type", ProductCategory.OTHER.value)
            reason = r.get("reason", "")
            code = parse_issue_code(reason)
            if not code:
                continue
            iss = issue_map.get(code)
            if not iss:
                continue
            lines = iss.get("lines", [])
            exp_name = ""
            for ln in lines:
                if ln.get("item_type") == "product":
                    exp_name = ln.get("item_name", "")
                    break
            if not exp_name:
                continue
            exp_norm_name, exp_norm_type = expect_norm(exp_name)
            
            # 这里的逻辑比较特定，暂时保留原字符串判断，或者后续优化
            if ptype == "无碱速凝剂" and exp_norm_type == "有碱速凝剂":
                qty = float(r.get("quantity", 0.0))
                old_idx = find_item_idx(pname, ptype)
                new_idx = find_item_idx(exp_norm_name, exp_norm_type)
                if new_idx == -1:
                    new_id = max([p.get("id", 0) for p in inventory], default=0) + 1
                    inventory.append({
                        "id": new_id,
                        "product_name": exp_norm_name,
                        "type": exp_norm_type,
                        "stock_quantity": 0.0,
                        "unit": UnitType.TON.value,
                        "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                    new_idx = len(inventory) - 1
                if old_idx >= 0:
                    old_stock = float(inventory[old_idx].get("stock_quantity") or inventory[old_idx].get("current_stock") or 0.0)
                    inventory[old_idx]["stock_quantity"] = old_stock + qty
                    if "current_stock" in inventory[old_idx]: del inventory[old_idx]["current_stock"]
                    inventory[old_idx]["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                new_stock = float(inventory[new_idx].get("stock_quantity") or inventory[new_idx].get("current_stock") or 0.0)
                inventory[new_idx]["stock_quantity"] = new_stock - qty
                if "current_stock" in inventory[new_idx]: del inventory[new_idx]["current_stock"]
                inventory[new_idx]["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                r["product_name"] = exp_norm_name
                r["product_type"] = exp_norm_type
                r["snapshot_stock"] = float(inventory[new_idx].get("stock_quantity", 0.0))
                fixed.append({
                    "record_id": r.get("id"),
                    "issue_code": code,
                    "old_name": pname,
                    "old_type": ptype,
                    "new_name": exp_norm_name,
                    "new_type": exp_norm_type,
                    "quantity": qty
                })
        data[DataCategory.PRODUCT_INVENTORY.value] = inventory
        data[DataCategory.PRODUCT_INVENTORY_RECORDS.value] = records
        self.save_data(data)
        after_snapshot = { (it.get("product_name") or it.get("name"), it.get("type")): float(it.get("stock_quantity") or it.get("current_stock") or 0.0) for it in inventory }
        report_rows = []
        for f in fixed:
            old_key = (f["old_name"], f["old_type"])
            new_key = (f["new_name"], f["new_type"])
            report_rows.append({
                "记录ID": f["record_id"],
                "领料单号": f["issue_code"],
                "修正数量(吨)": round(f["quantity"], 6),
                "原产品": f["old_name"],
                "原类型": f["old_type"],
                "新产品": f["new_name"],
                "新类型": f["new_type"],
                "原产品修正后库存(吨)": round(after_snapshot.get(old_key, 0.0), 6),
                "新产品修正后库存(吨)": round(after_snapshot.get(new_key, 0.0), 6)
            })
        return report_rows

    def normalize_product_aliases(self):
        """
        规范产品名称别名：
        - 将有碱/无碱速凝剂的别名合并为带编码的规范名称
        - 合并库存条目，累计库存数量
        - 级联更新产品库存台账中的产品名称
        Returns:
            list[dict]: 调整摘要
        """
        data = self.load_data()
        inventory = data.get(DataCategory.PRODUCT_INVENTORY.value, [])
        records = data.get(DataCategory.PRODUCT_INVENTORY_RECORDS.value, [])
        
        alias_map = {
            "YJSNJ-有碱速凝剂": ["有碱速凝剂", "碱速凝剂"],
            "WJSNJ-无碱速凝剂": ["无碱速凝剂"]
        }
        
        adjustments = []
        
        for canonical, aliases in alias_map.items():
            group_names = [canonical] + aliases
            group_items = [item for item in inventory if str(item.get("product_name") or item.get("name")) in group_names]
            if not group_items:
                adjustments.append({
                    "规范名称": canonical,
                    "合并来源": ",".join(aliases),
                    "原库存合计(吨)": 0.0,
                    "合并后库存(吨)": 0.0,
                    "删除条目数": 0,
                    "更新台账记录数": 0
                })
                continue
            
            total_stock = sum(float(it.get("stock_quantity") or it.get("current_stock") or 0.0) for it in group_items)
            canonical_item = next((it for it in group_items if (it.get("product_name") or it.get("name")) == canonical), None)
            
            if canonical_item is None:
                canonical_item = {
                    "id": self._get_next_id(inventory),
                    "product_name": canonical,
                    "type": "有碱速凝剂" if "有碱速凝剂" in canonical else ("无碱速凝剂" if "无碱速凝剂" in canonical else group_items[0].get("type", ProductCategory.OTHER.value)),
                    "stock_quantity": 0.0,
                    "unit": group_items[0].get("unit", UnitType.TON.value),
                    "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                inventory.append(canonical_item)
            
            prev_total = float(canonical_item.get("stock_quantity") or canonical_item.get("current_stock") or 0.0)
            canonical_item["stock_quantity"] = total_stock
            if "current_stock" in canonical_item: del canonical_item["current_stock"]
            canonical_item["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            desired_type = "有碱速凝剂" if "有碱速凝剂" in canonical else "无碱速凝剂"
            canonical_item["type"] = desired_type
            
            removed_count = 0
            new_inventory = []
            for it in inventory:
                pname = it.get("product_name") or it.get("name")
                if pname in aliases:
                    removed_count += 1
                    continue
                if pname == canonical:
                    it["type"] = desired_type
                new_inventory.append(it)
            inventory = new_inventory
            
            updated_records = 0
            for r in records:
                if r.get("product_name") in group_names:
                    r["product_name"] = canonical
                    r["product_type"] = desired_type
                    updated_records += 1
            
            adjustments.append({
                "规范名称": canonical,
                "合并来源": ",".join(aliases),
                "原库存合计(吨)": round(prev_total, 4),
                "合并后库存(吨)": round(total_stock, 4),
                "删除条目数": removed_count,
                "更新台账记录数": updated_records
            })
        
        data[DataCategory.PRODUCT_INVENTORY.value] = inventory
        data[DataCategory.PRODUCT_INVENTORY_RECORDS.value] = records
        self.save_data(data)
        return adjustments
