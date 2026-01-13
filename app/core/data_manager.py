"""数据管理模块 - 主要数据管理类"""

import json
import shutil
from pathlib import Path
from datetime import datetime
import pandas as pd
import base64
from io import BytesIO
import streamlit as st

from core.timeline_manager import TimelineManager
from utils.logger import logger
from utils.unit_helper import convert_quantity, normalize_unit

class DataManager:
    """统一数据管理器"""
    
    def __init__(self):
        # Point to data.json in the project root (polycarb_project/data.json)
        # app/core/data_manager.py -> app/core -> app -> polycarb_project
        self.data_file = Path(__file__).parent.parent.parent / "data.json"
        self.backup_dir = Path(__file__).parent.parent.parent / "backups"
        self._ensure_valid_data_file()
        self._ensure_backup_dir()
        
        # 初始化备份状态
        if "last_backup_time" not in st.session_state:
            st.session_state.last_backup_time = None
    
    def _ensure_valid_data_file(self):
        """确保数据文件存在且格式有效"""
        try:
            # 尝试加载数据，验证文件是否有效
            if self.data_file.exists():
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # 检查数据结构
                if not isinstance(data, dict):
                    raise ValueError("数据格式不正确")
                # 确保有所有必要的数据结构
                self._ensure_data_structure(data)
                return True
        except (json.JSONDecodeError, ValueError, FileNotFoundError):
            # 如果文件无效或不存在，创建初始数据
            print("数据文件无效或不存在，正在创建初始数据...")
            initial_data = self.get_initial_data()
            return self.save_data(initial_data)
        return False
    
    def _ensure_data_structure(self, data):
        """确保数据结构完整"""
        required_keys = [
            "projects", "experiments", "performance_data",
            "raw_materials", "synthesis_records", "products",
            "paste_experiments", "mortar_experiments", "concrete_experiments",
            "mother_liquors",
            # SAP/BOM Modules
            "inventory_records", "boms", "bom_versions", 
            "production_orders", "material_issues", "goods_receipts"
        ]
        
        for key in required_keys:
            if key not in data:
                if key == "performance_data":
                    data[key] = {"synthesis": [], "paste": [], "mortar": [], "concrete": []}
                else:
                    data[key] = []
        
        return data
    
    def _ensure_backup_dir(self):
        """确保备份目录存在"""
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def load_data(self):
        """从JSON文件加载所有数据"""
        try:
            if self.data_file.exists():
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return self._ensure_data_structure(data)
            else:
                return self.get_initial_data()
        except Exception as e:
            st.error(f"读取数据失败: {e}")
            # 返回空数据结构
            return self.get_initial_data()
    
    def save_data(self, data):
        """保存数据到JSON文件，并创建备份"""
        try:
            # 确保目录存在
            self.data_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 临时文件路径
            temp_file = self.data_file.with_suffix('.tmp')
            
            # 写入临时文件
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            
            # 替换原文件
            temp_file.replace(self.data_file)
            
            # 检查是否需要创建自动备份
            self.check_and_create_auto_backup()
            
            return True
        except Exception as e:
            st.error(f"保存数据失败: {e}")
            return False
    
    def check_and_create_auto_backup(self):
        """检查并创建自动备份（每小时最多一次）"""
        try:
            # 获取当前时间
            now = datetime.now()
            
            # 检查上次备份时间
            last_backup = st.session_state.get("last_backup_time")
            
            should_backup = False
            if last_backup is None:
                should_backup = True
            elif isinstance(last_backup, datetime):
                # 如果上次备份超过1小时
                if (now - last_backup).total_seconds() > 3600:
                    should_backup = True
            else:
                # 兼容旧的date类型或其它情况
                should_backup = True
                
            if should_backup:
                # 创建备份
                self.create_backup()
                # 更新备份时间
                st.session_state.last_backup_time = now
        except Exception as e:
            print(f"检查备份失败: {e}")
    
    def create_backup(self):
        """创建数据备份"""
        try:
            if self.data_file.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = self.backup_dir / f"data_backup_{timestamp}.json"
                
                # 复制文件
                shutil.copy2(self.data_file, backup_file)
                
                # 清理旧的备份文件（保留最近30天的备份）
                self._cleanup_old_backups()
                
                return True
        except Exception as e:
            print(f"创建备份失败: {e}")
            return False
    
    def _cleanup_old_backups(self, max_backups=30):
        """清理旧的备份文件"""
        try:
            backup_files = list(self.backup_dir.glob("data_backup_*.json"))
            
            if len(backup_files) > max_backups:
                # 按修改时间排序，删除最旧的文件
                backup_files.sort(key=lambda x: x.stat().st_mtime)
                files_to_delete = backup_files[:-max_backups]
                
                for file in files_to_delete:
                    file.unlink()
                    
        except Exception as e:
            print(f"清理备份文件失败: {e}")


    
    # -------------------- 获取初始数据 --------------------
    def get_initial_data(self):
        """返回初始数据结构"""
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
                },
                {
                    "id": 2,
                    "name": "PC-002性能测试",
                    "leader": "李四",
                    "start_date": "2024-01-10",
                    "end_date": "2024-02-15",
                    "status": "已完成",
                    "progress": 100,
                    "description": "测试不同配方性能"
                }
            ],
            "experiments": [
                {
                    "id": 1,
                    "name": "PC-001-合成实验1",
                    "type": "合成实验",
                    "project_id": 1,
                    "planned_date": "2024-01-20",
                    "actual_date": "2024-01-20",
                    "priority": "高",
                    "status": "已完成",
                    "description": "第一轮合成实验"
                }
            ],
            "performance_data": {
                "synthesis": [
                    {
                        "id": 1,
                        "batch": "PC-001",
                        "water_reduction": 18.5,
                        "solid_content": 40,
                        "slump_flow": 650,
                        "test_date": "2024-01-10",
                        "sample_id": "PC-001-20240110"
                    }
                ],
                "paste": [],
                "mortar": [],
                "concrete": []
            },
            "raw_materials": [],
            "synthesis_records": [],
            "products": [],
            "paste_experiments": [],
            "mortar_experiments": [],
            "concrete_experiments": [],
            "mother_liquors": [],
            "inventory_records": [],
            "boms": [],
            "bom_versions": [],
            "production_orders": [],
            "material_issues": [],
            "goods_receipts": []
        }
    
    # -------------------- 项目CRUD操作 --------------------
    def get_all_projects(self):
        """获取所有项目"""
        data = self.load_data()
        return data.get("projects", [])
    
    def get_next_project_id(self):
        """获取下一个可用的项目ID"""
        projects = self.get_all_projects()
        if not projects:
            return 1
        return max([p.get("id", 0) for p in projects]) + 1
    
    def get_project(self, project_id):
        """根据ID获取单个项目"""
        projects = self.get_all_projects()
        for project in projects:
            if project.get("id") == project_id:
                return project
        return None
    
    def add_project(self, project_data):
        """添加新项目"""
        data = self.load_data()
        projects = data.get("projects", [])
        
        # 生成新ID
        new_id = max([p.get("id", 0) for p in projects], default=0) + 1
        project_data["id"] = new_id
        
        # 确保日期是字符串格式
        for date_field in ["start_date", "end_date"]:
            if date_field in project_data and hasattr(project_data[date_field], 'strftime'):
                project_data[date_field] = project_data[date_field].strftime("%Y-%m-%d")
        
        projects.append(project_data)
        data["projects"] = projects
        success = self.save_data(data)
        return success
    
    def update_project(self, project_id, updated_fields):
        """更新项目信息"""
        data = self.load_data()
        projects = data.get("projects", [])
        
        updated = False
        for i, project in enumerate(projects):
            if project.get("id") == project_id:
                # 更新字段
                projects[i].update(updated_fields)
                updated = True
                break
        
        if updated:
            data["projects"] = projects
            return self.save_data(data)
        return False
    
    def delete_project(self, project_id):
        """根据ID删除项目"""
        try:
            data = self.load_data()
            projects = data.get("projects", [])
            
            # 记录删除前的数量
            original_count = len(projects)
            
            # 过滤掉要删除的项目
            new_projects = [p for p in projects if p.get("id") != project_id]
            
            # 检查是否真的删除了项目
            if len(new_projects) < original_count:
                data["projects"] = new_projects
                success = self.save_data(data)
                if success:
                    print(f"成功删除项目 ID: {project_id}")
                    return True
                else:
                    print(f"保存数据失败，项目 ID: {project_id} 删除未生效")
                    return False
            else:
                print(f"未找到项目 ID: {project_id}")
                return False
        except Exception as e:
            print(f"删除项目时出错: {e}")
            return False
    
    # -------------------- 项目时间线相关方法 --------------------
    def get_project_timeline(self, project_id):
        """
        获取项目时间线信息（使用TimelineManager）
        参数:
            project_id: 项目ID
        返回:
            时间线信息字典，如果项目不存在返回None
        """
        # 1. 获取项目数据
        project_data = self.get_project(project_id)
        if not project_data:
            print(f"警告: 未找到项目ID {project_id}")
            return None
        
        # 2. 使用TimelineManager进行计算
        return TimelineManager.calculate_timeline(project_data)
    
    # -------------------- 实验CRUD操作 --------------------
    def get_all_experiments(self):
        """获取所有实验"""
        data = self.load_data()
        return data.get("experiments", [])
    
    def add_experiment(self, experiment_data):
        """添加新实验"""
        data = self.load_data()
        experiments = data.get("experiments", [])
        
        # 生成新ID
        new_id = max([e.get("id", 0) for e in experiments], default=0) + 1
        experiment_data["id"] = new_id
        
        # 确保日期是字符串格式
        for date_field in ["planned_date", "actual_date"]:
            if date_field in experiment_data and experiment_data[date_field]:
                if hasattr(experiment_data[date_field], 'strftime'):
                    experiment_data[date_field] = experiment_data[date_field].strftime("%Y-%m-%d")
        
        experiments.append(experiment_data)
        data["experiments"] = experiments
        return self.save_data(data)
    
    def update_experiment(self, experiment_id, updated_fields):
        """更新实验信息"""
        data = self.load_data()
        experiments = data.get("experiments", [])
        
        updated = False
        for i, exp in enumerate(experiments):
            if exp.get("id") == experiment_id:
                # 更新字段
                experiments[i].update(updated_fields)
                updated = True
                break
        
        if updated:
            data["experiments"] = experiments
            return self.save_data(data)
        return False
    
    def delete_experiment(self, experiment_id):
        """根据ID删除实验"""
        data = self.load_data()
        experiments = data.get("experiments", [])
        
        new_experiments = [e for e in experiments if e.get("id") != experiment_id]
        
        if len(new_experiments) < len(experiments):
            data["experiments"] = new_experiments
            return self.save_data(data)
        return False
    
    # -------------------- 数据记录模块CRUD操作 --------------------
    # 原材料管理
    def get_all_raw_materials(self):
        """获取所有原材料"""
        data = self.load_data()
        return data.get("raw_materials", [])
    
    def add_raw_material(self, material_data):
        """添加新原材料"""
        data = self.load_data()
        materials = data.get("raw_materials", [])
        
        # 检查名称是否重复
        name = material_data.get("name")
        if name:
            for m in materials:
                if m.get("name") == name:
                    return False, f"原材料名称 '{name}' 已存在"
        
        # 生成新ID
        new_id = max([m.get("id", 0) for m in materials], default=0) + 1
        material_data["id"] = new_id
        material_data["created_date"] = datetime.now().strftime("%Y-%m-%d")
        
        materials.append(material_data)
        data["raw_materials"] = materials
        if self.save_data(data):
            return True, "添加成功"
        return False, "保存失败"
    
    def update_raw_material(self, material_id, updated_fields):
        """更新原材料信息"""
        try:
            data = self.load_data()
            materials = data.get("raw_materials", [])
            
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
                
                data["raw_materials"] = materials
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
    
    def _update_raw_material_references(self, data, old_name, new_name):
        """更新所有引用旧原材料名称的记录"""
        try:
            count = 0
            # 1. 更新合成实验记录
            records = data.get("synthesis_records", [])
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
            products = data.get("products", [])
            for product in products:
                modified = False
                composition = product.get("composition", []) # Note: In data_recording.py it is 'ingredients', checking data structure in data_manager.py... 
                # Wait, data_recording.py uses 'ingredients'. 
                # Let's check get_initial_data or add_product to be sure what key is used.
                # In data_recording.py add_product: "ingredients": valid_ingredients
                # So here it should be "ingredients" not "composition"?
                # Let's check lines 469-480 in original file.
                # It said: composition = product.get("composition", [])
                # I should fix this if it's wrong.
                
                # Checking add_product in data_recording.py (from previous read):
                # "ingredients": valid_ingredients
                
                # So "composition" might be wrong if I assumed it earlier.
                # Let's check lines 469-480 in the current file content I read.
                # Yes, it says composition = product.get("composition", [])
                
                # I should change "composition" to "ingredients" here as well to be correct.
                # Or check both?
                
                # Let's use "ingredients" as seen in data_recording.py.
                
                ingredients = product.get("ingredients", [])
                if ingredients:
                    for item in ingredients:
                        if item.get("name") == old_name:
                            item["name"] = new_name
                            modified = True
                            count += 1
                
                # Also check "composition" for backward compatibility if needed?
                composition = product.get("composition", [])
                if composition:
                     for item in composition:
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
    
    def delete_raw_material(self, material_id):
        """删除原材料"""
        try:
            data = self.load_data()
            materials = data.get("raw_materials", [])
            
            # 获取要删除的原材料名称
            material_to_delete = next((m for m in materials if m.get("id") == material_id), None)
            if not material_to_delete:
                logger.warning(f"Delete failed: Raw material ID {material_id} not found.")
                return False, "原材料不存在"
            
            material_name = material_to_delete.get("name")
            
            # 检查引用
            # 1. 检查合成实验记录
            records = data.get("synthesis_records", [])
            for record in records:
                for key in ["reactor_materials", "a_materials", "b_materials"]:
                    items = record.get(key, [])
                    for item in items:
                        if item.get("material_name") == material_name:
                            msg = f"无法删除：该原材料在合成实验配方 {record.get('formula_id', '未知')} 中被使用"
                            logger.warning(f"Delete blocked: {msg}")
                            return False, msg
            
            # 2. 检查成品减水剂
            products = data.get("products", [])
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
                data["raw_materials"] = new_materials
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

    # -------------------- 库存管理 (SAP Lite) --------------------
    def add_inventory_record(self, record_data):
        """添加库存变动记录"""
        try:
            data = self.load_data()
            
            # 1. Update Stock in Raw Material
            materials = data.get("raw_materials", [])
            material_found = False
            current_stock = 0.0
            
            material_id = record_data.get("material_id")
            if isinstance(material_id, str) and material_id.isdigit():
                material_id = int(material_id)
            
            for i, m in enumerate(materials):
                if m.get("id") == material_id:
                    # Check if material is "Water" (no stock tracking)
                    mat_name = m.get("name", "").strip()
                    water_names = ["水", "自来水", "纯水", "去离子水", "工业用水", "生产用水"]
                    is_water = mat_name in water_names
                    
                    if not is_water:
                        current_stock = float(m.get("stock_quantity", 0.0))
                        change = float(record_data.get("quantity", 0.0))
                        
                        if record_data.get("type") == "out":
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
            records = data.get("inventory_records", [])
            new_id = max([r.get("id", 0) for r in records], default=0) + 1
            record_data["id"] = new_id
            record_data["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            record_data["snapshot_stock"] = current_stock
            
            records.append(record_data)
            
            data["raw_materials"] = materials
            data["inventory_records"] = records
            
            if self.save_data(data):
                return True, "库存更新成功"
            return False, "保存失败"
        except Exception as e:
            logger.error(f"Error adding inventory record: {e}")
            return False, f"系统错误: {str(e)}"

    def get_inventory_records(self, material_id=None):
        """获取库存记录"""
        data = self.load_data()
        records = data.get("inventory_records", [])
        if material_id:
            if isinstance(material_id, str) and material_id.isdigit():
                material_id = int(material_id)
            return [r for r in records if r.get("material_id") == material_id]
        return records
    
    # -------------------- 母液管理CRUD操作 --------------------
    def get_all_mother_liquors(self):
        """获取所有母液"""
        data = self.load_data()
        return data.get("mother_liquors", [])
    
    def get_mother_liquor(self, ml_id):
        """根据ID获取单个母液"""
        mls = self.get_all_mother_liquors()
        for ml in mls:
            if ml.get("id") == ml_id:
                return ml
        return None

    def add_mother_liquor(self, ml_data):
        """添加新母液"""
        data = self.load_data()
        mls = data.get("mother_liquors", [])
        
        # 生成新ID
        new_id = max([m.get("id", 0) for m in mls], default=0) + 1
        ml_data["id"] = new_id
        
        # 确保日期字符串格式 (如果需要)
        # created_at 已经在调用端处理了，这里可以再次确认或不做处理
        
        mls.append(ml_data)
        data["mother_liquors"] = mls
        return self.save_data(data)

    def update_mother_liquor(self, ml_id, updated_fields):
        """更新母液信息"""
        data = self.load_data()
        mls = data.get("mother_liquors", [])
        
        updated = False
        for i, ml in enumerate(mls):
            if ml.get("id") == ml_id:
                # 更新字段
                mls[i].update(updated_fields)
                mls[i]["last_modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                updated = True
                break
        
        if updated:
            data["mother_liquors"] = mls
            return self.save_data(data)
        return False

    def delete_mother_liquor(self, ml_id):
        """删除母液"""
        data = self.load_data()
        mls = data.get("mother_liquors", [])
        
        new_mls = [m for m in mls if m.get("id") != ml_id]
        
        if len(new_mls) < len(mls):
            data["mother_liquors"] = new_mls
            return self.save_data(data)
        return False
    
    # -------------------- 合成实验记录CRUD操作 --------------------
    def get_synthesis_experiment(self, exp_id):
        """获取单个合成实验记录"""
        data = self.load_data()
        records = data.get("synthesis_records", [])
        for record in records:
            if record.get("id") == exp_id:
                return record
        return None

    def get_all_synthesis_experiments(self):
        """获取所有合成实验（别名方法，兼容调用）"""
        return self.get_all_synthesis_records()
        
    def get_all_synthesis_records(self):
        """获取所有合成实验记录"""
        data = self.load_data()
        return data.get("synthesis_records", [])
    
    def add_synthesis_record(self, record_data):
        """添加新合成实验记录"""
        data = self.load_data()
        records = data.get("synthesis_records", [])
        
        # 生成新ID
        new_id = max([r.get("id", 0) for r in records], default=0) + 1
        record_data["id"] = new_id
        record_data["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        record_data["last_modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        records.append(record_data)
        data["synthesis_records"] = records
        return self.save_data(data)
    
    def delete_synthesis_record(self, record_id):
        """删除合成实验记录"""
        data = self.load_data()
        records = data.get("synthesis_records", [])
        
        new_records = [r for r in records if r.get("id") != record_id]
        
        if len(new_records) < len(records):
            data["synthesis_records"] = new_records
            return self.save_data(data)
        return False
    
    # 成品减水剂
    def get_all_products(self):
        """获取所有成品减水剂"""
        data = self.load_data()
        return data.get("products", [])

    def check_product_name_exists(self, name, exclude_id=None):
        """检查成品名称是否已存在（不区分大小写）"""
        products = self.get_all_products()
        name = name.strip().lower()
        for product in products:
            if exclude_id is not None and product.get("id") == exclude_id:
                continue
            if product.get("product_name", "").strip().lower() == name:
                return True
        return False
    
    def add_product(self, product_data):
        """添加新成品减水剂"""
        # 检查名称唯一性
        if self.check_product_name_exists(product_data.get("product_name", "")):
             raise ValueError(f"成品名称 '{product_data.get('product_name')}' 已存在")

        data = self.load_data()
        products = data.get("products", [])
        
        # 生成新ID
        new_id = max([p.get("id", 0) for p in products], default=0) + 1
        product_data["id"] = new_id
        product_data["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        products.append(product_data)
        data["products"] = products
        return self.save_data(data)
    
    def delete_product(self, product_id):
        """删除成品减水剂"""
        data = self.load_data()
        products = data.get("products", [])
        
        new_products = [p for p in products if p.get("id") != product_id]
        
        if len(new_products) < len(products):
            data["products"] = new_products
            return self.save_data(data)
        return False

    def update_product(self, product_id, updated_fields):
        """更新成品减水剂"""
        # 如果更新了名称，检查唯一性
        if "product_name" in updated_fields:
             if self.check_product_name_exists(updated_fields["product_name"], exclude_id=product_id):
                 raise ValueError(f"成品名称 '{updated_fields['product_name']}' 已存在")

        data = self.load_data()
        products = data.get("products", [])
        updated = False
        for i, product in enumerate(products):
            if product.get("id") == product_id:
                new_product = dict(product)
                new_product.update(updated_fields)
                new_product["id"] = product_id
                if "created_at" not in new_product and product.get("created_at"):
                    new_product["created_at"] = product.get("created_at")
                new_product["last_modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                products[i] = new_product
                updated = True
                break
        if updated:
            data["products"] = products
            return self.save_data(data)
        return False

    # -------------------- BOM 管理 (M2) --------------------
    # Ensure this section is loaded
    def get_all_boms(self):
        """获取所有BOM主数据"""
        data = self.load_data()
        return data.get("boms", [])

    def add_bom(self, bom_data):
        """添加BOM主数据"""
        data = self.load_data()
        boms = data.get("boms", [])
        
        new_id = max([b.get("id", 0) for b in boms], default=0) + 1
        bom_data["id"] = new_id
        bom_data["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        bom_data["last_modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        boms.append(bom_data)
        data["boms"] = boms
        if self.save_data(data):
            return new_id
        return None

    def update_bom(self, bom_id, updated_fields):
        """更新BOM主数据"""
        data = self.load_data()
        boms = data.get("boms", [])
        updated = False
        for i, bom in enumerate(boms):
            if bom.get("id") == bom_id:
                boms[i].update(updated_fields)
                boms[i]["last_modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                updated = True
                break
        if updated:
            data["boms"] = boms
            return self.save_data(data)
        return False
        
    def delete_bom(self, bom_id):
        """删除BOM（软删除或硬删除，这里做硬删除但要检查版本）"""
        # 实际业务中建议检查是否有生产单引用
        data = self.load_data()
        boms = data.get("boms", [])
        versions = data.get("bom_versions", [])
        
        # 级联删除版本
        new_versions = [v for v in versions if v.get("bom_id") != bom_id]
        new_boms = [b for b in boms if b.get("id") != bom_id]
        
        if len(new_boms) < len(boms):
            data["boms"] = new_boms
            data["bom_versions"] = new_versions
            return self.save_data(data)
        return False

    def get_bom_versions(self, bom_id):
        """获取指定BOM的所有版本"""
        data = self.load_data()
        versions = data.get("bom_versions", [])
        return [v for v in versions if v.get("bom_id") == bom_id]

    def add_bom_version(self, version_data):
        """添加BOM版本"""
        data = self.load_data()
        versions = data.get("bom_versions", [])
        
        new_id = max([v.get("id", 0) for v in versions], default=0) + 1
        version_data["id"] = new_id
        version_data["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        versions.append(version_data)
        data["bom_versions"] = versions
        if self.save_data(data):
            return new_id
        return None

    def update_bom_version(self, version_id, updated_fields):
        """更新BOM版本"""
        data = self.load_data()
        versions = data.get("bom_versions", [])
        updated = False
        for i, v in enumerate(versions):
            if v.get("id") == version_id:
                versions[i].update(updated_fields)
                updated = True
                break
        if updated:
            data["bom_versions"] = versions
            return self.save_data(data)
        return False

    def explode_bom(self, bom_version_id, target_qty=1000.0):
        """
        BOM 展开计算
        Args:
            bom_version_id: 版本ID
            target_qty: 目标产量
        Returns:
            list: [{item_id, item_name, item_type, required_qty, uom, ...}]
        """
        data = self.load_data()
        versions = data.get("bom_versions", [])
        
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
                "uom": line.get("uom", "kg"),
                "phase": line.get("phase", ""),
                "item_name": line.get("item_name", "Unknown")
            }
            
            result.append(item_info)
            
        return result
    
    # -------------------- 生产与库存扩展 (M3) --------------------
    def get_stock_balance(self, material_id=None):
        """获取库存余额（通过汇总台账）"""
        data = self.load_data()
        records = data.get("inventory_records", [])
        
        # 如果指定了 material_id，只计算该物料
        if material_id:
            balance = 0.0
            for r in records:
                if r.get("material_id") == material_id:
                    qty = float(r.get("quantity", 0.0))
                    rtype = r.get("type", "")
                    if rtype in ["in", "produce_in", "adjust_in", "return_in"]:
                        balance += qty
                    elif rtype in ["out", "consume_out", "adjust_out"]:
                        balance -= qty
            return balance
        
        # 否则返回所有物料的余额字典
        balances = {}
        for r in records:
            mid = r.get("material_id")
            if mid not in balances: balances[mid] = 0.0
            
            qty = float(r.get("quantity", 0.0))
            rtype = r.get("type", "")
            if rtype in ["in", "produce_in", "adjust_in", "return_in"]:
                balances[mid] += qty
            elif rtype in ["out", "consume_out", "adjust_out"]:
                balances[mid] -= qty
        return balances

    def add_production_order(self, order_data):
        """添加生产单"""
        data = self.load_data()
        orders = data.get("production_orders", [])
        
        new_id = max([o.get("id", 0) for o in orders], default=0) + 1
        order_data["id"] = new_id
        order_data["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        orders.append(order_data)
        data["production_orders"] = orders
        if self.save_data(data):
            return new_id
        return None

    def update_production_order(self, order_id, updated_fields):
        """更新生产单"""
        data = self.load_data()
        orders = data.get("production_orders", [])
        updated = False
        for i, order in enumerate(orders):
            if order.get("id") == order_id:
                orders[i].update(updated_fields)
                orders[i]["last_modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                updated = True
                break
        if updated:
            data["production_orders"] = orders
            return self.save_data(data)
        return False
        
    def get_all_production_orders(self):
        """获取所有生产单"""
        data = self.load_data()
        return data.get("production_orders", [])

    def delete_production_order(self, order_id):
        """删除生产单（及其关联的领料单）"""
        data = self.load_data()
        orders = data.get("production_orders", [])
        issues = data.get("material_issues", [])
        
        # 检查是否可以删除
        order = next((o for o in orders if o.get("id") == order_id), None)
        if not order: return False, "生产单不存在"
        
        # 如果已经有领料单过账，则不允许删除
        related_issues = [i for i in issues if i.get("production_order_id") == order_id]
        for issue in related_issues:
            if issue.get("status") == "posted":
                return False, "无法删除：存在已过账的领料单"
        
        # 删除生产单
        new_orders = [o for o in orders if o.get("id") != order_id]
        # 删除关联的草稿领料单
        new_issues = [i for i in issues if i.get("production_order_id") != order_id]
        
        if len(new_orders) < len(orders):
            data["production_orders"] = new_orders
            data["material_issues"] = new_issues
            if self.save_data(data):
                return True, "删除成功"
            return False, "保存失败"
        return False, "删除未生效"

    def create_issue_from_order(self, order_id):
        """
        根据生产单创建领料单（建议）
        Returns:
            int: 新领料单ID
        """
        data = self.load_data()
        orders = data.get("production_orders", [])
        order = next((o for o in orders if o.get("id") == order_id), None)
        
        if not order: return None
        
        # 1. 找到对应的 BOM 版本
        bom_version_id = order.get("bom_version_id")
        plan_qty = float(order.get("plan_qty", 0.0))
        
        # 2. 展开 BOM
        lines = self.explode_bom(bom_version_id, plan_qty)
        
        # 3. 生成领料单
        issues = data.get("material_issues", [])
        new_id = max([i.get("id", 0) for i in issues], default=0) + 1
        
        issue_data = {
            "id": new_id,
            "issue_code": f"ISS-{datetime.now().strftime('%Y%m%d')}-{new_id:04d}",
            "production_order_id": order_id,
            "status": "draft",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "lines": lines  # 直接使用展开的行作为建议领料行
        }
        
        issues.append(issue_data)
        data["material_issues"] = issues
        
        if self.save_data(data):
            return new_id
        return None

    def get_material_issues(self, order_id=None):
        """获取领料单"""
        data = self.load_data()
        issues = data.get("material_issues", [])
        if order_id:
            return [i for i in issues if i.get("production_order_id") == order_id]
        return issues
        
    def update_material_issue(self, issue_id, updated_fields):
        """更新领料单（通常是更新实发数量）"""
        data = self.load_data()
        issues = data.get("material_issues", [])
        updated = False
        for i, issue in enumerate(issues):
            if issue.get("id") == issue_id:
                issues[i].update(updated_fields)
                updated = True
                break
        if updated:
            data["material_issues"] = issues
            return self.save_data(data)
        return False

    def post_issue(self, issue_id, operator="System"):
        """
        领料过账：
        1. 锁定领料单 status=posted
        2. 生成 inventory_records (type=consume_out)
        3. 更新库存
        """
        data = self.load_data()
        issues = data.get("material_issues", [])
        target_issue = None
        for issue in issues:
            if issue.get("id") == issue_id:
                target_issue = issue
                break
        
        if not target_issue: return False, "领料单不存在"
        if target_issue.get("status") == "posted": return False, "领料单已过账"
        
        # 准备批量写入台账
        records = data.get("inventory_records", [])
        materials = data.get("raw_materials", [])
        
        # 遍历行项目
        for line in target_issue.get("lines", []):
            qty = float(line.get("required_qty", 0.0)) # 或者是实发数量字段
            if qty <= 0: continue
            
            mid = line.get("item_id")
            line_uom = line.get("uom", "kg")
            
            # 更新原材料库存
            current_stock = 0.0
            mat_idx = -1
            is_water = False
            
            for idx, m in enumerate(materials):
                if m.get("id") == mid:
                    current_stock = float(m.get("stock_quantity", 0.0))
                    mat_name = m.get("name", "").strip()
                    water_names = ["水", "自来水", "纯水", "去离子水", "工业用水", "生产用水"]
                    is_water = mat_name in water_names
                    mat_idx = idx
                    break
            
            # 即使没找到物料（可能被删），只要ID在也应该记录？或者报错？
            # 这里假设ID必须存在
            if mat_idx >= 0:
                # 单位转换
                stock_unit = materials[mat_idx].get("unit", "kg")
                final_qty, success = convert_quantity(qty, line_uom, stock_unit)
                
                if not success and normalize_unit(line_uom) != normalize_unit(stock_unit):
                     logger.warning(f"Unit conversion failed in post_issue: {qty} {line_uom} -> {stock_unit}")

                new_stock = current_stock
                if not is_water:
                    new_stock = current_stock - final_qty
                    materials[mat_idx]["stock_quantity"] = new_stock
                    materials[mat_idx]["last_stock_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # 写入台账 (记录转换后的数量，并备注原始数量)
                reason_note = f"生产领料: {target_issue.get('issue_code')}"
                if normalize_unit(line_uom) != normalize_unit(stock_unit):
                    reason_note += f" (原: {qty}{line_uom})"
                
                new_rec_id = max([r.get("id", 0) for r in records], default=0) + 1
                records.append({
                    "id": new_rec_id,
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "material_id": mid,
                    "type": "consume_out",
                    "quantity": final_qty,
                    "reason": reason_note,
                    "operator": operator,
                    "related_doc_type": "ISSUE",
                    "related_doc_id": issue_id,
                    "snapshot_stock": new_stock
                })
        
        # 更新领料单状态
        target_issue["status"] = "posted"
        target_issue["posted_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        data["inventory_records"] = records
        data["raw_materials"] = materials
        # material_issues 已经在 target_issue 引用中修改了
        
        if self.save_data(data):
            return True, "过账成功"
        return False, "保存失败"

    def cancel_issue_posting(self, issue_id, operator="System"):
        """
        撤销领料过账：
        1. 检查状态是否为 posted
        2. 生成冲销台账 (type=return_in, reason=撤销领料)
        3. 恢复库存
        4. 状态回滚为 draft
        """
        data = self.load_data()
        issues = data.get("material_issues", [])
        target_issue = None
        for issue in issues:
            if issue.get("id") == issue_id:
                target_issue = issue
                break
        
        if not target_issue: return False, "领料单不存在"
        if target_issue.get("status") != "posted": return False, "只有已过账的领料单可以撤销"
        
        records = data.get("inventory_records", [])
        materials = data.get("raw_materials", [])
        
        # 遍历行项目进行回滚
        for line in target_issue.get("lines", []):
            qty = float(line.get("required_qty", 0.0))
            if qty <= 0: continue
            
            mid = line.get("item_id")
            line_uom = line.get("uom", "kg")
            
            # 更新原材料库存（加回）
            current_stock = 0.0
            mat_idx = -1
            is_water = False
            
            for idx, m in enumerate(materials):
                if m.get("id") == mid:
                    current_stock = float(m.get("stock_quantity", 0.0))
                    mat_name = m.get("name", "").strip()
                    water_names = ["水", "自来水", "纯水", "去离子水", "工业用水", "生产用水"]
                    is_water = mat_name in water_names
                    mat_idx = idx
                    break
            
            if mat_idx >= 0:
                # 单位转换
                stock_unit = materials[mat_idx].get("unit", "kg")
                final_qty, success = convert_quantity(qty, line_uom, stock_unit)

                if not success and normalize_unit(line_uom) != normalize_unit(stock_unit):
                     logger.warning(f"Unit conversion failed in cancel_issue: {qty} {line_uom} -> {stock_unit}")

                new_stock = current_stock
                if not is_water:
                    new_stock = current_stock + final_qty # 恢复库存
                    materials[mat_idx]["stock_quantity"] = new_stock
                    materials[mat_idx]["last_stock_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # 写入冲销台账
                reason_note = f"撤销领料: {target_issue.get('issue_code')}"
                if normalize_unit(line_uom) != normalize_unit(stock_unit):
                    reason_note += f" (原: {qty}{line_uom})"

                new_rec_id = max([r.get("id", 0) for r in records], default=0) + 1
                records.append({
                    "id": new_rec_id,
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "material_id": mid,
                    "type": "return_in", # 视为退料入库/冲销
                    "quantity": final_qty,
                    "reason": reason_note,
                    "operator": operator,
                    "related_doc_type": "ISSUE_CANCEL",
                    "related_doc_id": issue_id,
                    "snapshot_stock": new_stock
                })
        
        # 状态回滚
        target_issue["status"] = "draft"
        target_issue["last_modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        data["inventory_records"] = records
        data["raw_materials"] = materials
        
        if self.save_data(data):
            return True, "撤销成功，库存已恢复"
        return False, "保存失败"
        
    # 净浆实验
    def get_all_paste_experiments(self):
        """获取所有净浆实验"""
        data = self.load_data()
        return data.get("paste_experiments", [])
    
    def add_paste_experiment(self, experiment_data):
        """添加新净浆实验"""
        data = self.load_data()
        experiments = data.get("paste_experiments", [])
        
        # 生成新ID
        new_id = max([e.get("id", 0) for e in experiments], default=0) + 1
        experiment_data["id"] = new_id
        experiment_data["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        experiments.append(experiment_data)
        data["paste_experiments"] = experiments
        return self.save_data(data)
    
    def delete_paste_experiment(self, experiment_id):
        """删除净浆实验"""
        data = self.load_data()
        experiments = data.get("paste_experiments", [])
        
        new_experiments = [e for e in experiments if e.get("id") != experiment_id]
        
        if len(new_experiments) < len(experiments):
            data["paste_experiments"] = new_experiments
            return self.save_data(data)
        return False

    def update_paste_experiment(self, experiment_id, updated_fields):
        """更新净浆实验"""
        data = self.load_data()
        experiments = data.get("paste_experiments", [])
        updated = False
        for i, exp in enumerate(experiments):
            if exp.get("id") == experiment_id:
                experiments[i].update(updated_fields)
                experiments[i]["last_modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                updated = True
                break
        if updated:
            data["paste_experiments"] = experiments
            return self.save_data(data)
        return False
    
    # 砂浆实验
    def get_all_mortar_experiments(self):
        """获取所有砂浆实验"""
        data = self.load_data()
        return data.get("mortar_experiments", [])
    
    def add_mortar_experiment(self, experiment_data):
        """添加新砂浆实验"""
        data = self.load_data()
        experiments = data.get("mortar_experiments", [])
        
        # 生成新ID
        new_id = max([e.get("id", 0) for e in experiments], default=0) + 1
        experiment_data["id"] = new_id
        experiment_data["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        experiments.append(experiment_data)
        data["mortar_experiments"] = experiments
        return self.save_data(data)
    
    def delete_mortar_experiment(self, experiment_id):
        """删除砂浆实验"""
        data = self.load_data()
        experiments = data.get("mortar_experiments", [])
        
        new_experiments = [e for e in experiments if e.get("id") != experiment_id]
        
        if len(new_experiments) < len(experiments):
            data["mortar_experiments"] = new_experiments
            return self.save_data(data)
        return False

    def update_mortar_experiment(self, experiment_id, updated_fields):
        """更新砂浆实验"""
        data = self.load_data()
        experiments = data.get("mortar_experiments", [])
        updated = False
        for i, exp in enumerate(experiments):
            if exp.get("id") == experiment_id:
                experiments[i].update(updated_fields)
                experiments[i]["last_modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                updated = True
                break
        if updated:
            data["mortar_experiments"] = experiments
            return self.save_data(data)
        return False

    # -----------------------------------------------------------
    # 产品库存管理 (Product Inventory)
    # -----------------------------------------------------------
    
    def get_product_inventory(self):
        """获取所有产品库存"""
        data = self.load_data()
        return data.get("product_inventory", [])
        
    def add_product_inventory_record(self, record_data):
        """
        添加产品库存记录 (入库/出库)
        record_data: {
            "product_name": str,
            "product_type": str, (母液/速凝剂/防冻剂/减水剂/...)
            "quantity": float, (吨)
            "type": "in" | "out",
            "reason": str,
            "operator": str,
            "date": str
        }
        """
        data = self.load_data()
        inventory = data.get("product_inventory", [])
        records = data.get("product_inventory_records", [])
        
        # 1. 更新库存快照
        product_name = record_data.get("product_name")
        product_type = record_data.get("product_type", "其他")
        qty = float(record_data.get("quantity", 0.0))
        op_type = record_data.get("type")
        
        target_item = next((p for p in inventory if p["name"] == product_name and p.get("type") == product_type), None)
        
        if not target_item:
            # 新增产品
            if op_type == "out":
                return False, "库存不足 (产品不存在)"
            
            target_item = {
                "id": max([p.get("id", 0) for p in inventory], default=0) + 1,
                "name": product_name,
                "type": product_type,
                "stock_quantity": qty,
                "unit": "吨",
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            inventory.append(target_item)
        else:
            # 更新现有产品
            current_stock = float(target_item.get("stock_quantity", 0.0))
            if op_type == "in":
                target_item["stock_quantity"] = current_stock + qty
            else:
                if current_stock < qty:
                    # 允许负库存? 暂时允许警告但继续，或者禁止
                    pass 
                target_item["stock_quantity"] = current_stock - qty
            
            target_item["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
        # 2. 添加流水记录
        new_rec_id = max([r.get("id", 0) for r in records], default=0) + 1
        record_data["id"] = new_rec_id
        record_data["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        record_data["snapshot_stock"] = target_item["stock_quantity"]
        records.append(record_data)
        
        data["product_inventory"] = inventory
        data["product_inventory_records"] = records
        
        if self.save_data(data):
            return True, "库存更新成功"
        return False, "保存失败"

    def get_product_inventory_records(self):
        """获取产品库存流水"""
        data = self.load_data()
        return data.get("product_inventory_records", [])
    
    # 混凝土实验
    def get_all_concrete_experiments(self):
        """获取所有混凝土实验"""
        data = self.load_data()
        return data.get("concrete_experiments", [])
    
    def add_concrete_experiment(self, experiment_data):
        """添加新混凝土实验"""
        data = self.load_data()
        experiments = data.get("concrete_experiments", [])
        
        # 生成新ID
        new_id = max([e.get("id", 0) for e in experiments], default=0) + 1
        experiment_data["id"] = new_id
        experiment_data["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        experiments.append(experiment_data)
        data["concrete_experiments"] = experiments
        return self.save_data(data)
    
    def delete_concrete_experiment(self, experiment_id):
        """删除混凝土实验"""
        data = self.load_data()
        experiments = data.get("concrete_experiments", [])
        
        new_experiments = [e for e in experiments if e.get("id") != experiment_id]
        
        if len(new_experiments) < len(experiments):
            data["concrete_experiments"] = new_experiments
            return self.save_data(data)
        return False

    def update_concrete_experiment(self, experiment_id, updated_fields):
        """更新混凝土实验"""
        data = self.load_data()
        experiments = data.get("concrete_experiments", [])
        updated = False
        for i, exp in enumerate(experiments):
            if exp.get("id") == experiment_id:
                experiments[i].update(updated_fields)
                experiments[i]["last_modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                updated = True
                break
        if updated:
            data["concrete_experiments"] = experiments
            return self.save_data(data)
        return False
    
    # -------------------- 数据导出/导入功能 --------------------
    def export_to_excel(self):
        """将所有数据导出到Excel文件"""
        try:
            # 创建内存中的Excel文件
            output = BytesIO()
            
            # 使用pandas的ExcelWriter
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # 获取所有数据
                data = self.load_data()
                
                # 导出各个数据表
                # 1. 项目数据
                if data.get("projects"):
                    projects_df = pd.DataFrame(data["projects"])
                    projects_df.to_excel(writer, sheet_name='项目', index=False)
                
                # 2. 实验数据
                if data.get("experiments"):
                    experiments_df = pd.DataFrame(data["experiments"])
                    experiments_df.to_excel(writer, sheet_name='实验', index=False)
                
                # 3. 原材料数据
                if data.get("raw_materials"):
                    raw_materials_df = pd.DataFrame(data["raw_materials"])
                    raw_materials_df.to_excel(writer, sheet_name='原材料', index=False)
                
                # 4. 合成实验记录
                if data.get("synthesis_records"):
                    synthesis_df = pd.DataFrame(data["synthesis_records"])
                    synthesis_df.to_excel(writer, sheet_name='合成实验', index=False)
                
                # 5. 成品减水剂
                if data.get("products"):
                    products_df = pd.DataFrame(data["products"])
                    products_df.to_excel(writer, sheet_name='成品减水剂', index=False)
                
                # 6. 净浆实验
                if data.get("paste_experiments"):
                    paste_df = pd.DataFrame(data["paste_experiments"])
                    paste_df.to_excel(writer, sheet_name='净浆实验', index=False)
                
                # 7. 砂浆实验
                if data.get("mortar_experiments"):
                    mortar_df = pd.DataFrame(data["mortar_experiments"])
                    mortar_df.to_excel(writer, sheet_name='砂浆实验', index=False)
                
                # 8. 混凝土实验
                if data.get("concrete_experiments"):
                    concrete_df = pd.DataFrame(data["concrete_experiments"])
                    concrete_df.to_excel(writer, sheet_name='混凝土实验', index=False)
                
                # 9. 性能数据
                if data.get("performance_data"):
                    perf_data = data["performance_data"]
                    if perf_data.get("synthesis"):
                        perf_synth_df = pd.DataFrame(perf_data["synthesis"])
                        perf_synth_df.to_excel(writer, sheet_name='合成性能数据', index=False)
                
                # 10. 数据字典（说明）
                metadata = {
                    'Sheet名称': ['项目', '实验', '原材料', '合成实验', '成品减水剂', '净浆实验', '砂浆实验', '混凝土实验', '合成性能数据'],
                    '描述': [
                        '项目基本信息和管理信息',
                        '实验计划和执行信息',
                        '原材料库管理信息',
                        '合成实验详细记录',
                        '成品减水剂信息',
                        '净浆实验测试数据',
                        '砂浆实验测试数据',
                        '混凝土实验测试数据',
                        '合成性能测试数据'
                    ]
                }
                metadata_df = pd.DataFrame(metadata)
                metadata_df.to_excel(writer, sheet_name='数据字典', index=False)
            
            # 获取二进制数据
            excel_data = output.getvalue()
            
            # 创建下载链接
            b64 = base64.b64encode(excel_data).decode()
            href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="聚羧酸减水剂研发数据_{datetime.now().strftime("%Y%m%d")}.xlsx">点击下载 Excel 文件</a>'
            
            return href
        
        except Exception as e:
            st.error(f"导出数据失败: {e}")
            return None

    def import_from_excel(self, uploaded_file):
        """从Excel文件导入数据"""
        try:
            # 读取Excel文件
            excel_file = pd.ExcelFile(uploaded_file)
            
            # 获取现有数据
            data = self.load_data()
            
            # 导入各个工作表
            import_summary = []
            
            # 1. 导入项目数据
            if '项目' in excel_file.sheet_names:
                projects_df = pd.read_excel(excel_file, sheet_name='项目')
                if not projects_df.empty:
                    # 转换为字典列表
                    projects_list = projects_df.to_dict('records')
                    # 确保ID字段存在
                    for i, project in enumerate(projects_list, 1):
                        if 'id' not in project or pd.isna(project['id']):
                            project['id'] = i
                    data['projects'] = projects_list
                    import_summary.append(f"项目: {len(projects_list)} 条")
            
            # 2. 导入实验数据
            if '实验' in excel_file.sheet_names:
                experiments_df = pd.read_excel(excel_file, sheet_name='实验')
                if not experiments_df.empty:
                    experiments_list = experiments_df.to_dict('records')
                    for i, exp in enumerate(experiments_list, 1):
                        if 'id' not in exp or pd.isna(exp['id']):
                            exp['id'] = i
                    data['experiments'] = experiments_list
                    import_summary.append(f"实验: {len(experiments_list)} 条")
            
            # 3. 导入原材料数据
            if '原材料' in excel_file.sheet_names:
                materials_df = pd.read_excel(excel_file, sheet_name='原材料')
                if not materials_df.empty:
                    materials_list = materials_df.to_dict('records')
                    for i, mat in enumerate(materials_list, 1):
                        if 'id' not in mat or pd.isna(mat['id']):
                            mat['id'] = i
                    data['raw_materials'] = materials_list
                    import_summary.append(f"原材料: {len(materials_list)} 条")
            
            # 4. 导入合成实验数据
            if '合成实验' in excel_file.sheet_names:
                synthesis_df = pd.read_excel(excel_file, sheet_name='合成实验')
                if not synthesis_df.empty:
                    synthesis_list = synthesis_df.to_dict('records')
                    for i, record in enumerate(synthesis_list, 1):
                        if 'id' not in record or pd.isna(record['id']):
                            record['id'] = i
                    data['synthesis_records'] = synthesis_list
                    import_summary.append(f"合成实验: {len(synthesis_list)} 条")
            
            # 5. 导入成品减水剂数据
            if '成品减水剂' in excel_file.sheet_names:
                products_df = pd.read_excel(excel_file, sheet_name='成品减水剂')
                if not products_df.empty:
                    products_list = products_df.to_dict('records')
                    for i, product in enumerate(products_list, 1):
                        if 'id' not in product or pd.isna(product['id']):
                            product['id'] = i
                    data['products'] = products_list
                    import_summary.append(f"成品减水剂: {len(products_list)} 条")
            
            # 6. 导入净浆实验数据
            if '净浆实验' in excel_file.sheet_names:
                paste_df = pd.read_excel(excel_file, sheet_name='净浆实验')
                if not paste_df.empty:
                    paste_list = paste_df.to_dict('records')
                    for i, exp in enumerate(paste_list, 1):
                        if 'id' not in exp or pd.isna(exp['id']):
                            exp['id'] = i
                    data['paste_experiments'] = paste_list
                    import_summary.append(f"净浆实验: {len(paste_list)} 条")
            
            # 7. 导入砂浆实验数据
            if '砂浆实验' in excel_file.sheet_names:
                mortar_df = pd.read_excel(excel_file, sheet_name='砂浆实验')
                if not mortar_df.empty:
                    mortar_list = mortar_df.to_dict('records')
                    for i, exp in enumerate(mortar_list, 1):
                        if 'id' not in exp or pd.isna(exp['id']):
                            exp['id'] = i
                    data['mortar_experiments'] = mortar_list
                    import_summary.append(f"砂浆实验: {len(mortar_list)} 条")
            
            # 8. 导入混凝土实验数据
            if '混凝土实验' in excel_file.sheet_names:
                concrete_df = pd.read_excel(excel_file, sheet_name='混凝土实验')
                if not concrete_df.empty:
                    concrete_list = concrete_df.to_dict('records')
                    for i, exp in enumerate(concrete_list, 1):
                        if 'id' not in exp or pd.isna(exp['id']):
                            exp['id'] = i
                    data['concrete_experiments'] = concrete_list
                    import_summary.append(f"混凝土实验: {len(concrete_list)} 条")
            
            # 9. 导入合成性能数据
            if '合成性能数据' in excel_file.sheet_names:
                perf_df = pd.read_excel(excel_file, sheet_name='合成性能数据')
                if not perf_df.empty:
                    perf_list = perf_df.to_dict('records')
                    if 'performance_data' not in data:
                        data['performance_data'] = {}
                    data['performance_data']['synthesis'] = perf_list
                    import_summary.append(f"合成性能数据: {len(perf_list)} 条")
            
            # 保存导入的数据
            if self.save_data(data):
                return True, "，".join(import_summary)
            else:
                return False, "保存导入数据失败"
                
        except Exception as e:
            return False, f"导入数据失败: {str(e)}"

    def get_json_content(self):
        """获取当前数据的JSON字符串"""
        if self.data_file.exists():
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return f.read()
        return "{}"

    def import_from_json(self, json_content):
        """从JSON字符串导入数据（完全覆盖）"""
        try:
            data = json.loads(json_content)
            # 验证结构
            if not isinstance(data, dict):
                return False, "数据格式错误：根节点必须是对象"
            
            # 确保必要字段存在
            self._ensure_data_structure(data)
            
            # 保存
            if self.save_data(data):
                return True, "数据恢复成功"
            else:
                return False, "保存数据失败"
        except json.JSONDecodeError:
            return False, "JSON格式解析失败"
        except Exception as e:
            return False, f"导入失败: {str(e)}"

