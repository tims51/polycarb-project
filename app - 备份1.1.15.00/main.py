"""
聚羧酸减水剂研发管理系统 - 主程序 (修复删除功能版)
基于数据管理器架构，支持完整的增删查改功能
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from pathlib import Path
import json
import time

# -------------------- 自定义数据管理模块 --------------------
# ==================== 时间线管理器类 ====================
class TimelineManager:
    """专门处理项目时间线计算和管理的类"""
    
    @staticmethod
    def calculate_timeline(project_data):
        """
        计算项目时间线信息
        返回：时间线信息字典，包含状态、进度、时间等信息
        """
        # ... 原有代码保持不变 ...

    @staticmethod
    def _create_invalid_timeline(reason=""):
        """创建无效时间线信息"""
        # ... 原有代码保持不变 ...

    @staticmethod
    def get_timeline_summary(timeline_info):
        """获取时间线摘要文本"""
        # ... 原有代码保持不变 ...

    @staticmethod
    def is_project_active(timeline_info):
        """检查项目是否处于活跃状态（进行中或即将开始）"""
        # ... 原有代码保持不变 ...

# ==================== 数据管理器类 ====================
class DataManager:
    """统一数据管理器 - 处理所有数据的增删查改"""
    
    def __init__(self):
        self.data_file = Path(__file__).parent.parent / "data.json"
        self.backup_dir = Path(__file__).parent.parent / "backups"
        self._ensure_valid_data_file()
        self._ensure_backup_dir()
    
    def _ensure_backup_dir(self):
        """确保备份目录存在"""
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
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
                return True
        except (json.JSONDecodeError, ValueError, FileNotFoundError):
            # 如果文件无效或不存在，创建初始数据
            print("数据文件无效或不存在，正在创建初始数据...")
            initial_data = self.get_initial_data()
            return self.save_data(initial_data)
        return False
    
    def backup_data(self, backup_name=None):
        """备份数据到备份目录"""
        try:
            if backup_name is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"data_backup_{timestamp}.json"
            
            backup_file = self.backup_dir / backup_name
            
            # 复制当前数据文件
            import shutil
            if self.data_file.exists():
                shutil.copy2(self.data_file, backup_file)
                return True, backup_file
            else:
                return False, "数据文件不存在"
        except Exception as e:
            return False, str(e)
    
    def restore_from_backup(self, backup_file):
        """从备份文件恢复数据"""
        try:
            import shutil
            shutil.copy2(backup_file, self.data_file)
            return True, "数据恢复成功"
        except Exception as e:
            return False, str(e)
    
    def export_data(self, export_format='json'):
        """导出数据"""
        data = self.load_data()
        if export_format == 'json':
            return json.dumps(data, ensure_ascii=False, indent=4)
        elif export_format == 'csv':
            # 这里可以根据需要实现CSV导出
            pass
        return None
    
    def import_data(self, json_data, overwrite=False):
        """导入数据"""
        try:
            data = json.loads(json_data)
            if not isinstance(data, dict):
                return False, "数据格式不正确"
            
            if overwrite:
                self.save_data(data)
                return True, "数据已覆盖导入"
            else:
                # 合并数据
                current_data = self.load_data()
                for key in data:
                    if key not in current_data:
                        current_data[key] = data[key]
                    else:
                        # 合并列表数据
                        if isinstance(current_data[key], list) and isinstance(data[key], list):
                            current_data[key].extend(data[key])
                self.save_data(current_data)
                return True, "数据已合并导入"
        except Exception as e:
            return False, f"导入失败: {str(e)}"
    
    def load_data(self):
        """从JSON文件加载所有数据"""
        try:
            if self.data_file.exists():
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return self.get_initial_data()
        except Exception as e:
            st.error(f"读取数据失败: {e}")
            # 返回空数据结构
            return self.get_initial_data()
    
    def save_data(self, data):
        """保存数据到JSON文件"""
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
            return True
        except Exception as e:
            st.error(f"保存数据失败: {e}")
            return False
    
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
                },
                {
                    "id": 3,
                    "name": "PC-003配方筛选",
                    "leader": "王五",
                    "start_date": "2024-01-15",
                    "end_date": "2024-04-01",
                    "status": "进行中",
                    "progress": 30,
                    "description": "筛选最优单体配比"
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
            "performance_data": [
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
            "synthesis_records": [],
            "products": [],
            "raw_materials": []
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
    
    def delete_experiment(self, experiment_id):
        """根据ID删除实验"""
        data = self.load_data()
        experiments = data.get("experiments", [])
        
        new_experiments = [e for e in experiments if e.get("id") != experiment_id]
        
        if len(new_experiments) < len(experiments):
            data["experiments"] = new_experiments
            return self.save_data(data)
        return False
    
    # ==================== 原料管理方法 ====================
    def get_all_raw_materials(self):
        """获取所有原料信息"""
        data = self.load_data()
        return data.get("raw_materials", [])
    
    def get_raw_material(self, material_id):
        """根据ID获取原料信息"""
        materials = self.get_all_raw_materials()
        for material in materials:
            if material.get("id") == material_id:
                return material
        return None
    
    def add_raw_material(self, material_data):
        """添加新原料"""
        data = self.load_data()
        materials = data.get("raw_materials", [])
        
        # 生成新ID
        new_id = max([m.get("id", 0) for m in materials], default=0) + 1
        material_data["id"] = new_id
        
        # 计算总值
        if "current_quantity" in material_data and "unit_price" in material_data:
            material_data["total_value"] = material_data["current_quantity"] * material_data["unit_price"]
        
        materials.append(material_data)
        data["raw_materials"] = materials
        return self.save_data(data)
    
    def update_raw_material(self, material_id, updated_fields):
        """更新原料信息"""
        data = self.load_data()
        materials = data.get("raw_materials", [])
        
        for i, material in enumerate(materials):
            if material.get("id") == material_id:
                # 更新字段
                materials[i].update(updated_fields)
                
                # 重新计算总值
                if "current_quantity" in updated_fields or "unit_price" in updated_fields:
                    current_qty = materials[i].get("current_quantity", 0)
                    unit_price = materials[i].get("unit_price", 0)
                    materials[i]["total_value"] = current_qty * unit_price
                
                data["raw_materials"] = materials
                return self.save_data(data)
        return False
    
    def delete_raw_material(self, material_id):
        """删除原料"""
        data = self.load_data()
        materials = data.get("raw_materials", [])
        
        new_materials = [m for m in materials if m.get("id") != material_id]
        
        if len(new_materials) < len(materials):
            data["raw_materials"] = new_materials
            return self.save_data(data)
        return False
    
    # ==================== 合成记录管理方法 ====================
    def get_all_synthesis_records(self):
        """获取所有合成记录"""
        data = self.load_data()
        return data.get("synthesis_records", [])
    
    def get_synthesis_record(self, record_id):
        """根据ID获取合成记录"""
        records = self.get_all_synthesis_records()
        for record in records:
            if record.get("id") == record_id:
                return record
        return None
    
    def add_synthesis_record(self, record_data):
        """添加合成记录"""
        data = self.load_data()
        records = data.get("synthesis_records", [])
        
        # 生成新ID
        new_id = max([r.get("id", 0) for r in records], default=0) + 1
        record_data["id"] = new_id
        
        # 确保日期格式正确
        for date_field in ["synthesis_date", "qc_date"]:
            if date_field in record_data and record_data[date_field]:
                if hasattr(record_data[date_field], 'strftime'):
                    record_data[date_field] = record_data[date_field].strftime("%Y-%m-%d")
        
        # 生成批次号（如果未提供）
        if "batch_no" not in record_data or not record_data["batch_no"]:
            formula_id = record_data.get("formula_id", "PC")
            date_str = record_data.get("synthesis_date", datetime.now().strftime("%Y%m%d"))
            record_count = len([r for r in records if r.get("formula_id") == formula_id]) + 1
            record_data["batch_no"] = f"{formula_id}-{date_str}-{record_count:03d}"
        
        records.append(record_data)
        data["synthesis_records"] = records
        return self.save_data(data)
    
    def get_synthesis_by_experiment(self, experiment_id):
        """根据实验ID获取合成记录"""
        records = self.get_all_synthesis_records()
        return [r for r in records if r.get("experiment_id") == experiment_id]
    
    # ==================== 成品减水剂管理方法 ====================
    def get_all_products(self):
        """获取所有成品减水剂"""
        data = self.load_data()
        return data.get("products", [])
    
    def get_product(self, product_id):
        """根据ID获取成品减水剂"""
        products = self.get_all_products()
        for product in products:
            if product.get("id") == product_id:
                return product
        return None
    
    def get_product_by_batch(self, batch_no):
        """根据批次号获取成品减水剂"""
        products = self.get_all_products()
        for product in products:
            if product.get("batch_no") == batch_no:
                return product
        return None
    
    def add_product(self, product_data):
        """添加成品减水剂"""
        data = self.load_data()
        products = data.get("products", [])
        
        # 生成新ID
        new_id = max([p.get("id", 0) for p in products], default=0) + 1
        product_data["id"] = new_id
        
        # 生成批次号（如果未提供）
        if "batch_no" not in product_data or not product_data["batch_no"]:
            base_code = product_data.get("product_code", "PC")
            date_str = datetime.now().strftime("%Y%m%d")
            product_count = len([p for p in products if p.get("product_code") == base_code]) + 1
            product_data["batch_no"] = f"{base_code}-{date_str}-{product_count:03d}"
        
        # 确保日期格式正确
        if "production_date" in product_data and product_data["production_date"]:
            if hasattr(product_data["production_date"], 'strftime'):
                product_data["production_date"] = product_data["production_date"].strftime("%Y-%m-%d")
        
        products.append(product_data)
        data["products"] = products
        return self.save_data(data)
    
    def get_synthesis_batch_list(self):
        """获取所有合成实验批次号列表"""
        synthesis_records = self.get_all_synthesis_records()
        batch_list = []
        for record in synthesis_records:
            batch_no = record.get("batch_no")
            if batch_no:
                batch_list.append({
                    "batch_no": batch_no,
                    "synthesis_date": record.get("synthesis_date"),
                    "formula_id": record.get("formula_id"),
                    "id": record.get("id")
                })
        return batch_list
    
    def get_product_batch_list(self):
        """获取所有成品减水剂批次号列表"""
        products = self.get_all_products()
        batch_list = []
        for product in products:
            batch_no = product.get("batch_no")
            if batch_no:
                batch_list.append({
                    "batch_no": batch_no,
                    "product_name": product.get("product_name"),
                    "production_date": product.get("production_date"),
                    "id": product.get("id")
                })
        return batch_list
    
    def get_all_batch_options(self):
        """获取所有批次选项（合成母液 + 成品减水剂）"""
        options = []
        
        # 合成母液
        synthesis_batches = self.get_synthesis_batch_list()
        for batch in synthesis_batches:
            options.append({
                "type": "母液",
                "batch_no": batch["batch_no"],
                "name": f"母液: {batch['batch_no']}",
                "date": batch.get("synthesis_date", ""),
                "source": "synthesis",
                "source_id": batch["id"]
            })
        
        # 成品减水剂
        product_batches = self.get_product_batch_list()
        for batch in product_batches:
            options.append({
                "type": "成品",
                "batch_no": batch["batch_no"],
                "name": f"成品: {batch['batch_no']} - {batch.get('product_name', '')}",
                "date": batch.get("production_date", ""),
                "source": "product",
                "source_id": batch["id"]
            })
        
        return options
    
    # ==================== 性能记录管理方法 ====================
    def get_all_performance_records(self):
        """获取所有性能测试记录"""
        data = self.load_data()
        return data.get("performance_records", [])
    
    def add_performance_record(self, record_data):
        """添加性能测试记录"""
        data = self.load_data()
        records = data.get("performance_records", [])
        
        # 生成新ID
        new_id = max([r.get("id", 0) for r in records], default=0) + 1
        record_data["id"] = new_id
        
        # 确保日期格式正确
        if "test_date" in record_data and record_data["test_date"]:
            if hasattr(record_data["test_date"], 'strftime'):
                record_data["test_date"] = record_data["test_date"].strftime("%Y-%m-%d")
        
        records.append(record_data)
        data["performance_records"] = records
        return self.save_data(data)
    
    def get_performance_by_synthesis(self, synthesis_id):
        """根据合成记录ID获取性能测试记录"""
        records = self.get_all_performance_records()
        return [r for r in records if r.get("synthesis_record_id") == synthesis_id]
    
    # ==================== 性能数据管理方法 ====================
    def get_performance_data(self, data_type=None):
        """获取性能数据"""
        data = self.load_data()
        
        # 确保performance_data存在且为字典
        if "performance_data" not in data:
            data["performance_data"] = {
                "synthesis": [],
                "paste": [],
                "mortar": [],
                "concrete": []
            }
        
        # 如果是列表格式的旧数据，转换为新格式
        if isinstance(data["performance_data"], list):
            old_data = data["performance_data"]
            data["performance_data"] = {
                "synthesis": old_data,  # 假设旧数据都是合成实验
                "paste": [],
                "mortar": [],
                "concrete": []
            }
            # 保存转换后的数据
            self.save_data(data)
        
        performance_data = data["performance_data"]
        
        if data_type:
            return performance_data.get(data_type, [])
        else:
            return performance_data
    
    def add_performance_record_to_dict(self, data_type, record_data):
        """添加性能记录到字典格式"""
        data = self.load_data()
        
        # 确保performance_data存在且为字典
        if "performance_data" not in data:
            data["performance_data"] = {
                "synthesis": [],
                "paste": [],
                "mortar": [],
                "concrete": []
            }
        
        # 确保数据类型存在
        if data_type not in data["performance_data"]:
            data["performance_data"][data_type] = []
        
        # 添加记录
        data["performance_data"][data_type].append(record_data)
        
        # 保存数据
        return self.save_data(data)
    
    def get_experiment_performance(self, experiment_id, data_type=None):
        """获取特定实验的性能数据"""
        performance_data = self.get_performance_data()
        results = []
        
        if data_type:
            # 获取特定类型的数据
            data_list = performance_data.get(data_type, [])
            for record in data_list:
                if record.get("experiment_id") == experiment_id:
                    results.append(record)
        else:
            # 获取所有类型的数据
            for data_type in ["synthesis", "paste", "mortar", "concrete"]:
                data_list = performance_data.get(data_type, [])
                for record in data_list:
                    if record.get("experiment_id") == experiment_id:
                        record["data_type"] = data_type
                        results.append(record)
        
        return results
    
    def delete_performance_record(self, record_id, data_type=None):
        """删除性能记录"""
        data = self.load_data()
        
        if "performance_data" not in data:
            return False
        
        performance_data = data["performance_data"]
        deleted = False
        
        if data_type:
            # 删除特定类型的记录
            if data_type in performance_data:
                original_len = len(performance_data[data_type])
                performance_data[data_type] = [
                    record for record in performance_data[data_type] 
                    if record.get("id") != record_id
                ]
                if len(performance_data[data_type]) < original_len:
                    deleted = True
        else:
            # 删除所有类型中的记录
            for dtype in ["synthesis", "paste", "mortar", "concrete"]:
                if dtype in performance_data:
                    original_len = len(performance_data[dtype])
                    performance_data[dtype] = [
                        record for record in performance_data[dtype] 
                        if record.get("id") != record_id
                    ]
                    if len(performance_data[dtype]) < original_len:
                        deleted = True
        
        if deleted:
            data["performance_data"] = performance_data
            return self.save_data(data)
        
        return False
    
    def update_performance_record(self, record_id, data_type, updated_fields):
        """更新性能记录"""
        data = self.load_data()
        
        if "performance_data" not in data or data_type not in data["performance_data"]:
            return False
        
        records = data["performance_data"][data_type]
        
        for i, record in enumerate(records):
            if record.get("id") == record_id:
                # 更新字段
                records[i].update(updated_fields)
                # 更新时间戳
                records[i]["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                data["performance_data"][data_type] = records
                return self.save_data(data)
        
        return False
    
    def get_performance_statistics(self, data_type=None):
        """获取性能数据统计信息"""
        performance_data = self.get_performance_data()
        
        stats = {
            "total_records": 0,
            "by_type": {}
        }
        
        if data_type:
            # 获取特定类型的统计
            if data_type in performance_data:
                records = performance_data[data_type]
                stats["total_records"] = len(records)
                
                if records:
                    # 计算数值型字段的平均值
                    numeric_fields = ["water_reduction", "solid_content", "initial_diameter", "mortar_flow", "slump", "strength_28d"]
                    for field in numeric_fields:
                        if field in records[0]:
                            values = [r[field] for r in records if field in r and r[field] is not None]
                            if values:
                                stats[field] = {
                                    "min": min(values),
                                    "max": max(values),
                                    "avg": sum(values) / len(values)
                                }
        else:
            # 获取所有类型的统计
            for dtype in ["synthesis", "paste", "mortar", "concrete"]:
                if dtype in performance_data:
                    records = performance_data[dtype]
                    stats["by_type"][dtype] = len(records)
                    stats["total_records"] += len(records)
        
        return stats
    
    def get_performance_by_date_range(self, start_date, end_date, data_type=None):
        """根据日期范围获取性能数据"""
        performance_data = self.get_performance_data()
        results = []
        
        if data_type:
            # 获取特定类型的数据
            if data_type in performance_data:
                for record in performance_data[data_type]:
                    record_date = datetime.strptime(record.get("record_date", "1900-01-01"), "%Y-%m-%d").date()
                    if start_date <= record_date <= end_date:
                        results.append(record)
        else:
            # 获取所有类型的数据
            for dtype in ["synthesis", "paste", "mortar", "concrete"]:
                if dtype in performance_data:
                    for record in performance_data[dtype]:
                        record_date = datetime.strptime(record.get("record_date", "1900-01-01"), "%Y-%m-%d").date()
                        if start_date <= record_date <= end_date:
                            record["data_type"] = dtype
                            results.append(record)
        
        return results
    
    def get_latest_performance_records(self, limit=10, data_type=None):
        """获取最新的性能记录"""
        performance_data = self.get_performance_data()
        all_records = []
        
        if data_type:
            # 获取特定类型的数据
            if data_type in performance_data:
                for record in performance_data[data_type]:
                    record["data_type"] = data_type
                    all_records.append(record)
        else:
            # 获取所有类型的数据
            for dtype in ["synthesis", "paste", "mortar", "concrete"]:
                if dtype in performance_data:
                    for record in performance_data[dtype]:
                        record["data_type"] = dtype
                        all_records.append(record)
        
        # 按创建时间排序
        all_records.sort(key=lambda x: x.get("created_at", "1900-01-01"), reverse=True)
        
        return all_records[:limit]
    
    # ==================== 成品减水剂管理方法 ====================
    def get_all_products(self):
        """获取所有成品减水剂"""
        data = self.load_data()
        return data.get("products", [])
    
    def get_product(self, product_id):
        """根据ID获取成品减水剂"""
        products = self.get_all_products()
        for product in products:
            if product.get("id") == product_id:
                return product
        return None
    
    def get_product_by_batch(self, batch_no):
        """根据批次号获取成品减水剂"""
        products = self.get_all_products()
        for product in products:
            if product.get("batch_no") == batch_no:
                return product
        return None
    
    def add_product(self, product_data):
        """添加成品减水剂"""
        data = self.load_data()
        products = data.get("products", [])
        
        # 生成新ID
        new_id = max([p.get("id", 0) for p in products], default=0) + 1
        product_data["id"] = new_id
        
        # 生成批次号（如果未提供）
        if "batch_no" not in product_data or not product_data["batch_no"]:
            base_code = product_data.get("product_code", "PC")
            date_str = datetime.now().strftime("%Y%m%d")
            product_count = len([p for p in products if p.get("product_code") == base_code]) + 1
            product_data["batch_no"] = f"{base_code}-{date_str}-{product_count:03d}"
        
        # 确保日期格式正确
        if "production_date" in product_data and product_data["production_date"]:
            if hasattr(product_data["production_date"], 'strftime'):
                product_data["production_date"] = product_data["production_date"].strftime("%Y-%m-%d")
        
        products.append(product_data)
        data["products"] = products
        return self.save_data(data)
    
    def get_synthesis_batch_list(self):
        """获取所有合成实验批次号列表"""
        synthesis_records = self.get_all_synthesis_records()
        batch_list = []
        for record in synthesis_records:
            batch_no = record.get("batch_no")
            if batch_no:
                batch_list.append({
                    "batch_no": batch_no,
                    "synthesis_date": record.get("synthesis_date"),
                    "formula_id": record.get("formula_id"),
                    "id": record.get("id")
                })
        return batch_list
    
    def get_product_batch_list(self):
        """获取所有成品减水剂批次号列表"""
        products = self.get_all_products()
        batch_list = []
        for product in products:
            batch_no = product.get("batch_no")
            if batch_no:
                batch_list.append({
                    "batch_no": batch_no,
                    "product_name": product.get("product_name"),
                    "production_date": product.get("production_date"),
                    "id": product.get("id")
                })
        return batch_list
    
    def get_all_batch_options(self):
        """获取所有批次选项（合成母液 + 成品减水剂）"""
        options = []
        
        # 合成母液
        synthesis_batches = self.get_synthesis_batch_list()
        for batch in synthesis_batches:
            options.append({
                "type": "母液",
                "batch_no": batch["batch_no"],
                "name": f"母液: {batch['batch_no']}",
                "date": batch.get("synthesis_date", ""),
                "source": "synthesis",
                "source_id": batch["id"]
            })
        
        # 成品减水剂
        product_batches = self.get_product_batch_list()
        for batch in product_batches:
            options.append({
                "type": "成品",
                "batch_no": batch["batch_no"],
                "name": f"成品: {batch['batch_no']} - {batch.get('product_name', '')}",
                "date": batch.get("production_date", ""),
                "source": "product",
                "source_id": batch["id"]
            })
        
        return options
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
      # ==================== 项目时间线相关方法 ====================
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
        # 确保TimelineManager类已经定义且可访问
        try:
            return TimelineManager.calculate_timeline(project_data)
        except NameError:
            # 如果TimelineManager未定义，尝试备用方案
            print("警告: TimelineManager未找到，使用备用时间线计算")
            return self._calculate_timeline_fallback(project_data)
    
    def _calculate_timeline_fallback(self, project_data):
        """备用的时间线计算方法（当TimelineManager不可用时）"""
        try:
            start_date_str = project_data.get('start_date', '')
            end_date_str = project_data.get('end_date', '')
            
            if not start_date_str or not end_date_str:
                return None
            
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            today = datetime.now().date()
            
            return {
                'is_valid': True,
                'status': '计算中',
                'status_emoji': '📅',
                'percent': 50,
                'passed_days': 0,
                'total_days': (end_date - start_date).days,
                'start_date': start_date,
                'end_date': end_date,
                'today': today
            }
        except:
            return None
    
    # ==================== 项目时间线方法结束 ====================
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
    
    def delete_experiment(self, experiment_id):
        """根据ID删除实验"""
        data = self.load_data()
        experiments = data.get("experiments", [])
        
        new_experiments = [e for e in experiments if e.get("id") != experiment_id]
        
        if len(new_experiments) < len(experiments):
            data["experiments"] = new_experiments
            return self.save_data(data)
        return False
    
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
        """根据ID删除项目 - 修复版"""
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
        # ==================== 原料管理方法 ====================
    def get_all_raw_materials(self):
        """获取所有原料信息"""
        data = self.load_data()
        return data.get("raw_materials", [])
    
    def get_raw_material(self, material_id):
        """根据ID获取原料信息"""
        materials = self.get_all_raw_materials()
        for material in materials:
            if material.get("id") == material_id:
                return material
        return None
    
    def add_raw_material(self, material_data):
        """添加新原料"""
        data = self.load_data()
        materials = data.get("raw_materials", [])
        
        # 生成新ID
        new_id = max([m.get("id", 0) for m in materials], default=0) + 1
        material_data["id"] = new_id
        
        # 计算总值
        if "current_quantity" in material_data and "unit_price" in material_data:
            material_data["total_value"] = material_data["current_quantity"] * material_data["unit_price"]
        
        materials.append(material_data)
        data["raw_materials"] = materials
        return self.save_data(data)
    
    def update_raw_material(self, material_id, updated_fields):
        """更新原料信息"""
        data = self.load_data()
        materials = data.get("raw_materials", [])
        
        for i, material in enumerate(materials):
            if material.get("id") == material_id:
                # 更新字段
                materials[i].update(updated_fields)
                
                # 重新计算总值
                if "current_quantity" in updated_fields or "unit_price" in updated_fields:
                    current_qty = materials[i].get("current_quantity", 0)
                    unit_price = materials[i].get("unit_price", 0)
                    materials[i]["total_value"] = current_qty * unit_price
                
                data["raw_materials"] = materials
                return self.save_data(data)
        return False
    
    def delete_raw_material(self, material_id):
        """删除原料"""
        data = self.load_data()
        materials = data.get("raw_materials", [])
        
        new_materials = [m for m in materials if m.get("id") != material_id]
        
        if len(new_materials) < len(materials):
            data["raw_materials"] = new_materials
            return self.save_data(data)
        return False
    
    # ==================== 合成记录管理方法 ====================
    def get_all_synthesis_records(self):
        """获取所有合成记录"""
        data = self.load_data()
        return data.get("synthesis_records", [])
    
    def get_synthesis_record(self, record_id):
        """根据ID获取合成记录"""
        records = self.get_all_synthesis_records()
        for record in records:
            if record.get("id") == record_id:
                return record
        return None
    
    def add_synthesis_record(self, record_data):
        """添加合成记录"""
        data = self.load_data()
        records = data.get("synthesis_records", [])
        
        # 生成新ID
        new_id = max([r.get("id", 0) for r in records], default=0) + 1
        record_data["id"] = new_id
        
        # 确保日期格式正确
        for date_field in ["synthesis_date", "qc_date"]:
            if date_field in record_data and record_data[date_field]:
                if hasattr(record_data[date_field], 'strftime'):
                    record_data[date_field] = record_data[date_field].strftime("%Y-%m-%d")
        
        # 生成批次号（如果未提供）
        if "batch_no" not in record_data or not record_data["batch_no"]:
            formula_id = record_data.get("formula_id", "PC")
            date_str = record_data.get("synthesis_date", datetime.now().strftime("%Y%m%d"))
            record_count = len([r for r in records if r.get("formula_id") == formula_id]) + 1
            record_data["batch_no"] = f"{formula_id}-{date_str}-{record_count:03d}"
        
        records.append(record_data)
        data["synthesis_records"] = records
        return self.save_data(data)
    
    def get_synthesis_by_experiment(self, experiment_id):
        """根据实验ID获取合成记录"""
        records = self.get_all_synthesis_records()
        return [r for r in records if r.get("experiment_id") == experiment_id]
    
    # ==================== 性能记录管理方法 ====================
    def get_all_performance_records(self):
        """获取所有性能测试记录"""
        data = self.load_data()
        return data.get("performance_records", [])
    
    def add_performance_record(self, record_data):
        """添加性能测试记录"""
        data = self.load_data()
        records = data.get("performance_records", [])
        
        # 生成新ID
        new_id = max([r.get("id", 0) for r in records], default=0) + 1
        record_data["id"] = new_id
        
        # 确保日期格式正确
        if "test_date" in record_data and record_data["test_date"]:
            if hasattr(record_data["test_date"], 'strftime'):
                record_data["test_date"] = record_data["test_date"].strftime("%Y-%m-%d")
        
        records.append(record_data)
        data["performance_records"] = records
        return self.save_data(data)
    
    def get_performance_by_synthesis(self, synthesis_id):
        """根据合成记录ID获取性能测试记录"""
        records = self.get_all_performance_records()
        return [r for r in records if r.get("synthesis_record_id") == synthesis_id]
    
    # ==================== 辅助方法 ====================
    def get_material_usage_summary(self, material_id):
        """获取原料使用情况汇总"""
        synthesis_records = self.get_all_synthesis_records()
        
        total_usage = 0
        usage_records = []
        
        for record in synthesis_records:
            # 检查单体配比中的使用
            formula_params = record.get("formula_parameters", {})
            monomer_ratios = formula_params.get("monomer_ratios", [])
            
            for monomer in monomer_ratios:
                if monomer.get("material_id") == material_id:
                    usage = monomer.get("actual_usage", 0)
                    total_usage += usage
                    usage_records.append({
                        "batch_no": record.get("batch_no"),
                        "date": record.get("synthesis_date"),
                        "usage": usage,
                        "formula_id": record.get("formula_id")
                    })
            
            # 检查引发剂中的使用
            initiator = formula_params.get("initiator", {})
            if initiator.get("material_id") == material_id:
                usage = initiator.get("actual_usage", 0)
                total_usage += usage
                usage_records.append({
                    "batch_no": record.get("batch_no"),
                    "date": record.get("synthesis_date"),
                    "usage": usage,
                    "formula_id": record.get("formula_id")
                })
        
        return {
            "material_id": material_id,
            "total_usage": total_usage,
            "usage_records": usage_records
        }
    
# ==================== 性能数据管理方法 ====================
def get_performance_data(self, data_type=None):
    """获取性能数据"""
    data = self.load_data()
    
    # 确保performance_data存在且为字典
    if "performance_data" not in data:
        data["performance_data"] = {
            "synthesis": [],
            "paste": [],
            "mortar": [],
            "concrete": []
        }
    
    # 如果是列表格式的旧数据，转换为新格式
    if isinstance(data["performance_data"], list):
        old_data = data["performance_data"]
        data["performance_data"] = {
            "synthesis": old_data,  # 假设旧数据都是合成实验
            "paste": [],
            "mortar": [],
            "concrete": []
        }
        # 保存转换后的数据
        self.save_data(data)
    
    performance_data = data["performance_data"]
    
    if data_type:
        return performance_data.get(data_type, [])
    else:
        return performance_data

def add_performance_record(self, data_type, record_data):
    """添加性能记录"""
    data = self.load_data()
    
    # 确保performance_data存在且为字典
    if "performance_data" not in data:
        data["performance_data"] = {
            "synthesis": [],
            "paste": [],
            "mortar": [],
            "concrete": []
        }
    
    # 确保数据类型存在
    if data_type not in data["performance_data"]:
        data["performance_data"][data_type] = []
    
    # 添加记录
    data["performance_data"][data_type].append(record_data)
    
    # 保存数据
    return self.save_data(data)

def get_experiment_performance(self, experiment_id, data_type=None):
    """获取特定实验的性能数据"""
    performance_data = self.get_performance_data()
    results = []
    
    if data_type:
        # 获取特定类型的数据
        data_list = performance_data.get(data_type, [])
        for record in data_list:
            if record.get("experiment_id") == experiment_id:
                results.append(record)
    else:
        # 获取所有类型的数据
        for data_type in ["synthesis", "paste", "mortar", "concrete"]:
            data_list = performance_data.get(data_type, [])
            for record in data_list:
                if record.get("experiment_id") == experiment_id:
                    record["data_type"] = data_type
                    results.append(record)
    
    return results

def delete_performance_record(self, record_id, data_type=None):
    """删除性能记录"""
    data = self.load_data()
    
    if "performance_data" not in data:
        return False
    
    performance_data = data["performance_data"]
    deleted = False
    
    if data_type:
        # 删除特定类型的记录
        if data_type in performance_data:
            original_len = len(performance_data[data_type])
            performance_data[data_type] = [
                record for record in performance_data[data_type] 
                if record.get("id") != record_id
            ]
            if len(performance_data[data_type]) < original_len:
                deleted = True
    else:
        # 删除所有类型中的记录
        for dtype in ["synthesis", "paste", "mortar", "concrete"]:
            if dtype in performance_data:
                original_len = len(performance_data[dtype])
                performance_data[dtype] = [
                    record for record in performance_data[dtype] 
                    if record.get("id") != record_id
                ]
                if len(performance_data[dtype]) < original_len:
                    deleted = True
    
    if deleted:
        data["performance_data"] = performance_data
        return self.save_data(data)
    
    return False

def update_performance_record(self, record_id, data_type, updated_fields):
    """更新性能记录"""
    data = self.load_data()
    
    if "performance_data" not in data or data_type not in data["performance_data"]:
        return False
    
    records = data["performance_data"][data_type]
    
    for i, record in enumerate(records):
        if record.get("id") == record_id:
            # 更新字段
            records[i].update(updated_fields)
            # 更新时间戳
            records[i]["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            data["performance_data"][data_type] = records
            return self.save_data(data)
    
    return False

def get_performance_statistics(self, data_type=None):
    """获取性能数据统计信息"""
    performance_data = self.get_performance_data()
    
    stats = {
        "total_records": 0,
        "by_type": {}
    }
    
    if data_type:
        # 获取特定类型的统计
        if data_type in performance_data:
            records = performance_data[data_type]
            stats["total_records"] = len(records)
            
            if records:
                # 计算数值型字段的平均值
                numeric_fields = ["water_reduction", "solid_content", "initial_diameter", "mortar_flow", "slump", "strength_28d"]
                for field in numeric_fields:
                    if field in records[0]:
                        values = [r[field] for r in records if field in r and r[field] is not None]
                        if values:
                            stats[field] = {
                                "min": min(values),
                                "max": max(values),
                                "avg": sum(values) / len(values)
                            }
    else:
        # 获取所有类型的统计
        for dtype in ["synthesis", "paste", "mortar", "concrete"]:
            if dtype in performance_data:
                records = performance_data[dtype]
                stats["by_type"][dtype] = len(records)
                stats["total_records"] += len(records)
    
    return stats

def get_performance_by_date_range(self, start_date, end_date, data_type=None):
    """根据日期范围获取性能数据"""
    performance_data = self.get_performance_data()
    results = []
    
    if data_type:
        # 获取特定类型的数据
        if data_type in performance_data:
            for record in performance_data[data_type]:
                record_date = datetime.strptime(record.get("record_date", "1900-01-01"), "%Y-%m-%d").date()
                if start_date <= record_date <= end_date:
                    results.append(record)
    else:
        # 获取所有类型的数据
        for dtype in ["synthesis", "paste", "mortar", "concrete"]:
            if dtype in performance_data:
                for record in performance_data[dtype]:
                    record_date = datetime.strptime(record.get("record_date", "1900-01-01"), "%Y-%m-%d").date()
                    if start_date <= record_date <= end_date:
                        record["data_type"] = dtype
                        results.append(record)
    
    return results

def get_latest_performance_records(self, limit=10, data_type=None):
    """获取最新的性能记录"""
    performance_data = self.get_performance_data()
    all_records = []
    
    if data_type:
        # 获取特定类型的数据
        if data_type in performance_data:
            for record in performance_data[data_type]:
                record["data_type"] = data_type
                all_records.append(record)
    else:
        # 获取所有类型的数据
        for dtype in ["synthesis", "paste", "mortar", "concrete"]:
            if dtype in performance_data:
                for record in performance_data[dtype]:
                    record["data_type"] = dtype
                    all_records.append(record)
    
    # 按创建时间排序
    all_records.sort(key=lambda x: x.get("created_at", "1900-01-01"), reverse=True)
    
    return all_records[:limit]
# -------------------- 初始化数据管理器 --------------------
data_manager = DataManager()

# -------------------- 页面配置 --------------------
st.set_page_config(
    page_title="聚羧酸减水剂研发管理系统",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------- 页面渲染函数 --------------------
def render_project_timeline(project_data, timeline_info):
    """
    渲染项目时间线组件
    project_data: 项目数据字典
    timeline_info: 时间线信息字典（由TimelineManager计算）
    """
    if not timeline_info.get('is_valid'):
        st.warning("⚠️ 时间线信息不可用")
        return
    
    # 时间线头部：状态和标题
    status_emoji = timeline_info.get('status_emoji', '📅')
    status_text = timeline_info.get('status', '未知')
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"**{status_emoji} {status_text}**")
    with col2:
        percent = timeline_info.get('percent', 0)
        st.caption(f"{percent:.1f}%")
    
    # 时间线进度条
    st.progress(percent / 100)
    
    # 时间线详细信息
    with st.expander("📊 时间线详情", expanded=False):
        # 日期信息表格
        st.markdown("**日期信息**")
        
        date_info_cols = st.columns(3)
        with date_info_cols[0]:
            st.metric("开始日期", timeline_info.get('start_date').strftime('%Y-%m-%d'))
        with date_info_cols[1]:
            st.metric("结束日期", timeline_info.get('end_date').strftime('%Y-%m-%d'))
        with date_info_cols[2]:
            st.metric("今日日期", timeline_info.get('today').strftime('%Y-%m-%d'))
        
        # 时间进度信息
        st.markdown("**时间进度**")
        
        progress_info_cols = st.columns(3)
        with progress_info_cols[0]:
            passed_days = timeline_info.get('passed_days', 0)
            st.metric("已过天数", passed_days)
        with progress_info_cols[1]:
            total_days = timeline_info.get('total_days', 1)
            st.metric("总天数", total_days)
        with progress_info_cols[2]:
            remaining_days = timeline_info.get('remaining_days', 0)
            st.metric("剩余天数", remaining_days)
        
        # 额外信息
        st.markdown("**项目状态**")
        
        # 显示预计完成时间（如果进行中）
        estimated_completion = timeline_info.get('estimated_completion')
        if estimated_completion and timeline_info.get('status') == '进行中':
            st.info(f"📅 预计完成时间: {estimated_completion.strftime('%Y-%m-%d')}")
        
        # 显示延迟警告（如果已过期但未完成）
        if timeline_info.get('is_delayed'):
            st.error(f"⚠️ 项目已过期! 应于 {timeline_info.get('end_date').strftime('%Y-%m-%d')} 完成")
        
        # 显示时间线摘要
        summary = TimelineManager.get_timeline_summary(timeline_info)
        st.caption(f"📋 {summary}")
        
def render_dashboard():
    """渲染项目概览页面 - 紧凑布局版"""
    st.header("📊 项目概览")
    
    # 获取数据
    projects = data_manager.get_all_projects()
    experiments = data_manager.get_all_experiments()
    
    # 关键指标卡片（紧凑布局）
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        active_projects = sum(1 for p in projects if p.get("status") == "进行中")
        st.metric("进行中项目", active_projects)
    with col2:
        completed_projects = sum(1 for p in projects if p.get("status") == "已完成")
        st.metric("已完成项目", completed_projects)
    with col3:
        total_experiments = len(experiments)
        st.metric("总实验数", total_experiments)
    with col4:
        upcoming_exps = sum(1 for e in experiments if e.get("status") == "计划中")
        st.metric("待进行实验", upcoming_exps)
    
    st.divider()
    
    # --- 新增项目表单（紧凑设计）---
    with st.expander("➕ 新增项目", expanded=False):
        with st.form("add_project_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                new_name = st.text_input("项目名称*", key="new_project_name")
                new_leader = st.text_input("负责人*", key="new_project_leader")
                new_status = st.selectbox("状态*", ["计划中", "进行中", "已暂停", "已完成"], key="new_project_status")
            with col2:
                new_start = st.date_input("开始日期*", datetime.now(), key="new_project_start")
                new_end = st.date_input("结束日期", datetime.now() + timedelta(days=60), key="new_project_end")
                new_progress = st.slider("进度 (%)", 0, 100, 0, key="new_project_progress")
            
            new_desc = st.text_area("项目描述", key="new_project_desc", height=80)
            
            submitted = st.form_submit_button("添加项目", type="primary")
            if submitted:
                if new_name and new_leader:
                    new_project = {
                        "name": new_name,
                        "leader": new_leader,
                        "start_date": new_start,
                        "end_date": new_end,
                        "status": new_status,
                        "progress": new_progress,
                        "description": new_desc
                    }
                    if data_manager.add_project(new_project):
                        st.success(f"项目 '{new_name}' 添加成功！")
                        st.rerun()
                    else:
                        st.error("添加项目失败，请重试")
                else:
                    st.error("请填写带*的必填项")
    
    st.divider()
    
    # --- 编辑和删除项目（同一行，紧凑布局）---
    st.subheader("项目管理")
    
    # 使用两列布局，编辑和删除并排
    edit_col, delete_col = st.columns(2)
    
    # 编辑项目模块
    with edit_col:
        with st.expander("✏️ 编辑项目", expanded=False):
            if projects:
                # 创建项目选择下拉框
                edit_options = {f"{p['id']}: {p['name']}": p['id'] for p in projects}
                selected_edit_key = st.selectbox(
                    "选择项目",
                    options=list(edit_options.keys()),
                    key="edit_project_select_main"
                )
                
                if selected_edit_key:
                    selected_edit_id = edit_options[selected_edit_key]
                    project_to_edit = data_manager.get_project(selected_edit_id)
                    
                    if project_to_edit:
                        with st.form(f"edit_project_form_{selected_edit_id}", clear_on_submit=False):
                            # 基本信息 - 紧凑布局
                            col_a, col_b = st.columns(2)
                            with col_a:
                                edit_name = st.text_input(
                                    "项目名称*",
                                    value=project_to_edit.get("name", ""),
                                    key=f"name_{selected_edit_id}"
                                )
                                edit_leader = st.text_input(
                                    "负责人*",
                                    value=project_to_edit.get("leader", ""),
                                    key=f"leader_{selected_edit_id}"
                                )
                            
                            with col_b:
                                current_status = project_to_edit.get("status", "计划中")
                                status_options = ["计划中", "进行中", "已暂停", "已完成"]
                                status_index = status_options.index(current_status) if current_status in status_options else 0
                                
                                edit_status = st.selectbox(
                                    "状态",
                                    options=status_options,
                                    index=status_index,
                                    key=f"status_{selected_edit_id}"
                                )
                                edit_progress = st.slider(
                                    "进度 (%)",
                                    0, 100,
                                    value=project_to_edit.get("progress", 0),
                                    key=f"progress_{selected_edit_id}"
                                )
                            
                            # 时间和描述 - 紧凑布局
                            col_c, col_d = st.columns(2)
                            with col_c:
                                # 开始日期
                                start_date_str = project_to_edit.get("start_date", "")
                                try:
                                    if start_date_str:
                                        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                                    else:
                                        start_date = datetime.now().date()
                                except (ValueError, TypeError):
                                    start_date = datetime.now().date()
                                
                                edit_start_date = st.date_input(
                                    "开始日期",
                                    value=start_date,
                                    key=f"start_date_{selected_edit_id}"
                                )
                            
                            with col_d:
                                # 结束日期
                                end_date_str = project_to_edit.get("end_date", "")
                                try:
                                    if end_date_str:
                                        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                                    else:
                                        end_date = datetime.now().date() + timedelta(days=60)
                                except (ValueError, TypeError):
                                    end_date = datetime.now().date() + timedelta(days=60)
                                
                                edit_end_date = st.date_input(
                                    "结束日期",
                                    value=end_date,
                                    key=f"end_date_{selected_edit_id}"
                                )
                            
                            # 项目描述
                            edit_description = st.text_area(
                                "项目描述",
                                value=project_to_edit.get("description", ""),
                                height=80,
                                key=f"description_{selected_edit_id}"
                            )
                            
                            # 操作按钮
                            submit_col1, submit_col2 = st.columns(2)
                            with submit_col1:
                                submitted = st.form_submit_button(
                                    "💾 保存修改",
                                    type="primary",
                                    use_container_width=True
                                )
                            
                            with submit_col2:
                                if st.form_submit_button("🔄 重置", use_container_width=True):
                                    st.rerun()
                            
                            # 处理表单提交
                            if submitted:
                                if edit_name and edit_leader:
                                    updated_fields = {
                                        "name": edit_name,
                                        "leader": edit_leader,
                                        "status": edit_status,
                                        "progress": edit_progress,
                                        "start_date": edit_start_date.strftime("%Y-%m-%d"),
                                        "end_date": edit_end_date.strftime("%Y-%m-%d"),
                                        "description": edit_description
                                    }
                                    
                                    if data_manager.update_project(selected_edit_id, updated_fields):
                                        st.success(f"✅ 项目 '{edit_name}' 更新成功！")
                                        time.sleep(0.5)
                                        st.rerun()
                                    else:
                                        st.error("❌ 更新项目失败，请重试")
                                else:
                                    st.error("⚠️ 项目名称和负责人为必填项")
            else:
                st.info("暂无项目可编辑")
    
    # 删除项目模块
    with delete_col:
        with st.expander("🗑️ 删除项目", expanded=False):
            if projects:
                # 创建项目选择下拉框
                project_options = {f"{p['id']}: {p['name']}": p['id'] for p in projects}
                
                selected_delete_key = st.selectbox(
                    "选择项目",
                    options=list(project_options.keys()),
                    key="delete_project_select_main"
                )
                
                if selected_delete_key:
                    selected_delete_id = project_options[selected_delete_key]
                    project_name = selected_delete_key.split(": ")[1]
                    
                    # 初始化会话状态
                    delete_state_key = f"delete_confirm_{selected_delete_id}"
                    if delete_state_key not in st.session_state:
                        st.session_state[delete_state_key] = {
                            "show_confirm": False,
                            "project_name": project_name
                        }
                    
                    st.session_state[delete_state_key]["project_name"] = project_name
                    
                    # 显示确认界面
                    if not st.session_state[delete_state_key]["show_confirm"]:
                        if st.button(
                            "🗑️ 删除项目", 
                            key=f"init_delete_{selected_delete_id}",
                            use_container_width=True,
                            type="secondary"
                        ):
                            st.session_state[delete_state_key]["show_confirm"] = True
                            st.rerun()
                    
                    # 显示二次确认
                    if st.session_state[delete_state_key]["show_confirm"]:
                        current_project = st.session_state[delete_state_key]["project_name"]
                        
                        st.warning(f"⚠️ 确认删除项目: **{current_project}**")
                        st.info("此操作不可恢复，删除后相关实验数据也将丢失。")
                        
                        confirm_col1, confirm_col2 = st.columns(2)
                        
                        with confirm_col1:
                            if st.button(
                                "✅ 确认删除", 
                                key=f"final_confirm_{selected_delete_id}",
                                type="primary",
                                use_container_width=True
                            ):
                                with st.spinner(f"正在删除项目 '{current_project}'..."):
                                    if data_manager.delete_project(selected_delete_id):
                                        st.success(f"✅ 项目 '{current_project}' 已成功删除！")
                                        
                                        if delete_state_key in st.session_state:
                                            del st.session_state[delete_state_key]
                                        
                                        time.sleep(1)
                                        st.rerun()
                                    else:
                                        st.error(f"❌ 删除项目 '{current_project}' 失败")
                                        st.session_state[delete_state_key]["show_confirm"] = False
                        
                        with confirm_col2:
                            if st.button(
                                "❌ 取消", 
                                key=f"cancel_delete_{selected_delete_id}",
                                use_container_width=True
                            ):
                                st.session_state[delete_state_key]["show_confirm"] = False
                                st.info("已取消删除操作")
                                time.sleep(0.5)
                                st.rerun()
            else:
                st.info("暂无项目可删除")
    
    st.divider()
    
    # --- 项目详情总览（所有项目，紧凑卡片布局）---
    st.subheader("📋 项目详情总览")
    
    if projects:
        for i, project in enumerate(projects):
            # 创建项目卡片
            with st.container():
                # 卡片标题行
                status_colors = {
                    "计划中": "🟡",
                    "进行中": "🟢",
                    "已暂停": "🟠",
                    "已完成": "🔵"
                }
                status_emoji = status_colors.get(project.get("status", "计划中"), "⚪")
                
                # 第一行：项目名称和基本信息
                col_title, col_status = st.columns([3, 1])
                with col_title:
                    st.markdown(f"### {status_emoji} {project.get('name', '未命名项目')}")
                with col_status:
                    st.markdown(f"**{project.get('status', '未知')}**")
                
                # 第二行：负责人、时间和描述
                col_info, col_desc = st.columns([2, 2])
                
                with col_info:
                    # 基本信息表格样式
                    st.markdown("""
                    <style>
                    .project-info-row {
                        display: flex;
                        justify-content: space-between;
                        padding: 6px 0;
                        border-bottom: 1px solid #f0f0f0;
                        font-size: 0.9em;
                    }
                    .info-label {
                        font-weight: 600;
                        color: #666;
                    }
                    .info-value {
                        color: #333;
                    }
                    </style>
                    """, unsafe_allow_html=True)
                    
                    st.markdown(f"""
                    <div class="project-info-row">
                        <span class="info-label">负责人</span>
                        <span class="info-value">{project.get('leader', '未指定')}</span>
                    </div>
                    <div class="project-info-row">
                        <span class="info-label">开始时间</span>
                        <span class="info-value">{project.get('start_date', '未设置')}</span>
                    </div>
                    <div class="project-info-row">
                        <span class="info-label">结束时间</span>
                        <span class="info-value">{project.get('end_date', '未设置')}</span>
                    </div>
                    <div class="project-info-row">
                        <span class="info-label">项目描述</span>
                        <span class="info-value">{project.get('description', '暂无描述')[:50]}{'...' if len(project.get('description', '')) > 50 else ''}</span>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col_desc:
                    # 进度和时间线整合展示
                    progress_value = project.get("progress", 0)
                    
                    # 进度条
                    st.markdown(f"**进度:** {progress_value}%")
                    st.progress(progress_value / 100)
                    
                    # 时间线信息
                    timeline_info = data_manager.get_project_timeline(project.get("id"))
                    
                    if timeline_info and timeline_info.get('is_valid'):
                        # 状态和天数信息
                        status = timeline_info.get('status', '未知')
                        status_emoji = timeline_info.get('status_emoji', '📅')
                        passed_days = timeline_info.get('passed_days', 0)
                        total_days = timeline_info.get('total_days', 1)
                        
                        # 显示时间线状态
                        st.markdown(f"**{status_emoji} {status}**")
                        
                        # 显示天数进度
                        timeline_col1, timeline_col2 = st.columns([3, 1])
                        with timeline_col1:
                            percent = timeline_info.get('percent', 0)
                            st.progress(percent / 100)
                        with timeline_col2:
                            st.caption(f"{passed_days}/{total_days}天")
                        
                        # 显示日期范围
                        start_date = timeline_info.get('start_date')
                        end_date = timeline_info.get('end_date')
                        if start_date and end_date:
                            st.caption(f"📅 {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")
                        
                        # 显示额外信息
                        if status == "尚未开始":
                            st.info(f"项目将于 {start_date.strftime('%Y-%m-%d')} 开始")
                        elif status == "已完成":
                            st.success("项目已按时完成")
                        elif status == "进行中":
                            remaining_days = total_days - passed_days
                            if remaining_days > 0:
                                estimated_completion = timeline_info.get('estimated_completion')
                                if estimated_completion:
                                    st.info(f"剩余 {remaining_days} 天，预计 {estimated_completion.strftime('%Y-%m-%d')} 完成")
                    else:
                        st.info("时间线信息不可用")
                
                # 卡片分隔线（最后一个项目不显示）
                if i < len(projects) - 1:
                    st.divider()
    else:
        st.info("暂无项目数据，请点击上方'新增项目'创建第一个项目")
                
    
# -------------------- 实验管理页面 --------------------
def render_experiment_management():
    """渲染实验管理页面 - 集成勾选框删除功能"""
    
    # 定义更新选择状态的辅助函数
    def update_selection(exp_id, checkbox_key):
        """更新实验选择状态的辅助函数"""
        st.session_state.selected_experiments[exp_id] = st.session_state[checkbox_key]
    
    # 初始化编辑状态
    if "editing_experiment_id" not in st.session_state:
        st.session_state.editing_experiment_id = None
    
    if "show_edit_form" not in st.session_state:
        st.session_state.show_edit_form = False
    
    # 初始化分页状态
    if "experiment_page" not in st.session_state:
        st.session_state.experiment_page = 1
    
    # 初始化查找状态
    if "search_filter" not in st.session_state:
        st.session_state.search_filter = {
            "name": "",
            "type": "所有类型",
            "project_id": "所有项目",
            "status": "所有状态",
            "date_range": None,
            "priority": "所有优先级"
        }
    
    if "search_results" not in st.session_state:
        st.session_state.search_results = None
    
    st.header("🧪 实验管理")
    
    # 获取数据
    experiments = data_manager.get_all_experiments()
    projects = data_manager.get_all_projects()
    
    # 创建新实验的表单
    with st.expander("➕ 创建新实验", expanded=False):
        with st.form("create_experiment_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                exp_name = st.text_input("实验名称*")
                exp_type = st.selectbox("实验类型*", ["合成实验", "性能测试", "配方优化", "稳定性测试"])
                
                # 项目选择
                project_options = {p["name"]: p["id"] for p in projects}
                if project_options:
                    selected_project_name = st.selectbox(
                        "所属项目*",
                        options=list(project_options.keys())
                    )
                    project_id = project_options.get(selected_project_name)
                else:
                    st.warning("请先创建项目！")
                    project_id = None
            
            with col2:
                planned_date = st.date_input("计划日期*", datetime.now())
                priority = st.select_slider("优先级", options=["低", "中", "高"], value="中")
                exp_status = st.selectbox("状态", ["计划中", "进行中", "已完成", "已取消"])
            
            description = st.text_area("实验描述")
            
            submitted = st.form_submit_button("创建实验", type="primary")
            if submitted:
                if exp_name and project_id:
                    new_experiment = {
                        "name": exp_name,
                        "type": exp_type,
                        "project_id": project_id,
                        "planned_date": planned_date.strftime("%Y-%m-%d"),
                        "actual_date": planned_date.strftime("%Y-%m-%d") if exp_status == "已完成" else None,
                        "priority": priority,
                        "status": exp_status,
                        "description": description
                    }
                    if data_manager.add_experiment(new_experiment):
                        st.success(f"实验 '{exp_name}' 创建成功！")
                        st.rerun()
                    else:
                        st.error("创建实验失败，请重试")
                else:
                    st.error("请填写必填项")
    
    st.divider()
    
    # --- 新增：实验查找模块 ---
    with st.expander("🔍 查找实验", expanded=True):
        # 查找条件表单
        with st.form("search_experiment_form"):
            # 第一行：名称和类型
            col1, col2 = st.columns(2)
            with col1:
                search_name = st.text_input(
                    "实验名称",
                    value=st.session_state.search_filter["name"],
                    placeholder="输入实验名称关键词"
                )
            
            with col2:
                # 实验类型选项
                type_options = ["所有类型", "合成实验", "性能测试", "配方优化", "稳定性测试"]
                search_type = st.selectbox(
                    "实验类型",
                    options=type_options,
                    index=type_options.index(st.session_state.search_filter["type"]) if st.session_state.search_filter["type"] in type_options else 0
                )
            
            # 第二行：所属项目和状态
            col3, col4 = st.columns(2)
            with col3:
                # 项目选项
                project_options = ["所有项目"] + [p["name"] for p in projects]
                project_name_to_id = {p["name"]: p["id"] for p in projects}
                
                # 查找当前选择的项目在选项中的位置
                current_project_name = None
                if st.session_state.search_filter["project_id"] != "所有项目":
                    for p in projects:
                        if p["id"] == st.session_state.search_filter["project_id"]:
                            current_project_name = p["name"]
                            break
                
                search_project_name = st.selectbox(
                    "所属项目",
                    options=project_options,
                    index=project_options.index(current_project_name) if current_project_name in project_options else 0
                )
                
                # 将项目名称转换回ID
                if search_project_name == "所有项目":
                    search_project_id = "所有项目"
                else:
                    search_project_id = project_name_to_id.get(search_project_name, "所有项目")
            
            with col4:
                # 状态选项
                status_options = ["所有状态", "计划中", "进行中", "已完成", "已取消"]
                search_status = st.selectbox(
                    "状态",
                    options=status_options,
                    index=status_options.index(st.session_state.search_filter["status"]) if st.session_state.search_filter["status"] in status_options else 0
                )
            
            # 第三行：日期范围和优先级
            col5, col6 = st.columns(2)
            with col5:
                # 日期范围选择
                date_options = ["所有日期", "今天", "本周", "本月", "自定义范围"]
                date_range_option = st.selectbox(
                    "日期范围",
                    options=date_options
                )
                
                # 如果选择自定义范围，显示日期选择器
                if date_range_option == "自定义范围":
                    col_date1, col_date2 = st.columns(2)
                    with col_date1:
                        start_date = st.date_input("开始日期", datetime.now() - timedelta(days=30))
                    with col_date2:
                        end_date = st.date_input("结束日期", datetime.now())
                    search_date_range = (start_date, end_date)
                else:
                    search_date_range = None
            
            with col6:
                # 优先级选项
                priority_options = ["所有优先级", "高", "中", "低"]
                search_priority = st.selectbox(
                    "优先级",
                    options=priority_options,
                    index=priority_options.index(st.session_state.search_filter["priority"]) if st.session_state.search_filter["priority"] in priority_options else 0
                )
            
            # 查找和重置按钮
            col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])
            with col_btn1:
                search_submitted = st.form_submit_button(
                    "🔍 查找",
                    type="primary",
                    use_container_width=True
                )
            
            with col_btn2:
                reset_submitted = st.form_submit_button(
                    "🔄 重置",
                    type="secondary",
                    use_container_width=True
                )
            
            with col_btn3:
                st.caption("")
            
            # 处理查找提交
            if search_submitted:
                # 更新查找条件到session_state
                st.session_state.search_filter = {
                    "name": search_name,
                    "type": search_type,
                    "project_id": search_project_id,
                    "status": search_status,
                    "date_range": search_date_range,
                    "priority": search_priority,
                    "date_range_option": date_range_option
                }
                
                # 执行查找
                filtered_experiments = perform_search(experiments, projects, st.session_state.search_filter)
                st.session_state.search_results = filtered_experiments
                st.session_state.experiment_page = 1  # 重置到第一页
                
                st.success(f"查找到 {len(filtered_experiments)} 个实验")
                st.rerun()
            
            # 处理重置提交
            if reset_submitted:
                st.session_state.search_filter = {
                    "name": "",
                    "type": "所有类型",
                    "project_id": "所有项目",
                    "status": "所有状态",
                    "date_range": None,
                    "priority": "所有优先级"
                }
                st.session_state.search_results = None
                st.session_state.experiment_page = 1
                st.info("已重置查找条件")
                st.rerun()
    
    # 显示当前查找条件摘要
    if st.session_state.search_results is not None:
        filter_summary = get_filter_summary(st.session_state.search_filter, projects)
        st.info(f"📋 当前查找条件: {filter_summary}")
    
    # 确定要显示的数据：如果是查找结果则使用查找结果，否则使用所有数据
    display_experiments = st.session_state.search_results if st.session_state.search_results is not None else experiments
    
    # 实验列表（集成勾选框删除功能）
    st.subheader("📋 实验列表")
    
    # 添加CSS样式：调整行高和字体大小
    st.markdown("""
    <style>
    /* 调整实验列表区域字体大小和行高 */
    .experiment-list-area div[data-testid="column"] p,
    .experiment-list-area div[data-testid="column"] code,
    .experiment-list-area div[data-testid="column"] span {
        font-size: 15px !important;
        line-height: 1.2 !important;
        margin-bottom: 4px !important;
        margin-top: 4px !important;
    }
    
    /* 调整表头字体 */
    .experiment-list-area div[data-testid="column"] h1,
    .experiment-list-area div[data-testid="column"] h2,
    .experiment-list-area div[data-testid="column"] h3,
    .experiment-list-area div[data-testid="column"] h4,
    .experiment-list-area div[data-testid="column"] h5,
    .experiment-list-area div[data-testid="column"] h6 {
        font-size: 16px !important;
        margin-bottom: 6px !important;
        margin-top: 6px !important;
    }
    
    /* 调整复选框大小和位置 */
    .experiment-list-area .stCheckbox {
        margin-top: 4px;
        margin-bottom: 4px;
        padding-top: 2px !important;
        padding-bottom: 2px !important;
    }
    
    /* 调整复选框标签 */
    .experiment-list-area .stCheckbox > label {
        padding-top: 2px !important;
        padding-bottom: 2px !important;
        min-height: 24px !important;
    }
    
    /* 调整ID列的代码字体 */
    .experiment-list-area code {
        font-size: 14px !important;
        font-weight: bold;
        padding: 1px 3px !important;
    }
    
    /* 调整实验名称字体 */
    .experiment-list-area strong {
        font-size: 15px !important;
    }
    
    /* 调整状态图标大小 */
    .experiment-list-area span[role="img"] {
        font-size: 16px;
    }
    
    /* 调整列间距 */
    .experiment-list-area div[data-testid="column"] {
        padding-top: 2px !important;
        padding-bottom: 2px !important;
    }
    
    /* 调整行分隔线 */
    .experiment-list-area hr {
        margin-top: 4px !important;
        margin-bottom: 4px !important;
        height: 1px !important;
    }
    
    /* 分页按钮样式 */
    .pagination-buttons .stButton {
        min-height: 28px !important;
    }
    
    /* 紧凑表格样式 */
    .compact-table-row {
        padding: 2px 0 !important;
        margin: 0 !important;
    }
    
    /* 页码信息样式 */
    .page-info {
        text-align: center;
        padding: 6px 0;
        font-size: 14px;
        color: #666;
    }
    
    /* 查找条件标签样式 */
    .filter-tag {
        display: inline-block;
        background-color: #e6f3ff;
        border: 1px solid #91caff;
        border-radius: 12px;
        padding: 2px 8px;
        margin: 2px;
        font-size: 12px;
        color: #0066cc;
    }
    </style>
    """, unsafe_allow_html=True)
    
    if display_experiments:
        # 初始化选择状态
        if "selected_experiments" not in st.session_state:
            st.session_state.selected_experiments = {}
        
        # 批量操作工具栏 - 添加编辑按钮
        with st.container():
            batch_col1, batch_col2, batch_col3, batch_col4, batch_col5 = st.columns([1, 1, 1, 1, 2])
            
            with batch_col1:
                # 全选按钮
                if st.button("全选", key="select_all_btn", use_container_width=True, type="secondary"):
                    # 设置所有实验为选中状态
                    for exp in display_experiments:
                        exp_id = exp["id"]
                        st.session_state.selected_experiments[exp_id] = True
                    st.rerun()
            
            with batch_col2:
                # 取消全选按钮
                if st.button("取消全选", key="deselect_all_btn", use_container_width=True, type="secondary"):
                    # 清除所有选择
                    for exp in display_experiments:
                        exp_id = exp["id"]
                        st.session_state.selected_experiments[exp_id] = False
                    st.rerun()
            
            with batch_col3:
                # 编辑按钮 - 检查是否只选择了一个实验
                selected_count = sum(1 for exp in display_experiments 
                                   if exp["id"] in st.session_state.selected_experiments 
                                   and st.session_state.selected_experiments[exp["id"]])
                
                # 获取选中的实验ID
                selected_exp_ids = []
                for exp in display_experiments:
                    exp_id = exp["id"]
                    if exp_id in st.session_state.selected_experiments:
                        if st.session_state.selected_experiments[exp_id]:
                            selected_exp_ids.append(exp_id)
                
                # 只有选中一个实验时才启用编辑按钮
                if selected_count == 1:
                    edit_disabled = False
                    selected_exp_id = selected_exp_ids[0]
                else:
                    edit_disabled = True
                    selected_exp_id = None
                
                if st.button(
                    "✏️ 编辑", 
                    key="edit_selected_btn",
                    use_container_width=True,
                    type="secondary",
                    disabled=edit_disabled
                ) and selected_exp_id:
                    st.session_state.editing_experiment_id = selected_exp_id
                    st.session_state.show_edit_form = True
                    st.rerun()
            
            with batch_col4:
                # 刷新列表按钮
                if st.button("🔄 刷新", key="refresh_list", use_container_width=True, type="secondary"):
                    st.rerun()
            
            with batch_col5:
                # 统计信息
                selected_count = sum(1 for exp in display_experiments 
                                   if exp["id"] in st.session_state.selected_experiments 
                                   and st.session_state.selected_experiments[exp["id"]])
                
                # 显示查找结果计数
                if st.session_state.search_results is not None:
                    status_text = f"查找到 {len(display_experiments)} 个实验，已选择 {selected_count} 个"
                else:
                    status_text = f"共 {len(display_experiments)} 个实验，已选择 {selected_count} 个"
                
                # 如果只选择了一个实验，显示实验名称
                if selected_count == 1:
                    selected_exp_id = selected_exp_ids[0]
                    selected_exp = next((e for e in display_experiments if e["id"] == selected_exp_id), None)
                    if selected_exp:
                        status_text = f"已选择: {selected_exp['name']}"
                
                st.caption(status_text)
        
        # 实验编辑表单
        if st.session_state.show_edit_form and st.session_state.editing_experiment_id:
            editing_exp = next((e for e in experiments if e["id"] == st.session_state.editing_experiment_id), None)
            
            if editing_exp:
                # 查找所属项目名称
                editing_project_name = "未知项目"
                for p in projects:
                    if p.get("id") == editing_exp.get("project_id"):
                        editing_project_name = p.get("name")
                        break
                
                with st.expander(f"✏️ 编辑实验: {editing_exp['name']}", expanded=True):
                    with st.form("edit_experiment_form"):
                        col1, col2 = st.columns(2)
                        with col1:
                            edit_exp_name = st.text_input(
                                "实验名称*", 
                                value=editing_exp.get("name", ""),
                                key="edit_exp_name"
                            )
                            edit_exp_type = st.selectbox(
                                "实验类型*", 
                                ["合成实验", "性能测试", "配方优化", "稳定性测试"],
                                index=["合成实验", "性能测试", "配方优化", "稳定性测试"].index(editing_exp.get("type", "合成实验")),
                                key="edit_exp_type"
                            )
                            
                            # 项目选择
                            project_options = {p["name"]: p["id"] for p in projects}
                            if project_options:
                                # 查找当前项目在选项中的位置
                                current_project_name = None
                                for p_name, p_id in project_options.items():
                                    if p_id == editing_exp.get("project_id"):
                                        current_project_name = p_name
                                        break
                                
                                # 如果没有找到，使用第一个项目
                                if current_project_name is None and project_options:
                                    current_project_name = list(project_options.keys())[0]
                                
                                edit_project_name = st.selectbox(
                                    "所属项目*",
                                    options=list(project_options.keys()),
                                    index=list(project_options.keys()).index(current_project_name) if current_project_name in project_options else 0,
                                    key="edit_project_select"
                                )
                                edit_project_id = project_options.get(edit_project_name)
                        
                        with col2:
                            # 解析计划日期
                            planned_date_str = editing_exp.get("planned_date", "")
                            try:
                                if planned_date_str:
                                    edit_planned_date = st.date_input(
                                        "计划日期*", 
                                        value=datetime.strptime(planned_date_str, "%Y-%m-%d"),
                                        key="edit_planned_date"
                                    )
                                else:
                                    edit_planned_date = st.date_input(
                                        "计划日期*", 
                                        value=datetime.now(),
                                        key="edit_planned_date"
                                    )
                            except (ValueError, TypeError):
                                edit_planned_date = st.date_input(
                                    "计划日期*", 
                                    value=datetime.now(),
                                    key="edit_planned_date"
                                )
                            
                            priority_options = ["低", "中", "高"]
                            current_priority = editing_exp.get("priority", "中")
                            priority_index = priority_options.index(current_priority) if current_priority in priority_options else 1
                            
                            edit_priority = st.select_slider(
                                "优先级", 
                                options=priority_options,
                                value=priority_options[priority_index],
                                key="edit_priority"
                            )
                            
                            status_options = ["计划中", "进行中", "已完成", "已取消"]
                            current_status = editing_exp.get("status", "计划中")
                            status_index = status_options.index(current_status) if current_status in status_options else 0
                            
                            edit_status = st.selectbox(
                                "状态", 
                                status_options,
                                index=status_index,
                                key="edit_status"
                            )
                        
                        edit_description = st.text_area(
                            "实验描述", 
                            value=editing_exp.get("description", ""),
                            height=100,
                            key="edit_description"
                        )
                        
                        # 操作按钮
                        col_btn1, col_btn2, col_btn3 = st.columns(3)
                        
                        with col_btn1:
                            save_submitted = st.form_submit_button(
                                "💾 保存修改", 
                                type="primary",
                                use_container_width=True
                            )
                        
                        with col_btn2:
                            if st.form_submit_button(
                                "🔄 重置表单", 
                                type="secondary",
                                use_container_width=True
                            ):
                                st.rerun()
                        
                        with col_btn3:
                            cancel_submitted = st.form_submit_button(
                                "❌ 取消编辑", 
                                type="secondary",
                                use_container_width=True
                            )
                        
                        # 处理表单提交
                        if save_submitted:
                            if edit_exp_name and edit_project_id:
                                # 构建更新后的实验数据
                                updated_experiment = {
                                    "name": edit_exp_name,
                                    "type": edit_exp_type,
                                    "project_id": edit_project_id,
                                    "planned_date": edit_planned_date.strftime("%Y-%m-%d"),
                                    "actual_date": edit_planned_date.strftime("%Y-%m-%d") if edit_status == "已完成" else None,
                                    "priority": edit_priority,
                                    "status": edit_status,
                                    "description": edit_description,
                                    "id": st.session_state.editing_experiment_id  # 保持ID不变
                                }
                                
                                # 注意：这里需要添加一个update_experiment方法到DataManager
                                # 我先假设已经有了，如果没有需要先实现
                                try:
                                    # 临时保存原数据用于回滚
                                    original_data = data_manager.load_data()
                                    experiments_data = original_data.get("experiments", [])
                                    
                                    # 查找并更新实验
                                    updated = False
                                    for i, exp in enumerate(experiments_data):
                                        if exp.get("id") == st.session_state.editing_experiment_id:
                                            experiments_data[i] = updated_experiment
                                            updated = True
                                            break
                                    
                                    if updated:
                                        original_data["experiments"] = experiments_data
                                        if data_manager.save_data(original_data):
                                            st.success(f"✅ 实验 '{edit_exp_name}' 更新成功！")
                                            
                                            # 清空编辑状态
                                            st.session_state.editing_experiment_id = None
                                            st.session_state.show_edit_form = False
                                            
                                            # 清空选择
                                            for exp in experiments:
                                                exp_id = exp["id"]
                                                st.session_state.selected_experiments[exp_id] = False
                                            
                                            time.sleep(1)
                                            st.rerun()
                                        else:
                                            st.error("❌ 保存修改失败，请重试")
                                    else:
                                        st.error("❌ 未找到要更新的实验")
                                except Exception as e:
                                    st.error(f"❌ 更新实验时出错: {e}")
                            else:
                                st.error("⚠️ 实验名称和所属项目为必填项")
                        
                        if cancel_submitted:
                            st.session_state.editing_experiment_id = None
                            st.session_state.show_edit_form = False
                            st.info("已取消编辑操作")
                            time.sleep(0.5)
                            st.rerun()
        
        # 分页设置
        PAGE_SIZE = 20
        total_experiments = len(display_experiments)
        total_pages = (total_experiments + PAGE_SIZE - 1) // PAGE_SIZE  # 向上取整
        
        # 确保当前页码有效
        if st.session_state.experiment_page < 1:
            st.session_state.experiment_page = 1
        elif st.session_state.experiment_page > total_pages and total_pages > 0:
            st.session_state.experiment_page = total_pages
        
        # 获取当前页的实验数据
        start_idx = (st.session_state.experiment_page - 1) * PAGE_SIZE
        end_idx = min(start_idx + PAGE_SIZE, total_experiments)
        current_page_experiments = display_experiments[start_idx:end_idx]
        
        # 创建带勾选框的实验表格
        st.markdown("---")
        
        # 使用CSS类包装整个实验列表区域
        st.markdown('<div class="experiment-list-area">', unsafe_allow_html=True)
        
        # 表头
        col_header = st.columns([1, 2, 2, 2, 2, 2, 2, 3])
        headers = ["选择", "ID", "实验名称", "类型", "所属项目", "计划日期", "状态", "描述"]
        for i, header in enumerate(headers):
            # 使用紧凑的字体渲染表头
            col_header[i].markdown(f"<h5 style='margin:0; padding:4px 0; font-size:15px;'>{header}</h5>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        # 实验行数据 - 只显示当前页
        for exp in current_page_experiments:
            # 查找项目名称
            project_name = "未知项目"
            for p in projects:
                if p.get("id") == exp.get("project_id"):
                    project_name = p.get("name")
                    break
            
            # 获取实验信息
            exp_id = exp.get("id")
            exp_name = exp.get("name", "未命名")
            exp_type = exp.get("type", "")
            exp_plan_date = exp.get("planned_date", "")
            exp_status = exp.get("status", "")
            exp_desc = exp.get("description", "")[:25] + "..." if len(exp.get("description", "")) > 25 else exp.get("description", "")
            
            # 创建一行 - 使用紧凑布局
            col_row = st.columns([1, 2, 2, 2, 2, 2, 2, 3])
            
            # 勾选框 - 直接使用session_state
            with col_row[0]:
                # 从session_state获取当前值，如果不存在则默认为False
                current_value = st.session_state.selected_experiments.get(exp_id, False)
                
                # 创建复选框，使用唯一的key
                checkbox_key = f"exp_checkbox_{exp_id}"
                
                # 每次渲染时，确保checkbox的值与session_state.selected_experiments同步
                if checkbox_key not in st.session_state:
                    st.session_state[checkbox_key] = current_value
                
                # 渲染复选框
                is_selected = st.checkbox(
                    "",
                    value=st.session_state[checkbox_key],  # 使用独立的session_state键
                    key=checkbox_key,
                    label_visibility="collapsed",
                    on_change=lambda exp_id=exp_id, key=checkbox_key: update_selection(exp_id, key)
                )
                
                # 同步状态到我们的selected_experiments字典
                st.session_state.selected_experiments[exp_id] = is_selected
            
            # 其他列数据 - 使用紧凑的字体
            with col_row[1]:
                st.markdown(f"<span style='font-size:14px; font-weight:bold; padding:2px 0; display:block;'>`{exp_id}`</span>", unsafe_allow_html=True)
            
            with col_row[2]:
                st.markdown(f"<strong style='font-size:14px; padding:2px 0; display:block;'>{exp_name}</strong>", unsafe_allow_html=True)
            
            with col_row[3]:
                st.markdown(f"<span style='font-size:14px; padding:2px 0; display:block;'>{exp_type}</span>", unsafe_allow_html=True)
            
            with col_row[4]:
                st.markdown(f"<span style='font-size:14px; padding:2px 0; display:block;'>{project_name}</span>", unsafe_allow_html=True)
            
            with col_row[5]:
                st.markdown(f"<span style='font-size:14px; padding:2px 0; display:block;'>{exp_plan_date}</span>", unsafe_allow_html=True)
            
            with col_row[6]:
                # 状态标签颜色
                status_colors = {
                    "计划中": "🟡",
                    "进行中": "🟢",
                    "已完成": "✅",
                    "已取消": "❌"
                }
                status_emoji = status_colors.get(exp_status, "⚪")
                st.markdown(f"<span style='font-size:14px; padding:2px 0; display:block;'>{status_emoji} {exp_status}</span>", unsafe_allow_html=True)
            
            with col_row[7]:
                st.markdown(f"<span style='font-size:13px; padding:2px 0; display:block;'>{exp_desc}</span>", unsafe_allow_html=True)
            
            # 更细的行分隔线
            st.markdown("<hr style='margin:2px 0; height:0.5px;'>", unsafe_allow_html=True)
        
        # 关闭CSS包装器
        st.markdown('</div>', unsafe_allow_html=True)
        
        # --- 分页控制：移动到表格下方 ---
        if total_pages > 1:
            # 分页控制容器
            st.markdown("---")
            
            # 分页信息
            current_page = st.session_state.experiment_page
            start_num = (current_page - 1) * PAGE_SIZE + 1
            end_num = min(current_page * PAGE_SIZE, total_experiments)
            
            # 页码信息行
            info_col1, info_col2, info_col3 = st.columns([1, 2, 1])
            
            with info_col2:
                st.markdown(
                    f"<div class='page-info'>"
                    f"第 <strong>{current_page}</strong> 页 / 共 <strong>{total_pages}</strong> 页 · "
                    f"显示 <strong>{start_num}-{end_num}</strong> 条，共 <strong>{total_experiments}</strong> 条"
                    f"</div>", 
                    unsafe_allow_html=True
                )
            
            # 分页按钮行
            pagination_col1, pagination_col2, pagination_col3, pagination_col4 = st.columns([2, 1, 1, 2])
            
            with pagination_col2:
                # 上一页按钮
                if st.button(
                    "⬅️ 上一页", 
                    key="prev_page", 
                    disabled=st.session_state.experiment_page <= 1, 
                    use_container_width=True,
                    type="secondary"
                ):
                    st.session_state.experiment_page -= 1
                    st.rerun()
            
            with pagination_col3:
                # 下一页按钮
                if st.button(
                    "下一页 ➡️", 
                    key="next_page", 
                    disabled=st.session_state.experiment_page >= total_pages, 
                    use_container_width=True,
                    type="secondary"
                ):
                    st.session_state.experiment_page += 1
                    st.rerun()
            
            # 快速跳转行
            if total_pages > 5:
                jump_col1, jump_col2, jump_col3 = st.columns([1, 2, 1])
                
                with jump_col2:
                    # 快速跳转输入框
                    jump_page = st.number_input(
                        "跳转到",
                        min_value=1,
                        max_value=total_pages,
                        value=st.session_state.experiment_page,
                        key="jump_page_input",
                        label_visibility="collapsed",
                        step=1
                    )
                    
                    if jump_page != st.session_state.experiment_page:
                        st.session_state.experiment_page = jump_page
                        st.rerun()
        
        # 批量删除功能
        st.markdown("### 🗑️ 批量删除")
        
        # 统计选中的实验（所有页面的选中状态都会被统计）
        selected_exp_ids = []
        for exp in display_experiments:
            exp_id = exp["id"]
            if exp_id in st.session_state.selected_experiments:
                if st.session_state.selected_experiments[exp_id]:
                    selected_exp_ids.append(exp_id)
        
        if selected_exp_ids:
            # 获取选中的实验名称
            selected_exp_names = []
            for exp in display_experiments:
                if exp["id"] in selected_exp_ids:
                    selected_exp_names.append(exp["name"])
            
            st.warning(f"⚠️ 已选择 {len(selected_exp_ids)} 个实验进行删除")
            
            # 显示选中的实验列表
            with st.expander("📋 查看选中实验", expanded=False):
                for i, exp_id in enumerate(selected_exp_ids):
                    exp_info = next((e for e in display_experiments if e["id"] == exp_id), None)
                    if exp_info:
                        st.markdown(f"{i+1}. **{exp_info['name']}** (ID: {exp_id})")
            
            # 删除确认
            delete_col1, delete_col2 = st.columns(2)
            
            with delete_col1:
                if st.button(
                    "🗑️ 删除选中", 
                    key="delete_selected_exps",
                    use_container_width=True,
                    type="primary"
                ):
                    # 设置确认状态
                    st.session_state.confirm_batch_delete = True
                    st.rerun()
            
            with delete_col2:
                if st.button(
                    "❌ 取消", 
                    key="cancel_batch_delete",
                    use_container_width=True,
                    type="secondary"
                ):
                    # 清空选择
                    for exp in display_experiments:
                        exp_id = exp["id"]
                        st.session_state.selected_experiments[exp_id] = False
                        # 同时清除对应的checkbox键
                        checkbox_key = f"exp_checkbox_{exp_id}"
                        if checkbox_key in st.session_state:
                            st.session_state[checkbox_key] = False
                    st.rerun()
            
            # 确认对话框
            if "confirm_batch_delete" in st.session_state and st.session_state.confirm_batch_delete:
                with st.container(border=True):
                    st.markdown("#### ⚠️ 确认批量删除")
                    st.error("**危险操作！** 此操作将永久删除以下实验，不可恢复！")
                    
                    # 列出将要删除的实验
                    st.markdown("**将要删除的实验:**")
                    for i, exp_id in enumerate(selected_exp_ids):
                        exp_info = next((e for e in display_experiments if e["id"] == exp_id), None)
                        if exp_info:
                            st.markdown(f"- **{exp_info['name']}** (ID: {exp_id})")
                    
                    # 双重确认
                    st.markdown("---")
                    confirm_text = st.text_input(
                        "请输入 '确认删除' 以继续:",
                        key="batch_delete_confirm_text",
                        placeholder="请输入 '确认删除'"
                    )
                    
                    confirm_col1, confirm_col2 = st.columns(2)
                    
                    with confirm_col1:
                        if st.button(
                            "✅ 确认删除", 
                            key="final_batch_delete",
                            use_container_width=True,
                            type="primary",
                            disabled=confirm_text != "确认删除"
                        ):
                            with st.spinner("正在删除选中的实验..."):
                                success_count = 0
                                error_count = 0
                                
                                for exp_id in selected_exp_ids:
                                    if data_manager.delete_experiment(exp_id):
                                        success_count += 1
                                    else:
                                        error_count += 1
                                
                                # 清理会话状态
                                del st.session_state.confirm_batch_delete
                                
                                # 清空选择状态
                                for exp_id in selected_exp_ids:
                                    if exp_id in st.session_state.selected_experiments:
                                        st.session_state.selected_experiments[exp_id] = False
                                    # 清除对应的checkbox键
                                    checkbox_key = f"exp_checkbox_{exp_id}"
                                    if checkbox_key in st.session_state:
                                        st.session_state[checkbox_key] = False
                                
                                if error_count == 0:
                                    st.success(f"✅ 成功删除 {success_count} 个实验！")
                                else:
                                    st.warning(f"⚠️ 成功删除 {success_count} 个实验，{error_count} 个删除失败")
                                
                                time.sleep(1.5)
                                st.rerun()
                    
                    with confirm_col2:
                        if st.button(
                            "❌ 取消删除", 
                            key="cancel_final_delete",
                            use_container_width=True,
                            type="secondary"
                        ):
                            del st.session_state.confirm_batch_delete
                            st.info("已取消批量删除操作")
                            time.sleep(0.5)
                            st.rerun()
        else:
            st.info("请先勾选要删除的实验")
            
            # 快速操作提示
            with st.expander("💡 使用提示", expanded=False):
                st.markdown("""
                1. **勾选实验**: 点击每行前面的复选框选择实验
                2. **全选**: 点击"全选"按钮一次性选择所有实验
                3. **取消全选**: 点击"取消全选"按钮取消所有选择
                4. **编辑实验**: 勾选一个实验后，点击"编辑"按钮修改实验信息
                5. **刷新**: 点击"刷新"按钮重新加载实验列表
                6. **分页浏览**: 使用表格下方的分页控制浏览所有实验
                7. **批量删除**: 选择实验后，点击"删除选中"按钮进行批量删除
                8. **防误删**: 删除操作需要双重确认，防止误操作
                """)
    else:
        if st.session_state.search_results is not None:
            st.warning("未找到符合条件的实验，请尝试修改查找条件")
        else:
            st.info("暂无实验数据，请创建第一个实验。")
    
    # 添加清除查找结果按钮
    if st.session_state.search_results is not None:
        st.markdown("---")
        if st.button("❌ 清除查找结果，显示所有实验", use_container_width=True, type="secondary"):
            st.session_state.search_results = None
            st.session_state.experiment_page = 1
            st.rerun()

def perform_search(experiments, projects, search_filter):
    """根据查找条件筛选实验"""
    filtered = experiments.copy()
    
    # 1. 按实验名称筛选（模糊匹配）
    if search_filter["name"]:
        filtered = [exp for exp in filtered if search_filter["name"].lower() in exp.get("name", "").lower()]
    
    # 2. 按实验类型筛选
    if search_filter["type"] != "所有类型":
        filtered = [exp for exp in filtered if exp.get("type") == search_filter["type"]]
    
    # 3. 按所属项目筛选
    if search_filter["project_id"] != "所有项目":
        filtered = [exp for exp in filtered if exp.get("project_id") == search_filter["project_id"]]
    
    # 4. 按状态筛选
    if search_filter["status"] != "所有状态":
        filtered = [exp for exp in filtered if exp.get("status") == search_filter["status"]]
    
    # 5. 按优先级筛选
    if search_filter["priority"] != "所有优先级":
        filtered = [exp for exp in filtered if exp.get("priority") == search_filter["priority"]]
    
    # 6. 按日期范围筛选
    if search_filter.get("date_range_option") and search_filter["date_range_option"] != "所有日期":
        date_range_option = search_filter["date_range_option"]
        
        if date_range_option == "今天":
            today = datetime.now().date()
            filtered = [exp for exp in filtered if exp.get("planned_date") == today.strftime("%Y-%m-%d")]
        
        elif date_range_option == "本周":
            today = datetime.now().date()
            start_of_week = today - timedelta(days=today.weekday())
            end_of_week = start_of_week + timedelta(days=6)
            
            filtered = [exp for exp in filtered if exp.get("planned_date")]
            filtered = [exp for exp in filtered if 
                       start_of_week <= datetime.strptime(exp.get("planned_date"), "%Y-%m-%d").date() <= end_of_week]
        
        elif date_range_option == "本月":
            today = datetime.now().date()
            start_of_month = today.replace(day=1)
            if today.month == 12:
                end_of_month = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end_of_month = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
            
            filtered = [exp for exp in filtered if exp.get("planned_date")]
            filtered = [exp for exp in filtered if 
                       start_of_month <= datetime.strptime(exp.get("planned_date"), "%Y-%m-%d").date() <= end_of_month]
        
        elif date_range_option == "自定义范围" and search_filter["date_range"]:
            start_date, end_date = search_filter["date_range"]
            filtered = [exp for exp in filtered if exp.get("planned_date")]
            filtered = [exp for exp in filtered if 
                       start_date <= datetime.strptime(exp.get("planned_date"), "%Y-%m-%d").date() <= end_date]
    
    return filtered

def get_filter_summary(search_filter, projects):
    """获取查找条件摘要"""
    summary_parts = []
    
    if search_filter["name"]:
        summary_parts.append(f"名称: {search_filter['name']}")
    
    if search_filter["type"] != "所有类型":
        summary_parts.append(f"类型: {search_filter['type']}")
    
    if search_filter["project_id"] != "所有项目":
        project_name = "未知项目"
        for p in projects:
            if p["id"] == search_filter["project_id"]:
                project_name = p["name"]
                break
        summary_parts.append(f"项目: {project_name}")
    
    if search_filter["status"] != "所有状态":
        summary_parts.append(f"状态: {search_filter['status']}")
    
    if search_filter["priority"] != "所有优先级":
        summary_parts.append(f"优先级: {search_filter['priority']}")
    
    if search_filter.get("date_range_option") and search_filter["date_range_option"] != "所有日期":
        date_option = search_filter["date_range_option"]
        if date_option == "自定义范围" and search_filter["date_range"]:
            start_date, end_date = search_filter["date_range"]
            summary_parts.append(f"日期: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")
        else:
            summary_parts.append(f"日期: {date_option}")
    
    return " | ".join(summary_parts) if summary_parts else "无筛选条件"

# -------------------- 数据记录页面 --------------------
def render_data_recording():
    """渲染数据记录页面 - 完整重构版"""
    import uuid
    
    st.header("📝 数据记录")
    
    # 检查数据管理器
    try:
        from main import data_manager
    except ImportError:
        st.error("无法加载数据管理器，请确保系统初始化正确")
        return
    
    # 获取实验项目和实验数据
    try:
        experiments = data_manager.get_all_experiments()
        projects = data_manager.get_all_projects()
    except Exception as e:
        st.error(f"加载数据失败: {e}")
        experiments = []
        projects = []
    
    # 使用选项卡分为四个功能模块
    tab1, tab2, tab3, tab4 = st.tabs(["🧪 合成实验", "🥣 净浆实验", "🏗️ 砂浆实验", "🏢 混凝土实验"])
    
    # ==================== 辅助函数 ====================
    def get_experiment_options(exp_type=None):
        """根据实验类型获取实验选项"""
        options = {}
        for exp in experiments:
            if exp_type and exp.get("type") != exp_type:
                continue
            # 查找项目名称
            project_name = "未知项目"
            for proj in projects:
                if proj.get("id") == exp.get("project_id"):
                    project_name = proj.get("name", "未知项目")
                    break
            # 使用实验ID和名称作为选项
            exp_key = f"{exp['id']}: {exp['name']} - {project_name} ({exp.get('type', '未知类型')})"
            options[exp_key] = exp['id']
        return options
    
    def save_performance_data(data_type, record_data):
        """保存性能数据到JSON文件"""
        try:
            # 加载现有数据
            data = data_manager.load_data()
            
            # 初始化数据结构
            if "performance_data" not in data:
                data["performance_data"] = {
                    "synthesis": [],
                    "paste": [],
                    "mortar": [],
                    "concrete": []
                }
            
            if data_type not in data["performance_data"]:
                data["performance_data"][data_type] = []
            
            # 添加新记录
            data["performance_data"][data_type].append(record_data)
            
            # 保存数据
            return data_manager.save_data(data)
        except Exception as e:
            st.error(f"保存数据时出错: {e}")
            return False
    
    # ==================== 1. 合成实验数据记录 ====================
    with tab1:
        st.subheader("🧪 合成实验数据记录")
        
        # 初始化表单状态
        if "synthesis_form_state" not in st.session_state:
            st.session_state.synthesis_form_state = {
                "show_save_confirmation": False,
                "saved_data": None
            }
        
        # 创建三列布局
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            # 实验选择
            exp_options = get_experiment_options("合成实验")
            if exp_options:
                selected_exp_key = st.selectbox(
                    "选择实验项目*",
                    options=list(exp_options.keys()),
                    key="synthesis_exp_select",
                    help="选择要进行合成实验的项目"
                )
                selected_exp_id = exp_options.get(selected_exp_key)
                
                # 显示实验信息
                if selected_exp_id:
                    selected_exp = None
                    for exp in experiments:
                        if exp.get("id") == selected_exp_id:
                            selected_exp = exp
                            break
                    
                    if selected_exp:
                        st.info(f"""
                        **实验信息:**
                        - 项目ID: {selected_exp.get('project_id', 'N/A')}
                        - 计划日期: {selected_exp.get('planned_date', 'N/A')}
                        - 状态: {selected_exp.get('status', 'N/A')}
                        """)
            else:
                st.warning("暂无合成实验项目，请在实验管理中创建")
                selected_exp_id = None
            
            # 基础信息
            with st.container(border=True):
                st.markdown("### 📋 基础信息")
                record_date = st.date_input(
                    "记录日期*", 
                    datetime.now(), 
                    key="synthesis_date",
                    help="实验记录日期"
                )
                operator = st.text_input(
                    "操作人*", 
                    value="徐梓馨", 
                    key="synthesis_operator",
                    help="实验操作人员"
                )
                batch_no = st.text_input(
                    "批次号*", 
                    placeholder="例如: SYN-20240106-001", 
                    key="synthesis_batch",
                    help="合成实验批次编号"
                )
                formula_id = st.text_input(
                    "配方编号", 
                    placeholder="例如: F-001", 
                    key="synthesis_formula",
                    help="使用的配方编号"
                )
        
        with col2:
            # 性能指标
            with st.container(border=True):
                st.markdown("### 📊 性能指标")
                col_metric1, col_metric2 = st.columns(2)
                with col_metric1:
                    water_reduction = st.number_input(
                        "减水率 (%)", 
                        min_value=0.0, 
                        max_value=100.0, 
                        value=18.5, 
                        step=0.1, 
                        key="synthesis_water_reduction",
                        help="合成产品的减水率"
                    )
                    solid_content = st.number_input(
                        "固含量 (%)", 
                        min_value=0.0, 
                        max_value=100.0, 
                        value=40.0, 
                        step=0.1, 
                        key="synthesis_solid",
                        help="合成产品的固含量"
                    )
                    ph_value = st.number_input(
                        "pH值", 
                        min_value=0.0, 
                        max_value=14.0, 
                        value=7.0, 
                        step=0.1, 
                        key="synthesis_ph",
                        help="合成产品的pH值"
                    )
                
                with col_metric2:
                    density = st.number_input(
                        "密度 (g/cm³)", 
                        min_value=0.0, 
                        max_value=2.0, 
                        value=1.05, 
                        step=0.01, 
                        key="synthesis_density",
                        help="合成产品的密度"
                    )
                    viscosity = st.number_input(
                        "粘度 (mPa·s)", 
                        min_value=0.0, 
                        max_value=10000.0, 
                        value=50.0, 
                        step=1.0, 
                        key="synthesis_viscosity",
                        help="合成产品的粘度"
                    )
                    stability = st.selectbox(
                        "稳定性", 
                        ["优良", "良好", "一般", "较差"], 
                        key="synthesis_stability",
                        help="产品的稳定性评估"
                    )
                    color = st.text_input(
                        "颜色", 
                        placeholder="例如: 淡黄色", 
                        key="synthesis_color",
                        help="产品的颜色描述"
                    )
        
        with col3:
            # 反应条件
            with st.container(border=True):
                st.markdown("### 🔥 反应条件")
                reaction_temp = st.number_input(
                    "反应温度 (°C)", 
                    min_value=0.0, 
                    max_value=200.0, 
                    value=60.0, 
                    step=0.5, 
                    key="synthesis_temp",
                    help="合成反应温度"
                )
                reaction_time = st.number_input(
                    "反应时间 (小时)", 
                    min_value=0.0, 
                    max_value=24.0, 
                    value=4.0, 
                    step=0.5, 
                    key="synthesis_time",
                    help="合成反应时间"
                )
                nitrogen_time = st.number_input(
                    "氮气保护时间 (分钟)", 
                    min_value=0, 
                    max_value=120, 
                    value=30, 
                    step=5, 
                    key="synthesis_nitrogen",
                    help="氮气保护时间"
                )
        
        # ==================== 合成工艺参数 ====================
        # 1. 反应釜部分
        with st.expander("⚙️ 反应釜部分", expanded=True):
            st.markdown("#### 反应釜物料 (g)")
            
            col_reactor1, col_reactor2, col_reactor3, col_reactor4 = st.columns(4)
            
            with col_reactor1:
                big_monomer = st.number_input("大单体", min_value=0.0, value=100.0, step=1.0, key="big_monomer")
                small_monomer1 = st.number_input("小单体1", min_value=0.0, value=20.0, step=1.0, key="small_monomer1")
            
            with col_reactor2:
                small_monomer2 = st.number_input("小单体2", min_value=0.0, value=15.0, step=1.0, key="small_monomer2")
                small_monomer3 = st.number_input("小单体3", min_value=0.0, value=10.0, step=1.0, key="small_monomer3")
            
            with col_reactor3:
                catalyst = st.number_input("催化剂", min_value=0.0, value=1.0, step=0.1, key="catalyst")
                chain_transfer1 = st.number_input("链转移剂1", min_value=0.0, value=0.5, step=0.1, key="chain_transfer1")
            
            with col_reactor4:
                initiator1 = st.number_input("引发剂", min_value=0.0, value=0.2, step=0.1, key="initiator1")
                water1 = st.number_input("水", min_value=0.0, value=200.0, step=1.0, key="water1")
            
            # 计算反应釜总质量
            reactor_total = big_monomer + small_monomer1 + small_monomer2 + small_monomer3 + catalyst + chain_transfer1 + initiator1 + water1
            
            # 滴加控制参数
            st.markdown("#### 滴加控制参数")
            col_drop1, col_drop2 = st.columns(2)
            
            with col_drop1:
                drop_start_temp = st.number_input("滴加起始温度 (°C)", min_value=0.0, max_value=200.0, value=60.0, step=0.5, key="drop_start_temp")
                max_temp_limit = st.number_input("最高温度限制 (°C)", min_value=0.0, max_value=200.0, value=80.0, step=0.5, key="max_temp_limit")
            
            with col_drop2:
                drop_time_A = st.number_input("A料滴加时间 (min)", min_value=0, max_value=300, value=120, step=5, key="drop_time_A")
                drop_time_B = st.number_input("B料滴加时间 (min)", min_value=0, max_value=300, value=180, step=5, key="drop_time_B")
            
            # 显示反应釜总质量
            st.info(f"反应釜总质量: **{reactor_total:.1f} g**")
        
        # 2. A料部分
        with st.expander("🔬 A料部分", expanded=False):
            st.markdown("#### A料组成 (g)")
            
            col_A1, col_A2, col_A3 = st.columns(3)
            
            with col_A1:
                monomer1_A = st.number_input("单体1", min_value=0.0, value=30.0, step=1.0, key="monomer1_A")
                monomer2_A = st.number_input("单体2", min_value=0.0, value=25.0, step=1.0, key="monomer2_A")
            
            with col_A2:
                monomer3_A = st.number_input("单体3", min_value=0.0, value=20.0, step=1.0, key="monomer3_A")
                monomer4_A = st.number_input("单体4", min_value=0.0, value=15.0, step=1.0, key="monomer4_A")
            
            with col_A3:
                water_A = st.number_input("水", min_value=0.0, value=100.0, step=1.0, key="water_A")
            
            # 计算A料总量和滴加速度
            total_A = monomer1_A + monomer2_A + monomer3_A + monomer4_A + water_A
            drop_speed_A = total_A / drop_time_A if drop_time_A > 0 else 0
            
            col_calc1, col_calc2 = st.columns(2)
            with col_calc1:
                st.metric("A料总质量 (g)", f"{total_A:.1f}")
            with col_calc2:
                st.metric("A料滴加速度 (g/min)", f"{drop_speed_A:.1f}")
        
        # 3. B料部分
        with st.expander("🔬 B料部分", expanded=False):
            st.markdown("#### B料组成 (g)")
            
            col_B1, col_B2, col_B3 = st.columns(3)
            
            with col_B1:
                initiator2_B = st.number_input("引发剂2", min_value=0.0, value=0.5, step=0.1, key="initiator2_B")
                chain_transfer2_B = st.number_input("链转移剂2", min_value=0.0, value=0.3, step=0.1, key="chain_transfer2_B")
            
            with col_B2:
                other1_B = st.number_input("其他物料1", min_value=0.0, value=1.0, step=0.1, key="other1_B")
                other2_B = st.number_input("其他物料2", min_value=0.0, value=1.0, step=0.1, key="other2_B")
            
            with col_B3:
                water_B = st.number_input("水", min_value=0.0, value=50.0, step=1.0, key="water_B")
            
            # 计算B料总量和滴加速度
            total_B = initiator2_B + chain_transfer2_B + other1_B + other2_B + water_B
            drop_speed_B = total_B / drop_time_B if drop_time_B > 0 else 0
            
            col_calc1, col_calc2 = st.columns(2)
            with col_calc1:
                st.metric("B料总质量 (g)", f"{total_B:.1f}")
            with col_calc2:
                st.metric("B料滴加速度 (g/min)", f"{drop_speed_B:.1f}")
        
        # 4. 成品减水剂模块（可选）
        with st.expander("📦 成品减水剂（可选）", expanded=False):
            st.markdown("### 成品减水剂信息")
            st.info("此部分为可选内容，如果合成实验生成了成品减水剂，请填写以下信息")
            
            col_product1, col_product2 = st.columns(2)
            
            with col_product1:
                product_name = st.text_input("产品名称", placeholder="例如: PC-100", key="product_name")
                product_batch = st.text_input("成品批次号", placeholder="例如: PC-100-20240106", key="product_batch")
                production_date = st.date_input("生产日期", datetime.now(), key="production_date")
                package_type = st.selectbox("包装形式", ["桶装", "袋装", "液袋", "其他"], key="package_type")
            
            with col_product2:
                product_solid = st.number_input("成品固含量 (%)", min_value=0.0, max_value=100.0, value=40.0, step=0.1, key="product_solid")
                product_ph = st.number_input("成品pH值", min_value=0.0, max_value=14.0, value=7.0, step=0.1, key="product_ph")
                product_density = st.number_input("成品密度 (g/cm³)", min_value=0.0, max_value=2.0, value=1.05, step=0.01, key="product_density")
                product_color = st.text_input("成品颜色", placeholder="例如: 淡黄色透明", key="product_color")
        
        # 备注和保存
        col_note, col_save = st.columns([3, 1])
        with col_note:
            notes = st.text_area(
                "实验备注", 
                height=100, 
                placeholder="记录实验现象、异常情况、改进建议等", 
                key="synthesis_notes",
                help="详细记录实验过程中的观察和备注"
            )
        
        with col_save:
            st.markdown("<br>" * 4, unsafe_allow_html=True)
            
            # 保存按钮
            save_button = st.button("💾 保存合成实验数据", type="primary", use_container_width=True, key="save_synthesis")
            
            if save_button:
                # 验证必填字段
                validation_errors = []
                
                if not selected_exp_id:
                    validation_errors.append("请选择实验项目")
                if not batch_no:
                    validation_errors.append("请输入批次号")
                if not operator:
                    validation_errors.append("请输入操作人")
                
                if validation_errors:
                    for error in validation_errors:
                        st.error(error)
                else:
                    # 构建合成实验数据
                    synthesis_data = {
                        "id": str(uuid.uuid4())[:8],
                        "experiment_id": selected_exp_id,
                        "record_date": record_date.strftime("%Y-%m-%d"),
                        "operator": operator,
                        "batch_no": batch_no,
                        "formula_id": formula_id,
                        
                        # 性能指标
                        "water_reduction": water_reduction,
                        "solid_content": solid_content,
                        "ph_value": ph_value,
                        "density": density,
                        "viscosity": viscosity,
                        "stability": stability,
                        "color": color,
                        
                        # 反应条件
                        "reaction_temp": reaction_temp,
                        "reaction_time": reaction_time,
                        "nitrogen_time": nitrogen_time,
                        
                        # 反应釜部分
                        "big_monomer": big_monomer,
                        "small_monomer1": small_monomer1,
                        "small_monomer2": small_monomer2,
                        "small_monomer3": small_monomer3,
                        "catalyst": catalyst,
                        "chain_transfer1": chain_transfer1,
                        "initiator1": initiator1,
                        "water1": water1,
                        "reactor_total": reactor_total,
                        "drop_start_temp": drop_start_temp,
                        "max_temp_limit": max_temp_limit,
                        
                        # A料部分
                        "monomer1_A": monomer1_A,
                        "monomer2_A": monomer2_A,
                        "monomer3_A": monomer3_A,
                        "monomer4_A": monomer4_A,
                        "water_A": water_A,
                        "drop_time_A": drop_time_A,
                        "drop_speed_A": drop_speed_A,
                        "total_A": total_A,
                        
                        # B料部分
                        "initiator2_B": initiator2_B,
                        "chain_transfer2_B": chain_transfer2_B,
                        "other1_B": other1_B,
                        "other2_B": other2_B,
                        "water_B": water_B,
                        "drop_time_B": drop_time_B,
                        "drop_speed_B": drop_speed_B,
                        "total_B": total_B,
                        
                        # 备注
                        "notes": notes,
                        
                        # 元数据
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "type": "synthesis",
                        "total_mass": reactor_total + total_A + total_B
                    }
                    
                    # 保存合成实验数据
                    save_success = False
                    try:
                        if data_manager.add_synthesis_record(synthesis_data):
                            save_success = True
                            st.success("✅ 合成实验数据保存成功！")
                            
                            # 如果填写了成品减水剂信息，也保存成品数据
                            if product_name and product_batch:
                                product_data = {
                                    "product_name": product_name,
                                    "batch_no": product_batch,
                                    "production_date": production_date.strftime("%Y-%m-%d"),
                                    "package_type": package_type,
                                    "solid_content": product_solid,
                                    "ph_value": product_ph,
                                    "density": product_density,
                                    "color": product_color,
                                    "parent_batch": batch_no,  # 关联母液批次
                                    "synthesis_record_id": synthesis_data["id"],
                                    "experiment_id": selected_exp_id,
                                    "operator": operator
                                }
                                
                                if data_manager.add_product(product_data):
                                    st.success("✅ 成品减水剂信息保存成功！")
                                else:
                                    st.warning("成品减水剂信息保存失败，但合成数据已保存")
                            
                            # 存储到session state用于确认显示
                            st.session_state.synthesis_form_state = {
                                "show_save_confirmation": True,
                                "saved_data": synthesis_data
                            }
                            
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ 保存失败，请重试")
                    except Exception as e:
                        st.error(f"保存过程中出错: {e}")
        
        # 显示保存确认信息
        if st.session_state.synthesis_form_state["show_save_confirmation"]:
            with st.expander("📋 保存的数据详情", expanded=False):
                saved_data = st.session_state.synthesis_form_state["saved_data"]
                if saved_data:
                    st.json(saved_data)
                    
                    # 添加清除按钮
                    if st.button("清除确认信息", key="clear_confirmation"):
                        st.session_state.synthesis_form_state = {
                            "show_save_confirmation": False,
                            "saved_data": None
                        }
                        st.rerun()
    
    # ==================== 2. 净浆实验数据记录 ====================
    with tab2:
        st.subheader("🥣 净浆实验数据记录")
        
        # 初始化表单状态
        if "paste_form_state" not in st.session_state:
            st.session_state.paste_form_state = {
                "show_save_confirmation": False,
                "saved_data": None
            }
        
        # 创建两列布局
        col1, col2 = st.columns([1, 1])
        
        with col1:
            # 实验选择
            exp_options = get_experiment_options("性能测试")
            if exp_options:
                selected_exp_key = st.selectbox(
                    "选择实验项目*",
                    options=list(exp_options.keys()),
                    key="paste_exp_select",
                    help="选择要进行净浆性能测试的实验项目"
                )
                selected_exp_id = exp_options.get(selected_exp_key)
            else:
                st.warning("暂无性能测试实验项目，请在实验管理中创建")
                selected_exp_id = None
            
            # 关联批次选择
            with st.container(border=True):
                st.markdown("### 🔗 关联批次")
                
                # 获取所有批次选项
                try:
                    batch_options = data_manager.get_all_batch_options()
                except Exception as e:
                    st.error(f"获取批次列表失败: {e}")
                    batch_options = []
                
                if batch_options:
                    batch_option_names = [f"{b['type']}: {b['batch_no']} ({b['date']})" for b in batch_options]
                    selected_batch_name = st.selectbox(
                        "选择关联批次*",
                        options=batch_option_names,
                        key="paste_batch_select",
                        help="选择要进行净浆测试的合成母液或成品批次"
                    )
                    
                    if selected_batch_name:
                        selected_index = batch_option_names.index(selected_batch_name)
                        selected_batch = batch_options[selected_index]
                        batch_type = selected_batch["type"]
                        batch_no = selected_batch["batch_no"]
                        batch_source = selected_batch["source"]
                        batch_source_id = selected_batch["source_id"]
                        
                        # 显示批次信息
                        st.info(f"""
                        **批次信息:**
                        - 类型: {batch_type}
                        - 批次号: {batch_no}
                        - 日期: {selected_batch.get('date', 'N/A')}
                        """)
                else:
                    st.warning("暂无可用批次，请先进行合成实验")
                    batch_type = None
                    batch_no = None
                    batch_source = None
                    batch_source_id = None
            
            # 基础信息
            with st.container(border=True):
                st.markdown("### 📋 基础信息")
                record_date = st.date_input(
                    "记录日期*", 
                    datetime.now(), 
                    key="paste_date",
                    help="净浆实验记录日期"
                )
                operator = st.text_input(
                    "操作人*", 
                    value="徐梓馨", 
                    key="paste_operator",
                    help="净浆实验操作人员"
                )
                sample_id = st.text_input(
                    "样品编号*", 
                    placeholder="例如: PASTE-001", 
                    key="paste_sample",
                    help="净浆样品唯一编号"
                )
        
        with col2:
            # 实验条件
            with st.container(border=True):
                st.markdown("### 🔬 实验条件")
                col_cond1, col_cond2 = st.columns(2)
                with col_cond1:
                    cement_type = st.selectbox(
                        "水泥类型*", 
                        ["P·O 42.5", "P·O 52.5", "P·II 42.5", "其他"], 
                        key="paste_cement",
                        help="使用的水泥类型"
                    )
                    water_cement_ratio = st.number_input(
                        "水灰比*", 
                        min_value=0.1, 
                        max_value=1.0, 
                        value=0.29, 
                        step=0.01, 
                        key="paste_wc",
                        help="水与水泥的质量比"
                    )
                
                with col_cond2:
                    admixture_dosage = st.number_input(
                        "减水剂掺量 (%)*", 
                        min_value=0.0, 
                        max_value=5.0, 
                        value=0.18, 
                        step=0.01, 
                        key="paste_dosage",
                        help="减水剂占胶凝材料的百分比"
                    )
                    temperature = st.number_input(
                        "环境温度 (°C)", 
                        value=20.0, 
                        step=0.5, 
                        key="paste_temp",
                        help="实验环境温度"
                    )
        
        # 流动度测试
        with st.expander("📏 流动度测试", expanded=True):
            st.markdown("### 流动度测试结果")
            
            col_flow1, col_flow2, col_flow3 = st.columns(3)
            
            with col_flow1:
                st.markdown("#### 初始流动度")
                initial_diameter = st.number_input(
                    "初始直径 (mm)", 
                    min_value=100, 
                    max_value=300, 
                    value=180, 
                    step=1, 
                    key="paste_initial_dia",
                    help="净浆初始流动度直径"
                )
                initial_time = st.number_input(
                    "流动时间 (s)", 
                    min_value=0, 
                    max_value=300, 
                    value=5, 
                    step=1, 
                    key="paste_initial_time",
                    help="达到初始流动度所需时间"
                )
            
            with col_flow2:
                st.markdown("#### 30分钟流动度")
                flow_30min_dia = st.number_input(
                    "30分钟直径 (mm)", 
                    min_value=100, 
                    max_value=300, 
                    value=175, 
                    step=1, 
                    key="paste_30min_dia",
                    help="30分钟后的流动度直径"
                )
                # 自动计算保持率
                if initial_diameter > 0:
                    flow_30min_ret = (flow_30min_dia / initial_diameter) * 100
                    st.metric("保持率 (%)", f"{flow_30min_ret:.1f}")
                else:
                    flow_30min_ret = 0
            
            with col_flow3:
                st.markdown("#### 60分钟流动度")
                flow_60min_dia = st.number_input(
                    "60分钟直径 (mm)", 
                    min_value=100, 
                    max_value=300, 
                    value=170, 
                    step=1, 
                    key="paste_60min_dia",
                    help="60分钟后的流动度直径"
                )
                # 自动计算保持率
                if initial_diameter > 0:
                    flow_60min_ret = (flow_60min_dia / initial_diameter) * 100
                    st.metric("保持率 (%)", f"{flow_60min_ret:.1f}")
                else:
                    flow_60min_ret = 0
            
            # 流动度保持率可视化
            if initial_diameter > 0:
                time_points = ["初始", "30分钟", "60分钟"]
                flow_values = [initial_diameter, flow_30min_dia, flow_60min_dia]
                
                # 创建简单的柱状图
                import plotly.graph_objects as go
                
                fig = go.Figure(data=[
                    go.Bar(
                        x=time_points, 
                        y=flow_values,
                        text=[f"{v}mm" for v in flow_values],
                        textposition='auto',
                        marker_color=['#1f77b4', '#ff7f0e', '#2ca02c']
                    )
                ])
                
                fig.update_layout(
                    title="净浆流动度变化",
                    xaxis_title="时间",
                    yaxis_title="流动度直径 (mm)",
                    height=300
                )
                
                st.plotly_chart(fig, use_container_width=True)
        
        # 凝结时间和其他性能
        with st.expander("⏰ 凝结时间与泌水性", expanded=False):
            col_set1, col_set2 = st.columns(2)
            with col_set1:
                st.markdown("#### 凝结时间")
                initial_setting = st.number_input(
                    "初凝时间 (min)", 
                    min_value=0, 
                    max_value=1000, 
                    value=240, 
                    step=5, 
                    key="paste_initial_set",
                    help="净浆初凝时间"
                )
                final_setting = st.number_input(
                    "终凝时间 (min)", 
                    min_value=0, 
                    max_value=1500, 
                    value=360, 
                    step=5, 
                    key="paste_final_set",
                    help="净浆终凝时间"
                )
            
            with col_set2:
                st.markdown("#### 泌水性")
                bleeding_rate = st.number_input(
                    "泌水率 (%)", 
                    min_value=0.0, 
                    max_value=10.0, 
                    value=0.5, 
                    step=0.1, 
                    key="paste_bleeding",
                    help="净浆泌水率"
                )
        
        # 备注和保存
        col_note, col_save = st.columns([3, 1])
        with col_note:
            notes = st.text_area(
                "实验备注", 
                height=100, 
                placeholder="记录浆体状态、泌水情况、异常现象等", 
                key="paste_notes",
                help="详细记录净浆实验过程中的观察和备注"
            )
        
        with col_save:
            st.markdown("<br>" * 4, unsafe_allow_html=True)
            
            # 保存按钮
            save_button = st.button("💾 保存净浆实验数据", type="primary", use_container_width=True, key="save_paste")
            
            if save_button:
                # 验证必填字段
                validation_errors = []
                
                if not selected_exp_id:
                    validation_errors.append("请选择实验项目")
                if not sample_id:
                    validation_errors.append("请输入样品编号")
                if not operator:
                    validation_errors.append("请输入操作人")
                if not cement_type:
                    validation_errors.append("请选择水泥类型")
                if not batch_no:
                    validation_errors.append("请选择关联批次")
                
                if validation_errors:
                    for error in validation_errors:
                        st.error(error)
                else:
                    # 构建数据记录
                    paste_data = {
                        "id": str(uuid.uuid4())[:8],
                        "experiment_id": selected_exp_id,
                        "record_date": record_date.strftime("%Y-%m-%d"),
                        "operator": operator,
                        "sample_id": sample_id,
                        
                        # 实验条件
                        "cement_type": cement_type,
                        "water_cement_ratio": water_cement_ratio,
                        "admixture_dosage": admixture_dosage,
                        "temperature": temperature,
                        
                        # 流动度数据
                        "initial_diameter": initial_diameter,
                        "initial_time": initial_time,
                        "flow_30min_dia": flow_30min_dia,
                        "flow_30min_ret": flow_30min_ret,
                        "flow_60min_dia": flow_60min_dia,
                        "flow_60min_ret": flow_60min_ret,
                        
                        # 凝结时间
                        "initial_setting": initial_setting,
                        "final_setting": final_setting,
                        "bleeding_rate": bleeding_rate,
                        
                        # 关联信息
                        "related_batch_type": batch_type,
                        "related_batch_no": batch_no,
                        "related_batch_source": batch_source,
                        "related_batch_id": batch_source_id,
                        
                        # 备注
                        "notes": notes,
                        
                        # 元数据
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "type": "paste"
                    }
                    
                    # 保存数据
                    try:
                        if save_performance_data("paste", paste_data):
                            st.success("✅ 净浆实验数据保存成功！")
                            
                            # 存储到session state用于确认显示
                            st.session_state.paste_form_state = {
                                "show_save_confirmation": True,
                                "saved_data": paste_data
                            }
                            
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ 保存失败，请重试")
                    except Exception as e:
                        st.error(f"保存过程中出错: {e}")
        
        # 显示保存确认信息
        if st.session_state.paste_form_state["show_save_confirmation"]:
            with st.expander("📋 保存的数据详情", expanded=False):
                saved_data = st.session_state.paste_form_state["saved_data"]
                if saved_data:
                    st.json(saved_data)
                    
                    # 添加清除按钮
                    if st.button("清除确认信息", key="clear_paste_confirmation"):
                        st.session_state.paste_form_state = {
                            "show_save_confirmation": False,
                            "saved_data": None
                        }
                        st.rerun()
    
    # ==================== 3. 砂浆实验数据记录 ====================
    with tab3:
        st.subheader("🏗️ 砂浆实验数据记录")
        
        # 初始化表单状态
        if "mortar_form_state" not in st.session_state:
            st.session_state.mortar_form_state = {
                "show_save_confirmation": False,
                "saved_data": None
            }
        
        # 创建两列布局
        col1, col2 = st.columns([1, 1])
        
        with col1:
            # 实验选择
            exp_options = get_experiment_options("性能测试")
            if exp_options:
                selected_exp_key = st.selectbox(
                    "选择实验项目*",
                    options=list(exp_options.keys()),
                    key="mortar_exp_select",
                    help="选择要进行砂浆性能测试的实验项目"
                )
                selected_exp_id = exp_options.get(selected_exp_key)
            else:
                st.warning("暂无性能测试实验项目，请在实验管理中创建")
                selected_exp_id = None
            
            # 关联批次选择
            with st.container(border=True):
                st.markdown("### 🔗 关联批次")
                
                # 获取所有批次选项
                try:
                    batch_options = data_manager.get_all_batch_options()
                except Exception as e:
                    st.error(f"获取批次列表失败: {e}")
                    batch_options = []
                
                if batch_options:
                    batch_option_names = [f"{b['type']}: {b['batch_no']} ({b['date']})" for b in batch_options]
                    selected_batch_name = st.selectbox(
                        "选择关联批次*",
                        options=batch_option_names,
                        key="mortar_batch_select",
                        help="选择要进行砂浆测试的合成母液或成品批次"
                    )
                    
                    if selected_batch_name:
                        selected_index = batch_option_names.index(selected_batch_name)
                        selected_batch = batch_options[selected_index]
                        batch_type = selected_batch["type"]
                        batch_no = selected_batch["batch_no"]
                        batch_source = selected_batch["source"]
                        batch_source_id = selected_batch["source_id"]
                        
                        # 显示批次信息
                        st.info(f"""
                        **批次信息:**
                        - 类型: {batch_type}
                        - 批次号: {batch_no}
                        - 日期: {selected_batch.get('date', 'N/A')}
                        """)
                else:
                    st.warning("暂无可用批次，请先进行合成实验")
                    batch_type = None
                    batch_no = None
                    batch_source = None
                    batch_source_id = None
            
            # 基础信息
            with st.container(border=True):
                st.markdown("### 📋 基础信息")
                record_date = st.date_input(
                    "记录日期*", 
                    datetime.now(), 
                    key="mortar_date",
                    help="砂浆实验记录日期"
                )
                operator = st.text_input(
                    "操作人*", 
                    value="徐梓馨", 
                    key="mortar_operator",
                    help="砂浆实验操作人员"
                )
                sample_id = st.text_input(
                    "样品编号*", 
                    placeholder="例如: MORTAR-001", 
                    key="mortar_sample",
                    help="砂浆样品唯一编号"
                )
        
        with col2:
            # 配合比设计
            with st.container(border=True):
                st.markdown("### 🧮 配合比设计")
                col_mix1, col_mix2 = st.columns(2)
                with col_mix1:
                    cement_dosage = st.number_input(
                        "水泥用量 (g)*", 
                        min_value=0, 
                        max_value=2000, 
                        value=450, 
                        step=5, 
                        key="mortar_cement",
                        help="砂浆中水泥用量"
                    )
                    sand_dosage = st.number_input(
                        "砂用量 (g)*", 
                        min_value=0, 
                        max_value=5000, 
                        value=1350, 
                        step=10, 
                        key="mortar_sand",
                        help="砂浆中砂用量"
                    )
                
                with col_mix2:
                    water_dosage = st.number_input(
                        "水用量 (g)*", 
                        min_value=0, 
                        max_value=1000, 
                        value=225, 
                        step=5, 
                        key="mortar_water",
                        help="砂浆中水用量"
                    )
                    admixture_dosage = st.number_input(
                        "减水剂掺量 (%)*", 
                        min_value=0.0, 
                        max_value=5.0, 
                        value=0.18, 
                        step=0.01, 
                        key="mortar_dosage",
                        help="减水剂占胶凝材料的百分比"
                    )
                
                # 计算总质量和配合比
                total_mass = cement_dosage + sand_dosage + water_dosage
                cement_ratio = cement_dosage / total_mass * 100 if total_mass > 0 else 0
                sand_ratio = sand_dosage / total_mass * 100 if total_mass > 0 else 0
                water_ratio = water_dosage / total_mass * 100 if total_mass > 0 else 0
                
                st.info(f"""
                **配合比统计:**
                - 总质量: {total_mass:.1f} g
                - 水泥占比: {cement_ratio:.1f}%
                - 砂占比: {sand_ratio:.1f}%
                - 水占比: {water_ratio:.1f}%
                """)
        
        # 性能测试
        with st.expander("📊 性能测试", expanded=True):
            col_perf1, col_perf2 = st.columns(2)
            
            with col_perf1:
                st.markdown("#### 流动度")
                mortar_flow = st.number_input(
                    "砂浆流动度 (mm)", 
                    min_value=100, 
                    max_value=300, 
                    value=180, 
                    step=1, 
                    key="mortar_flow",
                    help="砂浆流动度"
                )
                flow_retention = st.number_input(
                    "流动度保持率 (%)", 
                    min_value=0.0, 
                    max_value=100.0, 
                    value=95.0, 
                    step=0.1, 
                    key="mortar_flow_ret",
                    help="砂浆流动度保持率"
                )
                
                st.markdown("#### 保水性")
                water_retention = st.number_input(
                    "保水性 (%)", 
                    min_value=0.0, 
                    max_value=100.0, 
                    value=85.0, 
                    step=0.1, 
                    key="mortar_water_ret",
                    help="砂浆保水性"
                )
            
            with col_perf2:
                st.markdown("#### 抗压强度 (MPa)")
                strength_1d = st.number_input(
                    "1天强度", 
                    min_value=0.0, 
                    max_value=100.0, 
                    value=15.0, 
                    step=0.1, 
                    key="mortar_strength_1d",
                    help="1天抗压强度"
                )
                strength_3d = st.number_input(
                    "3天强度", 
                    min_value=0.0, 
                    max_value=100.0, 
                    value=30.0, 
                    step=0.1, 
                    key="mortar_strength_3d",
                    help="3天抗压强度"
                )
                strength_7d = st.number_input(
                    "7天强度", 
                    min_value=0.0, 
                    max_value=100.0, 
                    value=45.0, 
                    step=0.1, 
                    key="mortar_strength_7d",
                    help="7天抗压强度"
                )
                strength_28d = st.number_input(
                    "28天强度", 
                    min_value=0.0, 
                    max_value=100.0, 
                    value=60.0, 
                    step=0.1, 
                    key="mortar_strength_28d",
                    help="28天抗压强度"
                )
        
        # 备注和保存
        col_note, col_save = st.columns([3, 1])
        with col_note:
            notes = st.text_area(
                "实验备注", 
                height=100, 
                placeholder="记录砂浆状态、成型情况、养护条件等", 
                key="mortar_notes",
                help="详细记录砂浆实验过程中的观察和备注"
            )
        
        with col_save:
            st.markdown("<br>" * 4, unsafe_allow_html=True)
            
            # 保存按钮
            save_button = st.button("💾 保存砂浆实验数据", type="primary", use_container_width=True, key="save_mortar")
            
            if save_button:
                # 验证必填字段
                validation_errors = []
                
                if not selected_exp_id:
                    validation_errors.append("请选择实验项目")
                if not sample_id:
                    validation_errors.append("请输入样品编号")
                if not operator:
                    validation_errors.append("请输入操作人")
                if not batch_no:
                    validation_errors.append("请选择关联批次")
                
                if validation_errors:
                    for error in validation_errors:
                        st.error(error)
                else:
                    # 构建数据记录
                    mortar_data = {
                        "id": str(uuid.uuid4())[:8],
                        "experiment_id": selected_exp_id,
                        "record_date": record_date.strftime("%Y-%m-%d"),
                        "operator": operator,
                        "sample_id": sample_id,
                        
                        # 配合比
                        "cement_dosage": cement_dosage,
                        "sand_dosage": sand_dosage,
                        "water_dosage": water_dosage,
                        "admixture_dosage": admixture_dosage,
                        "total_mass": total_mass,
                        
                        # 性能测试
                        "mortar_flow": mortar_flow,
                        "flow_retention": flow_retention,
                        "water_retention": water_retention,
                        "strength_1d": strength_1d,
                        "strength_3d": strength_3d,
                        "strength_7d": strength_7d,
                        "strength_28d": strength_28d,
                        
                        # 关联信息
                        "related_batch_type": batch_type,
                        "related_batch_no": batch_no,
                        "related_batch_source": batch_source,
                        "related_batch_id": batch_source_id,
                        
                        # 备注
                        "notes": notes,
                        
                        # 元数据
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "type": "mortar"
                    }
                    
                    # 保存数据
                    try:
                        if save_performance_data("mortar", mortar_data):
                            st.success("✅ 砂浆实验数据保存成功！")
                            
                            # 存储到session state用于确认显示
                            st.session_state.mortar_form_state = {
                                "show_save_confirmation": True,
                                "saved_data": mortar_data
                            }
                            
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ 保存失败，请重试")
                    except Exception as e:
                        st.error(f"保存过程中出错: {e}")
        
        # 显示保存确认信息
        if st.session_state.mortar_form_state["show_save_confirmation"]:
            with st.expander("📋 保存的数据详情", expanded=False):
                saved_data = st.session_state.mortar_form_state["saved_data"]
                if saved_data:
                    st.json(saved_data)
                    
                    # 添加清除按钮
                    if st.button("清除确认信息", key="clear_mortar_confirmation"):
                        st.session_state.mortar_form_state = {
                            "show_save_confirmation": False,
                            "saved_data": None
                        }
                        st.rerun()
    
    # ==================== 4. 混凝土实验数据记录 ====================
    with tab4:
        st.subheader("🏢 混凝土实验数据记录")
        
        # 初始化表单状态
        if "concrete_form_state" not in st.session_state:
            st.session_state.concrete_form_state = {
                "show_save_confirmation": False,
                "saved_data": None
            }
        
        # 创建两列布局
        col1, col2 = st.columns([1, 1])
        
        with col1:
            # 实验选择
            exp_options = get_experiment_options("性能测试")
            if exp_options:
                selected_exp_key = st.selectbox(
                    "选择实验项目*",
                    options=list(exp_options.keys()),
                    key="concrete_exp_select",
                    help="选择要进行混凝土性能测试的实验项目"
                )
                selected_exp_id = exp_options.get(selected_exp_key)
            else:
                st.warning("暂无性能测试实验项目，请在实验管理中创建")
                selected_exp_id = None
            
            # 关联批次选择
            with st.container(border=True):
                st.markdown("### 🔗 关联批次")
                
                # 获取所有批次选项
                try:
                    batch_options = data_manager.get_all_batch_options()
                except Exception as e:
                    st.error(f"获取批次列表失败: {e}")
                    batch_options = []
                
                if batch_options:
                    batch_option_names = [f"{b['type']}: {b['batch_no']} ({b['date']})" for b in batch_options]
                    selected_batch_name = st.selectbox(
                        "选择关联批次*",
                        options=batch_option_names,
                        key="concrete_batch_select",
                        help="选择要进行混凝土测试的合成母液或成品批次"
                    )
                    
                    if selected_batch_name:
                        selected_index = batch_option_names.index(selected_batch_name)
                        selected_batch = batch_options[selected_index]
                        batch_type = selected_batch["type"]
                        batch_no = selected_batch["batch_no"]
                        batch_source = selected_batch["source"]
                        batch_source_id = selected_batch["source_id"]
                        
                        # 显示批次信息
                        st.info(f"""
                        **批次信息:**
                        - 类型: {batch_type}
                        - 批次号: {batch_no}
                        - 日期: {selected_batch.get('date', 'N/A')}
                        """)
                else:
                    st.warning("暂无可用批次，请先进行合成实验")
                    batch_type = None
                    batch_no = None
                    batch_source = None
                    batch_source_id = None
            
            # 基础信息
            with st.container(border=True):
                st.markdown("### 📋 基础信息")
                record_date = st.date_input(
                    "记录日期*", 
                    datetime.now(), 
                    key="concrete_date",
                    help="混凝土实验记录日期"
                )
                operator = st.text_input(
                    "操作人*", 
                    value="徐梓馨", 
                    key="concrete_operator",
                    help="混凝土实验操作人员"
                )
                mix_id = st.text_input(
                    "配合比编号*", 
                    placeholder="例如: MIX-C30-001", 
                    key="concrete_mix",
                    help="混凝土配合比编号"
                )
        
        with col2:
            # 配合比设计
            with st.container(border=True):
                st.markdown("### 🧮 配合比设计 (kg/m³)")
                col_mix1, col_mix2 = st.columns(2)
                with col_mix1:
                    cement = st.number_input(
                        "水泥*", 
                        min_value=0, 
                        max_value=1000, 
                        value=320, 
                        step=5, 
                        key="concrete_cement",
                        help="每方混凝土水泥用量"
                    )
                    sand = st.number_input(
                        "砂*", 
                        min_value=0, 
                        max_value=2000, 
                        value=750, 
                        step=10, 
                        key="concrete_sand",
                        help="每方混凝土砂用量"
                    )
                    stone = st.number_input(
                        "石子*", 
                        min_value=0, 
                        max_value=2500, 
                        value=1050, 
                        step=10, 
                        key="concrete_stone",
                        help="每方混凝土石子用量"
                    )
                
                with col_mix2:
                    water = st.number_input(
                        "水*", 
                        min_value=0, 
                        max_value=300, 
                        value=160, 
                        step=5, 
                        key="concrete_water",
                        help="每方混凝土水用量"
                    )
                    admixture = st.number_input(
                        "减水剂*", 
                        min_value=0.0, 
                        max_value=10.0, 
                        value=3.2, 
                        step=0.1, 
                        key="concrete_admixture",
                        help="每方混凝土减水剂用量"
                    )
                    mineral_addition = st.number_input(
                        "矿物掺合料", 
                        min_value=0, 
                        max_value=300, 
                        value=80, 
                        step=5, 
                        key="concrete_mineral",
                        help="每方混凝土矿物掺合料用量"
                    )
                
                # 计算配合比参数
                total_materials = cement + sand + stone + water + admixture + mineral_addition
                water_cement_ratio = water / (cement + mineral_addition) if (cement + mineral_addition) > 0 else 0
                sand_ratio = sand / (sand + stone) * 100 if (sand + stone) > 0 else 0
                
                st.info(f"""
                **配合比参数:**
                - 总材料量: {total_materials:.1f} kg/m³
                - 水胶比: {water_cement_ratio:.2f}
                - 砂率: {sand_ratio:.1f}%
                """)
        
        # 新拌混凝土性能
        with st.expander("🥄 新拌混凝土性能", expanded=True):
            col_fresh1, col_fresh2, col_fresh3 = st.columns(3)
            
            with col_fresh1:
                st.markdown("#### 工作性")
                slump = st.number_input(
                    "坍落度 (mm)", 
                    min_value=0, 
                    max_value=300, 
                    value=180, 
                    step=5, 
                    key="concrete_slump",
                    help="混凝土坍落度"
                )
                slump_flow = st.number_input(
                    "扩展度 (mm)", 
                    min_value=300, 
                    max_value=800, 
                    value=500, 
                    step=10, 
                    key="concrete_slump_flow",
                    help="混凝土扩展度"
                )
            
            with col_fresh2:
                st.markdown("#### 含气量与密度")
                air_content = st.number_input(
                    "含气量 (%)", 
                    min_value=0.0, 
                    max_value=10.0, 
                    value=2.5, 
                    step=0.1, 
                    key="concrete_air",
                    help="混凝土含气量"
                )
                density = st.number_input(
                    "表观密度 (kg/m³)", 
                    min_value=2000, 
                    max_value=3000, 
                    value=2350, 
                    step=10, 
                    key="concrete_density",
                    help="混凝土表观密度"
                )
            
            with col_fresh3:
                st.markdown("#### 凝结时间")
                initial_setting = st.number_input(
                    "初凝 (h)", 
                    min_value=0.0, 
                    max_value=24.0, 
                    value=4.5, 
                    step=0.5, 
                    key="concrete_initial_set",
                    help="混凝土初凝时间"
                )
                final_setting = st.number_input(
                    "终凝 (h)", 
                    min_value=0.0, 
                    max_value=36.0, 
                    value=7.5, 
                    step=0.5, 
                    key="concrete_final_set",
                    help="混凝土终凝时间"
                )
        
        # 硬化混凝土性能
        with st.expander("💪 硬化混凝土性能", expanded=True):
            col_hard1, col_hard2 = st.columns(2)
            
            with col_hard1:
                st.markdown("#### 抗压强度 (MPa)")
                strength_3d = st.number_input(
                    "3天强度", 
                    min_value=0.0, 
                    max_value=100.0, 
                    value=20.0, 
                    step=0.1, 
                    key="concrete_strength_3d",
                    help="3天抗压强度"
                )
                strength_7d = st.number_input(
                    "7天强度", 
                    min_value=0.0, 
                    max_value=100.0, 
                    value=30.0, 
                    step=0.1, 
                    key="concrete_strength_7d",
                    help="7天抗压强度"
                )
                strength_28d = st.number_input(
                    "28天强度", 
                    min_value=0.0, 
                    max_value=100.0, 
                    value=45.0, 
                    step=0.1, 
                    key="concrete_strength_28d",
                    help="28天抗压强度"
                )
            
            with col_hard2:
                st.markdown("#### 其他性能")
                flexural_strength = st.number_input(
                    "抗折强度 (MPa)", 
                    min_value=0.0, 
                    max_value=20.0, 
                    value=5.5, 
                    step=0.1, 
                    key="concrete_flexural",
                    help="混凝土抗折强度"
                )
                shrinkage = st.number_input(
                    "收缩率 (×10⁻⁶)", 
                    min_value=0, 
                    max_value=1000, 
                    value=350, 
                    step=10, 
                    key="concrete_shrinkage",
                    help="混凝土收缩率"
                )
                carbonation = st.number_input(
                    "碳化深度 (mm)", 
                    min_value=0.0, 
                    max_value=50.0, 
                    value=2.5, 
                    step=0.1, 
                    key="concrete_carbonation",
                    help="混凝土碳化深度"
                )
        
        # 备注和保存
        col_note, col_save = st.columns([3, 1])
        with col_note:
            notes = st.text_area(
                "实验备注", 
                height=100, 
                placeholder="记录混凝土状态、施工性能、养护条件、异常情况等", 
                key="concrete_notes",
                help="详细记录混凝土实验过程中的观察和备注"
            )
        
        with col_save:
            st.markdown("<br>" * 4, unsafe_allow_html=True)
            
            # 保存按钮
            save_button = st.button("💾 保存混凝土实验数据", type="primary", use_container_width=True, key="save_concrete")
            
            if save_button:
                # 验证必填字段
                validation_errors = []
                
                if not selected_exp_id:
                    validation_errors.append("请选择实验项目")
                if not mix_id:
                    validation_errors.append("请输入配合比编号")
                if not operator:
                    validation_errors.append("请输入操作人")
                if not batch_no:
                    validation_errors.append("请选择关联批次")
                
                if validation_errors:
                    for error in validation_errors:
                        st.error(error)
                else:
                    # 构建数据记录
                    concrete_data = {
                        "id": str(uuid.uuid4())[:8],
                        "experiment_id": selected_exp_id,
                        "record_date": record_date.strftime("%Y-%m-%d"),
                        "operator": operator,
                        "mix_id": mix_id,
                        
                        # 配合比设计
                        "cement": cement,
                        "sand": sand,
                        "stone": stone,
                        "water": water,
                        "admixture": admixture,
                        "mineral_addition": mineral_addition,
                        "total_materials": total_materials,
                        "water_cement_ratio": water_cement_ratio,
                        "sand_ratio": sand_ratio,
                        
                        # 新拌混凝土性能
                        "slump": slump,
                        "slump_flow": slump_flow,
                        "air_content": air_content,
                        "density": density,
                        "initial_setting": initial_setting,
                        "final_setting": final_setting,
                        
                        # 硬化混凝土性能
                        "strength_3d": strength_3d,
                        "strength_7d": strength_7d,
                        "strength_28d": strength_28d,
                        "flexural_strength": flexural_strength,
                        "shrinkage": shrinkage,
                        "carbonation": carbonation,
                        
                        # 关联信息
                        "related_batch_type": batch_type,
                        "related_batch_no": batch_no,
                        "related_batch_source": batch_source,
                        "related_batch_id": batch_source_id,
                        
                        # 备注
                        "notes": notes,
                        
                        # 元数据
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "type": "concrete"
                    }
                    
                    # 保存数据
                    try:
                        if save_performance_data("concrete", concrete_data):
                            st.success("✅ 混凝土实验数据保存成功！")
                            
                            # 存储到session state用于确认显示
                            st.session_state.concrete_form_state = {
                                "show_save_confirmation": True,
                                "saved_data": concrete_data
                            }
                            
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ 保存失败，请重试")
                    except Exception as e:
                        st.error(f"保存过程中出错: {e}")
        
        # 显示保存确认信息
        if st.session_state.concrete_form_state["show_save_confirmation"]:
            with st.expander("📋 保存的数据详情", expanded=False):
                saved_data = st.session_state.concrete_form_state["saved_data"]
                if saved_data:
                    st.json(saved_data)
                    
                    # 添加清除按钮
                    if st.button("清除确认信息", key="clear_concrete_confirmation"):
                        st.session_state.concrete_form_state = {
                            "show_save_confirmation": False,
                            "saved_data": None
                        }
                        st.rerun()
    
    # ==================== 数据查看模块 ====================
    st.divider()
    st.subheader("📊 数据查看")
    
    # 获取所有性能数据
    try:
        performance_data = data_manager.get_performance_data()
    except Exception as e:
        st.error(f"加载性能数据失败: {e}")
        performance_data = {}
    
    # 使用选项卡查看不同类型的数据
    view_tab1, view_tab2, view_tab3, view_tab4 = st.tabs(["合成数据", "净浆数据", "砂浆数据", "混凝土数据"])
    
    with view_tab1:
        synthesis_data = performance_data.get("synthesis", [])
        if synthesis_data:
            # 转换为DataFrame
            df = pd.DataFrame(synthesis_data)
            
            # 选择要显示的列
            display_columns = ["record_date", "batch_no", "water_reduction", "solid_content", "ph_value", "operator"]
            available_columns = [col for col in display_columns if col in df.columns]
            
            if available_columns:
                st.dataframe(df[available_columns], use_container_width=True)
                
                # 统计信息
                col_stat1, col_stat2, col_stat3 = st.columns(3)
                with col_stat1:
                    st.metric("记录总数", len(df))
                with col_stat2:
                    avg_reduction = df["water_reduction"].mean() if "water_reduction" in df.columns else 0
                    st.metric("平均减水率", f"{avg_reduction:.1f}%")
                with col_stat3:
                    avg_solid = df["solid_content"].mean() if "solid_content" in df.columns else 0
                    st.metric("平均固含量", f"{avg_solid:.1f}%")
            else:
                st.dataframe(df, use_container_width=True)
        else:
            st.info("暂无合成实验数据")
    
    with view_tab2:
        paste_data = performance_data.get("paste", [])
        if paste_data:
            # 转换为DataFrame
            df = pd.DataFrame(paste_data)
            
            # 选择要显示的列
            display_columns = ["record_date", "sample_id", "initial_diameter", "flow_30min_dia", "flow_60min_dia", "operator"]
            available_columns = [col for col in display_columns if col in df.columns]
            
            if available_columns:
                st.dataframe(df[available_columns], use_container_width=True)
                
                # 统计信息
                col_stat1, col_stat2, col_stat3 = st.columns(3)
                with col_stat1:
                    st.metric("记录总数", len(df))
                with col_stat2:
                    avg_initial = df["initial_diameter"].mean() if "initial_diameter" in df.columns else 0
                    st.metric("平均初始直径", f"{avg_initial:.0f}mm")
                with col_stat3:
                    avg_30min = df["flow_30min_dia"].mean() if "flow_30min_dia" in df.columns else 0
                    st.metric("平均30分钟直径", f"{avg_30min:.0f}mm")
            else:
                st.dataframe(df, use_container_width=True)
        else:
            st.info("暂无净浆实验数据")
    
    with view_tab3:
        mortar_data = performance_data.get("mortar", [])
        if mortar_data:
            # 转换为DataFrame
            df = pd.DataFrame(mortar_data)
            
            # 选择要显示的列
            display_columns = ["record_date", "sample_id", "mortar_flow", "strength_3d", "strength_28d", "operator"]
            available_columns = [col for col in display_columns if col in df.columns]
            
            if available_columns:
                st.dataframe(df[available_columns], use_container_width=True)
                
                # 统计信息
                col_stat1, col_stat2, col_stat3 = st.columns(3)
                with col_stat1:
                    st.metric("记录总数", len(df))
                with col_stat2:
                    avg_flow = df["mortar_flow"].mean() if "mortar_flow" in df.columns else 0
                    st.metric("平均流动度", f"{avg_flow:.0f}mm")
                with col_stat3:
                    avg_28d = df["strength_28d"].mean() if "strength_28d" in df.columns else 0
                    st.metric("平均28天强度", f"{avg_28d:.1f}MPa")
            else:
                st.dataframe(df, use_container_width=True)
        else:
            st.info("暂无砂浆实验数据")
    
    with view_tab4:
        concrete_data = performance_data.get("concrete", [])
        if concrete_data:
            # 转换为DataFrame
            df = pd.DataFrame(concrete_data)
            
            # 选择要显示的列
            display_columns = ["record_date", "mix_id", "slump", "slump_flow", "strength_28d", "operator"]
            available_columns = [col for col in display_columns if col in df.columns]
            
            if available_columns:
                st.dataframe(df[available_columns], use_container_width=True)
                
                # 统计信息
                col_stat1, col_stat2, col_stat3 = st.columns(3)
                with col_stat1:
                    st.metric("记录总数", len(df))
                with col_stat2:
                    avg_slump = df["slump"].mean() if "slump" in df.columns else 0
                    st.metric("平均坍落度", f"{avg_slump:.0f}mm")
                with col_stat3:
                    avg_28d = df["strength_28d"].mean() if "strength_28d" in df.columns else 0
                    st.metric("平均28天强度", f"{avg_28d:.1f}MPa")
            else:
                st.dataframe(df, use_container_width=True)
        else:
            st.info("暂无混凝土实验数据")

# -------------------- 数据分析页面 --------------------
def render_data_analysis():
    """渲染数据分析页面"""
    st.header("📈 数据分析")
    
    # 获取性能数据
    data = data_manager.load_data()
    performance_data = data.get("performance_data", [])
    
    if not performance_data:
        st.info("暂无性能数据可用于分析，请在'数据记录'页面添加数据。")
        return
    
    # 转换为DataFrame
    perf_df = pd.DataFrame(performance_data)
    
    st.subheader("性能数据概览")
    st.dataframe(perf_df, use_container_width=True)

# -------------------- 报告生成页面 --------------------
def render_report_generation():
    """渲染报告生成页面"""
    st.header("📄 报告生成")
    
    st.info("报告生成模块")
    projects = data_manager.get_all_projects()
    
    if projects:
        selected_project = st.selectbox(
            "选择项目",
            options=[p["name"] for p in projects]
        )
        
        report_type = st.selectbox(
            "报告类型",
            ["实验报告", "进度报告", "总结报告"]
        )
        
        if st.button("生成报告", type="primary"):
            st.success(f"已生成 {selected_project} 的 {report_type}")
    else:
        st.info("暂无项目数据，无法生成报告")

# -------------------- 主程序入口 --------------------
def main():
    """主函数"""
    # 页面标题
    st.title("🧪 聚羧酸减水剂研发管理系统")
    st.markdown("---")
    
    # 侧边栏导航
    st.sidebar.title("导航菜单")
    menu_options = ["📊 项目概览", "🧪 实验管理", "📝 数据记录", "📈 数据分析", "📄 报告生成"]
    selected_page = st.sidebar.radio("选择功能", menu_options)
    
    # 侧边栏系统信息
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 系统信息")
    st.sidebar.info(f"当前时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    # 数据统计
    projects = data_manager.get_all_projects()
    experiments = data_manager.get_all_experiments()
    st.sidebar.metric("项目总数", len(projects))
    st.sidebar.metric("实验总数", len(experiments))
    
    # 数据文件状态
    data_file = Path(__file__).parent.parent / "data.json"
    if data_file.exists():
        file_size = data_file.stat().st_size / 1024  # KB
        st.sidebar.metric("数据文件大小", f"{file_size:.1f} KB")
    
    # 根据选择渲染页面
    if selected_page == "📊 项目概览":
        render_dashboard()
    elif selected_page == "🧪 实验管理":
        render_experiment_management()
    elif selected_page == "📝 数据记录":
        render_data_recording()
    elif selected_page == "📈 数据分析":
        render_data_analysis()
    elif selected_page == "📄 报告生成":
        render_report_generation()
    
    # 页脚
    st.markdown("---")
    st.caption("聚羧酸减水剂研发管理系统 v2.2 | 实验查找功能 | 最后更新: 2024年1月")

# -------------------- 程序执行 --------------------
if __name__ == "__main__":
    main()
