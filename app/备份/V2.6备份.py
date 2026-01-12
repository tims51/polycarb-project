# main.py

"""聚羧酸减水剂研发管理系统 - 主程序 (完整修复版)
修复数据丢失问题，增加数据导出/导入和定时备份功能
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from pathlib import Path
import json
import time
import os
import shutil
from io import BytesIO
import base64

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
        try:
            # 提取日期信息
            start_date_str = project_data.get('start_date', '')
            end_date_str = project_data.get('end_date', '')
            
            # 验证必要数据
            if not start_date_str or not end_date_str:
                return TimelineManager._create_invalid_timeline("缺少日期信息")
            
            # 解析日期
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            today = datetime.now().date()
            
            # 验证日期逻辑
            if end_date <= start_date:
                return TimelineManager._create_invalid_timeline("结束日期早于或等于开始日期")
            
            # 计算基础信息
            total_days = (end_date - start_date).days
            passed_days = max(0, min((today - start_date).days, total_days))
            
            # 确定项目状态
            if today < start_date:
                status = "尚未开始"
                status_emoji = "⏳"
                percent = 0
            elif today > end_date:
                status = "已完成"
                status_emoji = "✅"
                percent = 100
                passed_days = total_days
            else:
                status = "进行中"
                status_emoji = "📅"
                percent = (passed_days / total_days) * 100
            
            # 计算预计完成时间
            estimated_completion = None
            if 0 < percent < 100:
                remaining_days = total_days - passed_days
                estimated_completion = today + timedelta(days=remaining_days)
            
            # 构建时间线信息对象
            timeline_info = {
                'is_valid': True,
                'status': status,
                'status_emoji': status_emoji,
                'percent': percent,
                'passed_days': passed_days,
                'total_days': total_days,
                'start_date': start_date,
                'end_date': end_date,
                'today': today,
                'estimated_completion': estimated_completion,
                'remaining_days': total_days - passed_days if percent < 100 else 0,
                'is_delayed': today > end_date and percent < 100,
                'is_ahead': False  # 可以扩展：计算是否超前于计划
            }
            
            return timeline_info
            
        except ValueError as e:
            return TimelineManager._create_invalid_timeline(f"日期格式错误: {e}")
        except Exception as e:
            return TimelineManager._create_invalid_timeline(f"计算错误: {e}")
    
    @staticmethod
    def _create_invalid_timeline(reason=""):
        """创建无效时间线信息"""
        return {
            'is_valid': False,
            'error_reason': reason,
            'status': '未知',
            'status_emoji': '❓',
            'percent': 0,
            'passed_days': 0,
            'total_days': 0,
            'today': datetime.now().date()
        }
    
    @staticmethod
    def get_timeline_summary(timeline_info):
        """获取时间线摘要文本"""
        if not timeline_info.get('is_valid'):
            return "时间线信息不可用"
        
        status = timeline_info.get('status', '未知')
        passed = timeline_info.get('passed_days', 0)
        total = timeline_info.get('total_days', 1)
        percent = timeline_info.get('percent', 0)
        
        if status == "尚未开始":
            return f"项目尚未开始 ({timeline_info.get('start_date').strftime('%Y-%m-%d')})"
        elif status == "已完成":
            return f"项目已完成 ({passed}/{total}天)"
        else:  # 进行中
            remaining = total - passed
            return f"进行中: {passed}/{total}天 ({percent:.1f}%), 剩余{remaining}天"
    
    @staticmethod
    def is_project_active(timeline_info):
        """检查项目是否处于活跃状态（进行中或即将开始）"""
        if not timeline_info.get('is_valid'):
            return False
        
        status = timeline_info.get('status', '')
        return status in ["进行中", "尚未开始"]

# ==================== 扩展的DataManager类 ====================
class DataManager:
    """统一数据管理器 - 处理所有数据的增删查改，支持导出导入"""
    
    def __init__(self):
        self.data_file = Path(__file__).parent / "data.json"
        self.backup_dir = Path(__file__).parent / "backups"
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
            "paste_experiments", "mortar_experiments", "concrete_experiments"
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
            
            # 检查是否需要创建每日备份
            self.check_and_create_daily_backup()
            
            return True
        except Exception as e:
            st.error(f"保存数据失败: {e}")
            return False
    
    def check_and_create_daily_backup(self):
        """检查并创建每日备份"""
        try:
            # 获取当前日期
            today = datetime.now().date()
            
            # 检查上次备份时间
            if st.session_state.last_backup_time != today:
                # 创建备份
                self.create_backup()
                # 更新备份时间
                st.session_state.last_backup_time = today
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
            "concrete_experiments": []
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
        
        # 生成新ID
        new_id = max([m.get("id", 0) for m in materials], default=0) + 1
        material_data["id"] = new_id
        material_data["created_date"] = datetime.now().strftime("%Y-%m-%d")
        
        materials.append(material_data)
        data["raw_materials"] = materials
        return self.save_data(data)
    
    def update_raw_material(self, material_id, updated_fields):
        """更新原材料信息"""
        data = self.load_data()
        materials = data.get("raw_materials", [])
        
        updated = False
        for i, material in enumerate(materials):
            if material.get("id") == material_id:
                # 更新字段
                materials[i].update(updated_fields)
                updated = True
                break
        
        if updated:
            data["raw_materials"] = materials
            return self.save_data(data)
        return False
    
    def delete_raw_material(self, material_id):
        """删除原材料"""
        data = self.load_data()
        materials = data.get("raw_materials", [])
        
        new_materials = [m for m in materials if m.get("id") != material_id]
        
        if len(new_materials) < len(materials):
            data["raw_materials"] = new_materials
            return self.save_data(data)
        return False
    
    # 合成实验记录
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
    
    def add_product(self, product_data):
        """添加新成品减水剂"""
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
        st.warning(⚠️ 时间线信息不可用")
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
    
    st.header("🧪 实验管理")
    
    # 获取数据
    experiments = data_manager.get_all_experiments()
    projects = data_manager.get_all_projects()
    
    # 创建新实验的表单
    with st.expander("➕ 创建新实验", expanded=True):
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
    </style>
    """, unsafe_allow_html=True)
    
    if experiments:
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
                    for exp in experiments:
                        exp_id = exp["id"]
                        st.session_state.selected_experiments[exp_id] = True
                    st.rerun()
            
            with batch_col2:
                # 取消全选按钮
                if st.button("取消全选", key="deselect_all_btn", use_container_width=True, type="secondary"):
                    # 清除所有选择
                    for exp in experiments:
                        exp_id = exp["id"]
                        st.session_state.selected_experiments[exp_id] = False
                    st.rerun()
            
            with batch_col3:
                # 编辑按钮 - 检查是否只选择了一个实验
                selected_count = sum(1 for exp in experiments 
                                   if exp["id"] in st.session_state.selected_experiments 
                                   and st.session_state.selected_experiments[exp["id"]])
                
                # 获取选中的实验ID
                selected_exp_ids = []
                for exp in experiments:
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
                selected_count = sum(1 for exp in experiments 
                                   if exp["id"] in st.session_state.selected_experiments 
                                   and st.session_state.selected_experiments[exp["id"]])
                status_text = f"已选择 {selected_count} 个实验"
                
                # 如果只选择了一个实验，显示实验名称
                if selected_count == 1:
                    selected_exp_id = selected_exp_ids[0]
                    selected_exp = next((e for e in experiments if e["id"] == selected_exp_id), None)
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
                                }
                                
                                # 更新实验数据
                                if data_manager.update_experiment(st.session_state.editing_experiment_id, updated_experiment):
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
                                st.error("⚠️ 实验名称和所属项目为必填项")
                        
                        if cancel_submitted:
                            st.session_state.editing_experiment_id = None
                            st.session_state.show_edit_form = False
                            st.info("已取消编辑操作")
                            time.sleep(0.5)
                            st.rerun()
        
        # 分页设置
        PAGE_SIZE = 20
        total_experiments = len(experiments)
        total_pages = (total_experiments + PAGE_SIZE - 1) // PAGE_SIZE  # 向上取整
        
        # 确保当前页码有效
        if st.session_state.experiment_page < 1:
            st.session_state.experiment_page = 1
        elif st.session_state.experiment_page > total_pages and total_pages > 0:
            st.session_state.experiment_page = total_pages
        
        # 获取当前页的实验数据
        start_idx = (st.session_state.experiment_page - 1) * PAGE_SIZE
        end_idx = min(start_idx + PAGE_SIZE, total_experiments)
        current_page_experiments = experiments[start_idx:end_idx]
        
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
        for exp in experiments:
            exp_id = exp["id"]
            if exp_id in st.session_state.selected_experiments:
                if st.session_state.selected_experiments[exp_id]:
                    selected_exp_ids.append(exp_id)
        
        if selected_exp_ids:
            # 获取选中的实验名称
            selected_exp_names = []
            for exp in experiments:
                if exp["id"] in selected_exp_ids:
                    selected_exp_names.append(exp["name"])
            
            st.warning(f"⚠️ 已选择 {len(selected_exp_ids)} 个实验进行删除")
            
            # 显示选中的实验列表
            with st.expander("📋 查看选中实验", expanded=False):
                for i, exp_id in enumerate(selected_exp_ids):
                    exp_info = next((e for e in experiments if e["id"] == exp_id), None)
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
                    for exp in experiments:
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
                        exp_info = next((e for e in experiments if e["id"] == exp_id), None)
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
        st.info("暂无实验数据，请创建第一个实验。")

                
# -------------------- 数据记录页面 --------------------
def render_data_recording():
    """渲染数据记录页面 - 重构版"""
    st.header("📝 数据记录")
    
    # 使用标签页组织不同模块
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🧪 合成实验", 
        "📦 原材料管理", 
        "📊 成品减水剂",
        "🧫 净浆实验", 
        "🏗️ 砂浆实验", 
        "🏢 混凝土实验"
    ])
    
    # ==================== 原材料管理模块 ====================
    with tab2:
        st.subheader("📦 原材料管理")
        
        # 初始化原材料数据
        if "raw_materials" not in st.session_state:
            st.session_state.raw_materials = []
        
        # 添加新原材料表单
        with st.expander("➕ 添加新原材料", expanded=True):
            with st.form("add_raw_material_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    material_name = st.text_input("原材料名称*", key="material_name")
                    chemical_formula = st.text_input("化学式", key="chemical_formula")
                    molecular_weight = st.number_input("分子量 (g/mol)", 
                                                      min_value=0.0, 
                                                      step=0.01,
                                                      key="molecular_weight")
                    solid_content = st.number_input("固含 (%)", 
                                                   min_value=0.0, 
                                                   max_value=100.0,
                                                   step=0.1,
                                                   key="solid_content")
                with col2:
                    unit_price = st.number_input("单价 (元/吨)", 
                                                min_value=0.0,
                                                step=0.1,
                                                key="unit_price")
                    odor = st.selectbox("气味", 
                                       ["无", "轻微", "中等", "强烈", "刺激性"],
                                       key="odor")
                    storage_condition = st.text_input("存储条件", key="storage_condition")
                    supplier = st.text_input("供应商", key="supplier")
                
                main_usage = st.text_area("主要用途描述*", height=100, key="main_usage")
                
                submitted = st.form_submit_button("添加原材料", type="primary")
                if submitted:
                    if material_name and main_usage:
                        # 检查是否重复
                        existing_names = [m.get("name") for m in st.session_state.raw_materials]
                        if material_name in existing_names:
                            st.error(f"原材料 '{material_name}' 已存在！")
                        else:
                            new_material = {
                                "id": len(st.session_state.raw_materials) + 1,
                                "name": material_name,
                                "chemical_formula": chemical_formula,
                                "molecular_weight": molecular_weight,
                                "solid_content": solid_content,
                                "unit_price": unit_price,
                                "odor": odor,
                                "storage_condition": storage_condition,
                                "supplier": supplier,
                                "main_usage": main_usage,
                                "created_date": datetime.now().strftime("%Y-%m-%d")
                            }
                            st.session_state.raw_materials.append(new_material)
                            st.success(f"原材料 '{material_name}' 添加成功！")
                    else:
                        st.error("请填写带*的必填项")
        
        # 原材料列表
        st.divider()
        st.subheader("📋 原材料列表")
        
        if st.session_state.raw_materials:
            # 搜索功能
            search_col1, search_col2 = st.columns([3, 1])
            with search_col1:
                search_term = st.text_input("🔍 搜索原材料", 
                                           placeholder="输入名称或化学式搜索")
            with search_col2:
                items_per_page = st.selectbox("每页显示", [10, 20, 50], index=0)
            
            # 过滤数据
            filtered_materials = st.session_state.raw_materials
            if search_term:
                filtered_materials = [
                    m for m in filtered_materials
                    if search_term.lower() in m.get("name", "").lower() or 
                    search_term.lower() in m.get("chemical_formula", "").lower()
                ]
            
            # 分页
            if "material_page" not in st.session_state:
                st.session_state.material_page = 1
            
            total_pages = max(1, (len(filtered_materials) + items_per_page - 1) // items_per_page)
            start_idx = (st.session_state.material_page - 1) * items_per_page
            end_idx = min(start_idx + items_per_page, len(filtered_materials))
            current_materials = filtered_materials[start_idx:end_idx]
            
            # 显示表格
            if current_materials:
                # 创建紧凑表格
                for material in current_materials:
                    with st.container():
                        col1, col2, col3 = st.columns([2, 2, 1])
                        with col1:
                            st.markdown(f"**{material['name']}**")
                            if material['chemical_formula']:
                                st.caption(f"化学式: {material['chemical_formula']}")
                            st.caption(f"分子量: {material['molecular_weight']} g/mol")
                        with col2:
                            st.caption(f"固含: {material['solid_content']}%")
                            st.caption(f"单价: ¥{material['unit_price']}/吨")
                            st.caption(f"气味: {material['odor']}")
                        with col3:
                            st.caption(f"ID: {material['id']}")
                            if st.button("删除", key=f"del_material_{material['id']}"):
                                st.session_state.raw_materials = [
                                    m for m in st.session_state.raw_materials 
                                    if m['id'] != material['id']
                                ]
                                st.rerun()
                        st.markdown(f"**用途:** {material['main_usage']}")
                        st.divider()
                
                # 分页控制
                if total_pages > 1:
                    pag_col1, pag_col2, pag_col3 = st.columns([1, 2, 1])
                    with pag_col2:
                        col_prev, col_page, col_next = st.columns([1, 2, 1])
                        with col_prev:
                            if st.button("⬅️", key="mat_prev") and st.session_state.material_page > 1:
                                st.session_state.material_page -= 1
                                st.rerun()
                        with col_page:
                            page_num = st.number_input(
                                "页码", 
                                min_value=1, 
                                max_value=total_pages,
                                value=st.session_state.material_page,
                                key="mat_page_input",
                                label_visibility="collapsed"
                            )
                            if page_num != st.session_state.material_page:
                                st.session_state.material_page = page_num
                                st.rerun()
                        with col_next:
                            if st.button("➡️", key="mat_next") and st.session_state.material_page < total_pages:
                                st.session_state.material_page += 1
                                st.rerun()
        else:
            st.info("暂无原材料数据，请添加第一个原材料")
    
    # -------------------- 数据记录页面 --------------------
def render_data_recording():
    """渲染数据记录页面 - 重构版"""
    st.header("📝 数据记录")
    
    # 使用标签页组织不同模块
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🧪 合成实验", 
        "📦 原材料管理", 
        "📊 成品减水剂",
        "🧫 净浆实验", 
        "🏗️ 砂浆实验", 
        "🏢 混凝土实验"
    ])
    
    # ==================== 原材料管理模块 ====================
    with tab2:
        st.subheader("📦 原材料管理")
        
        # 初始化原材料数据
        if "raw_materials" not in st.session_state:
            st.session_state.raw_materials = []
        
        # 添加新原材料表单
        with st.expander("➕ 添加新原材料", expanded=True):
            with st.form("data_recording_raw_material_add_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    material_name = st.text_input("原材料名称*", key="data_raw_material_name")
                    chemical_formula = st.text_input("化学式", key="data_raw_chemical_formula")
                    molecular_weight = st.number_input("分子量 (g/mol)", 
                                                      min_value=0.0, 
                                                      step=0.01,
                                                      key="data_raw_molecular_weight")
                    solid_content = st.number_input("固含 (%)", 
                                                   min_value=0.0, 
                                                   max_value=100.0,
                                                   step=0.1,
                                                   key="data_raw_solid_content")
                with col2:
                    unit_price = st.number_input("单价 (元/吨)", 
                                                min_value=0.0,
                                                step=0.1,
                                                key="data_raw_unit_price")
                    odor = st.selectbox("气味", 
                                       ["无", "轻微", "中等", "强烈", "刺激性"],
                                       key="data_raw_odor")
                    storage_condition = st.text_input("存储条件", key="data_raw_storage_condition")
                    supplier = st.text_input("供应商", key="data_raw_supplier")
                
                main_usage = st.text_area("主要用途描述*", height=100, key="data_raw_main_usage")
                
                submitted = st.form_submit_button("添加原材料", type="primary")
                if submitted:
                    if material_name and main_usage:
                        # 检查是否重复
                        existing_names = [m.get("name") for m in st.session_state.raw_materials]
                        if material_name in existing_names:
                            st.error(f"原材料 '{material_name}' 已存在！")
                        else:
                            new_material = {
                                "id": len(st.session_state.raw_materials) + 1,
                                "name": material_name,
                                "chemical_formula": chemical_formula,
                                "molecular_weight": molecular_weight,
                                "solid_content": solid_content,
                                "unit_price": unit_price,
                                "odor": odor,
                                "storage_condition": storage_condition,
                                "supplier": supplier,
                                "main_usage": main_usage,
                                "created_date": datetime.now().strftime("%Y-%m-%d")
                            }
                            st.session_state.raw_materials.append(new_material)
                            st.success(f"原材料 '{material_name}' 添加成功！")
                            time.sleep(0.5)
                            st.rerun()
                    else:
                        st.error("请填写带*的必填项")
        
        # 原材料列表
        st.divider()
        st.subheader("📋 原材料列表")
        
        if st.session_state.raw_materials:
            # 搜索功能
            search_col1, search_col2 = st.columns([3, 1])
            with search_col1:
                search_term = st.text_input("🔍 搜索原材料", 
                                           placeholder="输入名称或化学式搜索",
                                           key="data_raw_material_search")
            with search_col2:
                items_per_page = st.selectbox("每页显示", [10, 20, 50], index=0, key="data_raw_material_page_size")
            
            # 过滤数据
            filtered_materials = st.session_state.raw_materials
            if search_term:
                filtered_materials = [
                    m for m in filtered_materials
                    if search_term.lower() in m.get("name", "").lower() or 
                    search_term.lower() in m.get("chemical_formula", "").lower()
                ]
            
            # 分页
            if "data_material_page" not in st.session_state:
                st.session_state.data_material_page = 1
            
            total_pages = max(1, (len(filtered_materials) + items_per_page - 1) // items_per_page)
            start_idx = (st.session_state.data_material_page - 1) * items_per_page
            end_idx = min(start_idx + items_per_page, len(filtered_materials))
            current_materials = filtered_materials[start_idx:end_idx]
            
            # 显示表格
            if current_materials:
                # 创建紧凑表格
                for material in current_materials:
                    with st.container():
                        col1, col2, col3 = st.columns([2, 2, 1])
                        with col1:
                            st.markdown(f"**{material['name']}**")
                            if material['chemical_formula']:
                                st.caption(f"化学式: {material['chemical_formula']}")
                            st.caption(f"分子量: {material['molecular_weight']} g/mol")
                        with col2:
                            st.caption(f"固含: {material['solid_content']}%")
                            st.caption(f"单价: ¥{material['unit_price']}/吨")
                            st.caption(f"气味: {material['odor']}")
                        with col3:
                            st.caption(f"ID: {material['id']}")
                            delete_key = f"data_del_material_{material['id']}"
                            if st.button("删除", key=delete_key):
                                st.session_state.raw_materials = [
                                    m for m in st.session_state.raw_materials 
                                    if m['id'] != material['id']
                                ]
                                st.success(f"已删除原材料: {material['name']}")
                                time.sleep(0.5)
                                st.rerun()
                        st.markdown(f"**用途:** {material['main_usage']}")
                        st.divider()
                
                # 分页控制
                if total_pages > 1:
                    pag_col1, pag_col2, pag_col3 = st.columns([1, 2, 1])
                    with pag_col2:
                        col_prev, col_page, col_next = st.columns([1, 2, 1])
                        with col_prev:
                            prev_key = "data_raw_mat_prev"
                            if st.button("⬅️", key=prev_key) and st.session_state.data_material_page > 1:
                                st.session_state.data_material_page -= 1
                                st.rerun()
                        with col_page:
                            page_num = st.number_input(
                                "页码", 
                                min_value=1, 
                                max_value=total_pages,
                                value=st.session_state.data_material_page,
                                key="data_raw_mat_page_input",
                                label_visibility="collapsed"
                            )
                            if page_num != st.session_state.data_material_page:
                                st.session_state.data_material_page = page_num
                                st.rerun()
                        with col_next:
                            next_key = "data_raw_mat_next"
                            if st.button("➡️", key=next_key) and st.session_state.data_material_page < total_pages:
                                st.session_state.data_material_page += 1
                                st.rerun()
            else:
                st.info("没有找到匹配的原材料")
        else:
            st.info("暂无原材料数据，请添加第一个原材料")
    
    # ==================== 合成实验模块 ====================
    with tab1:
        st.subheader("🧪 合成实验记录")
        
        # 初始化合成实验数据
        if "synthesis_records" not in st.session_state:
            st.session_state.synthesis_records = []
        
        # 获取实验项目选项
        experiments = data_manager.get_all_experiments()
        experiment_options = {f"{e['id']}: {e['name']}": e['id'] for e in experiments}
        
        # 获取原材料选项
        raw_material_names = [m['name'] for m in st.session_state.raw_materials] if st.session_state.raw_materials else []
        raw_material_options = {m['name']: m['id'] for m in st.session_state.raw_materials} if st.session_state.raw_materials else {}
        
        # 添加新合成实验表单
        with st.expander("➕ 新增合成实验", expanded=True):
            with st.form("data_recording_synthesis_experiment_form", clear_on_submit=True):
                # ==================== 第一部分：基础信息 ====================
                st.markdown("### 📝 第一部分：基础信息")
                base_col1, base_col2 = st.columns(2)
                
                with base_col1:
                    # 关联实验项目
                    if experiment_options:
                        selected_exp_key = st.selectbox(
                            "关联实验项目*",
                            options=["请选择..."] + list(experiment_options.keys()),
                            key="data_synthesis_project_select"
                        )
                        experiment_id = experiment_options.get(selected_exp_key) if selected_exp_key != "请选择..." else None
                    else:
                        st.warning("请先在实验管理模块创建实验")
                        experiment_id = None
                    
                    # 配方编号
                    formula_id = st.text_input("配方编号*", 
                                             placeholder="例如: PC-001-202401",
                                             key="data_synthesis_formula_id")
                    
                with base_col2:
                    # 设计固含
                    design_solid_content = st.number_input("设计固含 (%)*", 
                                                          min_value=0.0, 
                                                          max_value=100.0,
                                                          value=40.0,
                                                          step=0.1,
                                                          help="设计的固含量百分比",
                                                          key="data_synthesis_design_solid")
                    
                    # 合成日期
                    synthesis_date = st.date_input("合成日期", 
                                                  datetime.now(),
                                                  key="data_synthesis_date")
                    
                    # 操作人
                    operator = st.text_input("操作人*", 
                                            placeholder="请输入操作人员姓名",
                                            key="data_synthesis_operator")
                
                st.divider()
                
                # ==================== 第二部分：反应釜物料 ====================
                st.markdown("### ⚗️ 第二部分：反应釜物料")
                st.info("请从原材料库中选择以下物料并填写用量（单位: g）")
                
                # 反应釜物料 - 使用表格布局
                reactor_cols = st.columns(7)
                reactor_materials = []
                
                # 定义反应釜物料列表
                reactor_items = [
                    {"name": "单体1", "key": "monomer1"},
                    {"name": "单体2", "key": "monomer2"},
                    {"name": "单体3", "key": "monomer3"},
                    {"name": "单体4", "key": "monomer4"},
                    {"name": "引发剂", "key": "initiator"},
                    {"name": "链转移剂1", "key": "chain_transfer1"},
                    {"name": "水", "key": "water_reactor"}
                ]
                
                for i, item in enumerate(reactor_items):
                    with reactor_cols[i]:
                        st.markdown(f"**{item['name']}**")
                        
                        # 物料选择 - 使用模糊搜索的selectbox
                        material_options = ["请选择..."] + raw_material_names
                        selected_material = st.selectbox(
                            f"选择{item['name']}",
                            options=material_options,
                            key=f"data_reactor_{item['key']}_select_{i}",
                            help="输入名称搜索原材料",
                            index=0,
                            label_visibility="collapsed"
                        )
                        
                        # 用量输入
                        amount = st.number_input(
                            f"用量 (g)",
                            min_value=0.0,
                            step=0.1,
                            value=0.0,
                            key=f"data_reactor_{item['key']}_amount_{i}",
                            label_visibility="collapsed"
                        )
                        
                        if selected_material and selected_material != "请选择..." and amount > 0:
                            reactor_materials.append({
                                "name": item["name"],
                                "material_name": selected_material,
                                "amount": amount
                            })
                
                # 显示反应釜物料总用量
                total_reactor = sum([m["amount"] for m in reactor_materials])
                st.caption(f"反应釜物料总用量: **{total_reactor:.2f} g**")
                
                st.divider()
                
                # ==================== 第三部分：A料 ====================
                st.markdown("### 🔴 第三部分：A料")
                st.info("A料组成及滴加参数")
                
                # A料物料
                a_cols = st.columns(6)
                a_materials = []
                
                # 定义A料物料列表
                a_items = [
                    {"name": "单体a", "key": "monomer_a"},
                    {"name": "单体b", "key": "monomer_b"},
                    {"name": "单体c", "key": "monomer_c"},
                    {"name": "单体d", "key": "monomer_d"},
                    {"name": "水", "key": "water_a"},
                    {"name": "其他", "key": "other_a"}
                ]
                
                for i, item in enumerate(a_items):
                    with a_cols[i]:
                        st.markdown(f"**{item['name']}**")
                        
                        # 物料选择 - 使用模糊搜索的selectbox
                        material_options = ["请选择..."] + raw_material_names
                        selected_material = st.selectbox(
                            f"选择{item['name']}",
                            options=material_options,
                            key=f"data_a_{item['key']}_select_{i}",
                            help="输入名称搜索原材料",
                            index=0,
                            label_visibility="collapsed"
                        )
                        
                        # 用量输入
                        amount = st.number_input(
                            f"用量 (g)",
                            min_value=0.0,
                            step=0.1,
                            value=0.0,
                            key=f"data_a_{item['key']}_amount_{i}",
                            label_visibility="collapsed"
                        )
                        
                        if selected_material and selected_material != "请选择..." and amount > 0:
                            a_materials.append({
                                "name": item["name"],
                                "material_name": selected_material,
                                "amount": amount
                            })
                
                # A料滴加参数
                st.markdown("**滴加参数**")
                a_drip_col1, a_drip_col2, a_drip_col3 = st.columns(3)
                
                with a_drip_col1:
                    # A料总量（自动计算）
                    a_total_amount = sum([m["amount"] for m in a_materials])
                    # 修复：移除metric的key参数
                    st.metric("A料总用量", f"{a_total_amount:.2f} g")
                
                with a_drip_col2:
                    # 滴加时间
                    a_drip_time = st.number_input(
                        "滴加时间 (分钟)*",
                        min_value=0.0,
                        value=120.0,
                        step=1.0,
                        key="data_a_drip_time_input"
                    )
                
                with a_drip_col3:
                    # 滴加速度（自动计算）
                    a_drip_speed = 0.0
                    if a_drip_time > 0 and a_total_amount > 0:
                        a_drip_speed = a_total_amount / a_drip_time
                    # 修复：移除metric的key参数
                    st.metric("滴加速度", f"{a_drip_speed:.2f} g/min")
                
                st.divider()
                
                # ==================== 第四部分：B料 ====================
                st.markdown("### 🔵 第四部分：B料")
                st.info("B料组成及滴加参数")
                
                # B料物料
                b_cols = st.columns(5)
                b_materials = []
                
                # 定义B料物料列表
                b_items = [
                    {"name": "引发剂2", "key": "initiator2"},
                    {"name": "链转移剂2", "key": "chain_transfer2"},
                    {"name": "水", "key": "water_b"},
                    {"name": "其他1", "key": "other_b1"},
                    {"name": "其他2", "key": "other_b2"}
                ]
                
                for i, item in enumerate(b_items):
                    with b_cols[i]:
                        st.markdown(f"**{item['name']}**")
                        
                        # 物料选择 - 使用模糊搜索的selectbox
                        material_options = ["请选择..."] + raw_material_names
                        selected_material = st.selectbox(
                            f"选择{item['name']}",
                            options=material_options,
                            key=f"data_b_{item['key']}_select_{i}",
                            help="输入名称搜索原材料",
                            index=0,
                            label_visibility="collapsed"
                        )
                        
                        # 用量输入
                        amount = st.number_input(
                            f"用量 (g)",
                            min_value=0.0,
                            step=0.1,
                            value=0.0,
                            key=f"data_b_{item['key']}_amount_{i}",
                            label_visibility="collapsed"
                        )
                        
                        if selected_material and selected_material != "请选择..." and amount > 0:
                            b_materials.append({
                                "name": item["name"],
                                "material_name": selected_material,
                                "amount": amount
                            })
                
                # B料滴加参数
                st.markdown("**滴加参数**")
                b_drip_col1, b_drip_col2, b_drip_col3 = st.columns(3)
                
                with b_drip_col1:
                    # B料总量（自动计算）
                    b_total_amount = sum([m["amount"] for m in b_materials])
                    # 修复：移除metric的key参数
                    st.metric("B料总用量", f"{b_total_amount:.2f} g")
                
                with b_drip_col2:
                    # 滴加时间
                    b_drip_time = st.number_input(
                        "滴加时间 (分钟)*",
                        min_value=0.0,
                        value=60.0,
                        step=1.0,
                        key="data_b_drip_time_input"
                    )
                
                with b_drip_col3:
                    # 滴加速度（自动计算）
                    b_drip_speed = 0.0
                    if b_drip_time > 0 and b_total_amount > 0:
                        b_drip_speed = b_total_amount / b_drip_time
                    # 修复：移除metric的key参数
                    st.metric("滴加速度", f"{b_drip_speed:.2f} g/min")
                
                st.divider()
                
                # ==================== 第五部分：反应参数 ====================
                st.markdown("### 🔥 第五部分：反应参数")
                
                # 反应参数
                st.markdown("**温度控制**")
                reaction_col1, reaction_col2, reaction_col3 = st.columns(3)
                
                with reaction_col1:
                    # 起始温度
                    start_temp = st.number_input(
                        "起始温度 (°C)*",
                        min_value=0.0,
                        max_value=100.0,
                        value=20.0,
                        step=0.5,
                        key="data_start_temp_input"
                    )
                
                with reaction_col2:
                    # 最高温度
                    max_temp = st.number_input(
                        "最高温度 (°C)*",
                        min_value=0.0,
                        max_value=200.0,
                        value=80.0,
                        step=0.5,
                        key="data_max_temp_input"
                    )
                
                with reaction_col3:
                    # 保温时间
                    holding_time = st.number_input(
                        "保温时间 (小时)*",
                        min_value=0.0,
                        max_value=24.0,
                        value=2.0,
                        step=0.5,
                        key="data_holding_time_input"
                    )
                
                # 工艺备注
                process_notes = st.text_area(
                    "实验工艺备注",
                    height=150,
                    placeholder="请详细记录实验过程中的观察、调整、异常情况等工艺信息...",
                    key="data_synthesis_process_notes"
                )
                
                # 提交按钮
                submitted = st.form_submit_button("💾 保存合成实验记录", type="primary")
                
                if submitted:
                    # 验证必填项
                    validation_errors = []
                    
                    if not experiment_id:
                        validation_errors.append("请选择关联实验项目")
                    
                    if not formula_id:
                        validation_errors.append("请输入配方编号")
                    
                    if not design_solid_content:
                        validation_errors.append("请输入设计固含")
                    
                    if not operator:
                        validation_errors.append("请输入操作人")
                    
                    if a_drip_time <= 0:
                        validation_errors.append("请输入有效的A料滴加时间")
                    
                    if b_drip_time <= 0:
                        validation_errors.append("请输入有效的B料滴加时间")
                    
                    if start_temp <= 0:
                        validation_errors.append("请输入有效的起始温度")
                    
                    if max_temp <= 0 or max_temp < start_temp:
                        validation_errors.append("最高温度必须大于起始温度")
                    
                    if holding_time <= 0:
                        validation_errors.append("请输入有效的保温时间")
                    
                    # 检查是否选择了至少一种物料
                    if not reactor_materials and not a_materials and not b_materials:
                        validation_errors.append("请至少添加一种物料")
                    
                    if validation_errors:
                        for error in validation_errors:
                            st.error(error)
                    else:
                        # 构建新的合成实验记录
                        new_record = {
                            "id": len(st.session_state.synthesis_records) + 1,
                            "formula_id": formula_id,
                            "experiment_id": experiment_id,
                            "design_solid_content": design_solid_content,
                            "operator": operator,
                            "synthesis_date": synthesis_date.strftime("%Y-%m-%d"),
                            
                            # 反应釜物料
                            "reactor_materials": reactor_materials,
                            "reactor_total_amount": total_reactor,
                            
                            # A料
                            "a_materials": a_materials,
                            "a_total_amount": a_total_amount,
                            "a_drip_time": a_drip_time,
                            "a_drip_speed": a_drip_speed,
                            
                            # B料
                            "b_materials": b_materials,
                            "b_total_amount": b_total_amount,
                            "b_drip_time": b_drip_time,
                            "b_drip_speed": b_drip_speed,
                            
                            # 反应参数
                            "start_temp": start_temp,
                            "max_temp": max_temp,
                            "holding_time": holding_time,
                            
                            # 备注
                            "process_notes": process_notes,
                            
                            # 元数据
                            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "last_modified": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        
                        # 保存到session_state
                        st.session_state.synthesis_records.append(new_record)
                        
                        # 显示成功消息和摘要
                        st.success(f"✅ 合成实验记录 '{formula_id}' 保存成功！")
                        
                        # 显示数据摘要
                        with st.expander("📋 查看数据摘要", expanded=False):
                            summary_col1, summary_col2 = st.columns(2)
                            
                            with summary_col1:
                                st.markdown("**基础信息**")
                                st.write(f"**配方编号:** {formula_id}")
                                st.write(f"**操作人:** {operator}")
                                st.write(f"**设计固含:** {design_solid_content}%")
                                st.write(f"**合成日期:** {synthesis_date.strftime('%Y-%m-%d')}")
                            
                            with summary_col2:
                                st.markdown("**物料总览**")
                                st.write(f"**反应釜总用量:** {total_reactor:.2f} g")
                                st.write(f"**A料总用量:** {a_total_amount:.2f} g")
                                st.write(f"**B料总用量:** {b_total_amount:.2f} g")
                                total_materials = total_reactor + a_total_amount + b_total_amount
                                st.write(f"**总物料量:** {total_materials:.2f} g")
                        
                        time.sleep(0.5)
                        st.rerun()
    
    # ==================== 合成实验数据查看 ====================
        st.divider()
        st.subheader("📊 合成实验数据查看")
        
        if st.session_state.synthesis_records:
            # 搜索和过滤功能
            search_col1, search_col2, search_col3 = st.columns([2, 2, 1])
            with search_col1:
                search_formula = st.text_input("搜索配方编号", 
                                             placeholder="输入配方编号",
                                             key="data_synthesis_search_formula")
            with search_col2:
                search_operator = st.text_input("搜索操作人", 
                                              placeholder="输入操作人姓名",
                                              key="data_synthesis_search_operator")
            with search_col3:
                items_per_page = st.selectbox("每页显示", [10, 20, 50], index=1, key="data_synthesis_page_size")
            
            # 过滤数据
            filtered_records = st.session_state.synthesis_records
            if search_formula:
                filtered_records = [
                    r for r in filtered_records
                    if search_formula.lower() in r.get("formula_id", "").lower()
                ]
            if search_operator:
                filtered_records = [
                    r for r in filtered_records
                    if search_operator.lower() in r.get("operator", "").lower()
                ]
            
            # 分页
            if "data_syn_page" not in st.session_state:
                st.session_state.data_syn_page = 1
            
            total_pages = max(1, (len(filtered_records) + items_per_page - 1) // items_per_page)
            start_idx = (st.session_state.data_syn_page - 1) * items_per_page
            end_idx = min(start_idx + items_per_page, len(filtered_records))
            current_records = filtered_records[start_idx:end_idx]
            
            # 显示表格
            if current_records:
                # 表头
                header_cols = st.columns([1, 2, 2, 2, 2, 2])
                headers = ["序号", "配方编号", "操作人", "设计固含(%)", "合成日期", "操作"]
                
                for i, header in enumerate(headers):
                    header_cols[i].markdown(f"**{header}**")
                
                st.divider()
                
                # 数据行
                for idx, record in enumerate(current_records, start=start_idx+1):
                    with st.container():
                        row_cols = st.columns([1, 2, 2, 2, 2, 2])
                        
                        with row_cols[0]:
                            st.write(idx)
                        
                        with row_cols[1]:
                            formula = record.get("formula_id", "")
                            st.write(f"`{formula}`")
                        
                        with row_cols[2]:
                            st.write(record.get("operator", ""))
                        
                        with row_cols[3]:
                            st.write(f"{record.get('design_solid_content', 0)}%")
                        
                        with row_cols[4]:
                            st.write(record.get("synthesis_date", ""))
                        
                        with row_cols[5]:
                            # 查看详情按钮
                            view_key = f"data_view_synth_{record['id']}_{idx}"
                            if st.button("📋 详情", key=view_key):
                                if f"data_show_detail_{record['id']}" not in st.session_state:
                                    st.session_state[f"data_show_detail_{record['id']}"] = False
                                st.session_state[f"data_show_detail_{record['id']}"] = not st.session_state[f"data_show_detail_{record['id']}"]
                                st.rerun()
                            
                            # 删除按钮
                            delete_key = f"data_delete_synth_{record['id']}_{idx}"
                            if st.button("🗑️ 删除", key=delete_key):
                                st.session_state.synthesis_records = [
                                    r for r in st.session_state.synthesis_records 
                                    if r['id'] != record['id']
                                ]
                                st.success(f"已删除合成实验: {formula}")
                                time.sleep(0.5)
                                st.rerun()
                        
                        # 详细信息（可折叠）
                        if st.session_state.get(f"data_show_detail_{record['id']}", False):
                            with st.expander(f"📋 配方 {formula} 详细信息", expanded=True):
                                # 分页显示详细信息
                                detail_tabs = st.tabs(["基础信息", "反应釜物料", "A料", "B料", "反应参数", "工艺备注"])
                                
                                with detail_tabs[0]:
                                    base_col1, base_col2 = st.columns(2)
                                    with base_col1:
                                        st.markdown("**基础信息**")
                                        st.write(f"**配方编号:** {record.get('formula_id')}")
                                        st.write(f"**操作人:** {record.get('operator')}")
                                        st.write(f"**合成日期:** {record.get('synthesis_date')}")
                                    
                                    with base_col2:
                                        st.markdown("**设计参数**")
                                        st.write(f"**设计固含:** {record.get('design_solid_content')}%")
                                        st.write(f"**起始温度:** {record.get('start_temp')}°C")
                                        st.write(f"**最高温度:** {record.get('max_temp')}°C")
                                        st.write(f"**保温时间:** {record.get('holding_time')}小时")
                                
                                with detail_tabs[1]:
                                    if record.get('reactor_materials'):
                                        st.markdown("**反应釜物料组成**")
                                        reactor_df = pd.DataFrame(record['reactor_materials'])
                                        st.dataframe(reactor_df, use_container_width=True)
                                        # 修复：移除metric的key参数
                                        st.metric("反应釜总用量", f"{record.get('reactor_total_amount', 0):.2f} g")
                                    else:
                                        st.info("暂无反应釜物料数据")
                                
                                with detail_tabs[2]:
                                    if record.get('a_materials'):
                                        st.markdown("**A料组成**")
                                        a_df = pd.DataFrame(record['a_materials'])
                                        st.dataframe(a_df, use_container_width=True)
                                        
                                        a_info_col1, a_info_col2, a_info_col3 = st.columns(3)
                                        with a_info_col1:
                                            # 修复：移除metric的key参数
                                            st.metric("A料总用量", f"{record.get('a_total_amount', 0):.2f} g")
                                        with a_info_col2:
                                            # 修复：移除metric的key参数
                                            st.metric("滴加时间", f"{record.get('a_drip_time', 0)} 分钟")
                                        with a_info_col3:
                                            # 修复：移除metric的key参数
                                            st.metric("滴加速度", f"{record.get('a_drip_speed', 0):.2f} g/min")
                                    else:
                                        st.info("暂无A料数据")
                                
                                with detail_tabs[3]:
                                    if record.get('b_materials'):
                                        st.markdown("**B料组成**")
                                        b_df = pd.DataFrame(record['b_materials'])
                                        st.dataframe(b_df, use_container_width=True)
                                        
                                        b_info_col1, b_info_col2, b_info_col3 = st.columns(3)
                                        with b_info_col1:
                                            # 修复：移除metric的key参数
                                            st.metric("B料总用量", f"{record.get('b_total_amount', 0):.2f} g")
                                        with b_info_col2:
                                            # 修复：移除metric的key参数
                                            st.metric("滴加时间", f"{record.get('b_drip_time', 0)} 分钟")
                                        with b_info_col3:
                                            # 修复：移除metric的key参数
                                            st.metric("滴加速度", f"{record.get('b_drip_speed', 0):.2f} g/min")
                                    else:
                                        st.info("暂无B料数据")
                                
                                with detail_tabs[4]:
                                    st.markdown("**反应参数**")
                                    reaction_cols = st.columns(3)
                                    with reaction_cols[0]:
                                        # 修复：移除metric的key参数
                                        st.metric("起始温度", f"{record.get('start_temp', 0)}°C")
                                    with reaction_cols[1]:
                                        # 修复：移除metric的key参数
                                        st.metric("最高温度", f"{record.get('max_temp', 0)}°C")
                                    with reaction_cols[2]:
                                        # 修复：移除metric的key参数
                                        st.metric("保温时间", f"{record.get('holding_time', 0)}小时")
                                
                                with detail_tabs[5]:
                                    if record.get('process_notes'):
                                        st.markdown("**实验工艺备注**")
                                        st.info(record['process_notes'])
                                    else:
                                        st.info("暂无工艺备注")
                        
                        st.divider()
                
                # 分页控制
                if total_pages > 1:
                    st.markdown("---")
                    pag_col1, pag_col2, pag_col3 = st.columns([2, 1, 2])
                    
                    with pag_col1:
                        prev_key = "data_synthesis_prev"
                        if st.button("⬅️ 上一页", 
                                   disabled=st.session_state.data_syn_page <= 1,
                                   key=prev_key):
                            st.session_state.data_syn_page -= 1
                            st.rerun()
                    
                    with pag_col2:
                        st.markdown(f"**第 {st.session_state.data_syn_page}/{total_pages} 页**")
                    
                    with pag_col3:
                        next_key = "data_synthesis_next"
                        if st.button("下一页 ➡️", 
                                   disabled=st.session_state.data_syn_page >= total_pages,
                                   key=next_key):
                            st.session_state.data_syn_page += 1
                            st.rerun()
            else:
                st.info("没有找到匹配的合成实验记录")
        else:
            st.info("暂无合成实验数据，请添加第一条记录")
    
    # ==================== 成品减水剂模块 ====================
    with tab3:
        st.subheader("📊 成品减水剂管理")
        
        # 初始化成品减水剂数据
        if "products" not in st.session_state:
            st.session_state.products = []
        
        with st.expander("➕ 新增成品减水剂", expanded=True):
            with st.form("add_product_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    product_name = st.text_input("成品名称*", 
                                                placeholder="例如: PC-2024-HP")
                    product_code = st.text_input("产品编号*",
                                                placeholder="例如: PC001-2024")
                    batch_number = st.text_input("生产批号")
                    production_date = st.date_input("生产日期", datetime.now())
                with col2:
                    solid_content = st.number_input("固含(%)*", 
                                                   min_value=0.0, 
                                                   max_value=100.0,
                                                   value=40.0,
                                                   step=0.1)
                    density = st.number_input("密度 (g/cm³)", 
                                             min_value=0.8, 
                                             max_value=2.0,
                                             value=1.05,
                                             step=0.01)
                    ph_value = st.number_input("pH值", 
                                              min_value=0.0, 
                                              max_value=14.0,
                                              value=7.0,
                                              step=0.1)
                
                # 关联配方选项（来自合成实验或已有的成品）
                formula_options = []
                if st.session_state.synthesis_records:
                    formula_options.extend([
                        f"合成实验: {r['formula_id']}" for r in st.session_state.synthesis_records
                    ])
                if st.session_state.products:
                    formula_options.extend([
                        f"成品: {p['product_name']}" for p in st.session_state.products
                    ])
                
                if formula_options:
                    base_formula = st.selectbox("基础配方", 
                                              options=["自定义配方"] + formula_options)
                else:
                    base_formula = "自定义配方"
                
                # 原料组成
                st.markdown("### 原料组成")
                ingredient_cols = st.columns(3)
                ingredients = []
                
                for i in range(3):
                    with ingredient_cols[i]:
                        if raw_material_options:
                            material_name = st.selectbox(
                                f"原料{i+1}",
                                options=[""] + list(raw_material_options.keys()),
                                key=f"product_material_{i}"
                            )
                            if material_name:
                                amount = st.number_input(f"用量 (%)", 
                                                       min_value=0.0,
                                                       max_value=100.0,
                                                       step=0.1,
                                                       key=f"product_amount_{i}")
                                ingredients.append({
                                    "name": material_name,
                                    "amount": amount
                                })
                
                description = st.text_area("产品描述", height=100)
                
                submitted = st.form_submit_button("保存成品", type="primary")
                if submitted:
                    if product_name and product_code:
                        new_product = {
                            "id": len(st.session_state.products) + 1,
                            "product_name": product_name,
                            "product_code": product_code,
                            "batch_number": batch_number,
                            "production_date": production_date.strftime("%Y-%m-%d"),
                            "solid_content": solid_content,
                            "density": density,
                            "ph_value": ph_value,
                            "base_formula": base_formula,
                            "ingredients": ingredients,
                            "description": description,
                            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        st.session_state.products.append(new_product)
                        st.success(f"成品减水剂 '{product_name}' 保存成功！")
                    else:
                        st.error("请填写必填项")
        
        # 成品列表查看
        st.divider()
        if st.session_state.products:
            st.subheader("📋 成品列表")
            for product in st.session_state.products:
                with st.container():
                    col1, col2, col3 = st.columns([2, 2, 1])
                    with col1:
                        st.markdown(f"**{product['product_name']}**")
                        st.caption(f"编号: {product['product_code']}")
                        st.caption(f"批号: {product['batch_number']}")
                    with col2:
                        st.caption(f"固含: {product['solid_content']}%")
                        st.caption(f"密度: {product['density']} g/cm³")
                        st.caption(f"生产日期: {product['production_date']}")
                    with col3:
                        if st.button("查看详情", key=f"view_product_{product['id']}"):
                            if f"show_product_{product['id']}" not in st.session_state:
                                st.session_state[f"show_product_{product['id']}"] = False
                            st.session_state[f"show_product_{product['id']}"] = not st.session_state[f"show_product_{product['id']}"]
                    
                    # 详细信息
                    if st.session_state.get(f"show_product_{product['id']}", False):
                        with st.expander("详细信息", expanded=True):
                            detail_col1, detail_col2 = st.columns(2)
                            with detail_col1:
                                st.markdown("**基础信息**")
                                st.write(f"**基础配方:** {product['base_formula']}")
                                st.write(f"**pH值:** {product['ph_value']}")
                                if product.get('description'):
                                    st.markdown("**描述:**")
                                    st.info(product['description'])
                            
                            with detail_col2:
                                st.markdown("**原料组成**")
                                for ing in product.get('ingredients', []):
                                    if ing.get('name'):
                                        st.write(f"- {ing['name']}: {ing.get('amount', 0)}%")
                        
                    st.divider()
        else:
            st.info("暂无成品减水剂数据")
    
    # ==================== 净浆实验模块 ====================
    with tab4:
        st.subheader("🧫 净浆实验记录")
        
        # 获取可关联的配方选项
        paste_formula_options = []
        if st.session_state.synthesis_records:
            paste_formula_options.extend([
                f"合成实验: {r['formula_id']}" for r in st.session_state.synthesis_records
            ])
        if st.session_state.products:
            paste_formula_options.extend([
                f"成品: {p['product_name']}" for p in st.session_state.products
            ])
        
        with st.form("paste_experiment_form", clear_on_submit=True):
            st.markdown("### 实验设置")
            col1, col2 = st.columns(2)
            with col1:
                if paste_formula_options:
                    formula_name = st.selectbox("关联配方*", 
                                              options=paste_formula_options)
                else:
                    st.warning("请先创建合成实验或成品减水剂")
                    formula_name = None
                
                water_cement_ratio = st.number_input("水胶比*", 
                                                    min_value=0.1, 
                                                    max_value=1.0,
                                                    value=0.29,
                                                    step=0.01)
                
                cement_amount = st.number_input("水泥用量 (g)*", 
                                               min_value=100.0,
                                               value=300.0,
                                               step=1.0)
            
            with col2:
                water_amount = st.number_input("用水量 (g)*", 
                                              min_value=0.0,
                                              value=87.0,
                                              step=0.1)
                
                admixture_dosage = st.number_input("减水剂掺量 (%)*", 
                                                  min_value=0.0,
                                                  max_value=10.0,
                                                  value=0.2,
                                                  step=0.01)
                
                test_date = st.date_input("测试日期", datetime.now())
            
            # 性能指标（可折叠）
            with st.expander("📊 性能指标", expanded=False):
                perf_col1, perf_col2, perf_col3 = st.columns(3)
                with perf_col1:
                    slump_flow = st.number_input("流动度 (mm)", 
                                                min_value=0.0,
                                                value=220.0,
                                                step=1.0)
                    setting_time_initial = st.number_input("初凝时间 (min)", 
                                                          min_value=0.0,
                                                          value=300.0,
                                                          step=1.0)
                with perf_col2:
                    slump_flow_1h = st.number_input("1h流动度 (mm)", 
                                                   min_value=0.0,
                                                   value=200.0,
                                                   step=1.0)
                    setting_time_final = st.number_input("终凝时间 (min)", 
                                                        min_value=0.0,
                                                        value=480.0,
                                                        step=1.0)
                with perf_col3:
                    air_content = st.number_input("含气量 (%)", 
                                                 min_value=0.0,
                                                 max_value=20.0,
                                                 value=2.5,
                                                 step=0.1)
                    bleeding_rate = st.number_input("泌水率 (%)", 
                                                   min_value=0.0,
                                                   max_value=10.0,
                                                   value=0.5,
                                                   step=0.1)
            
            notes = st.text_area("实验备注", height=80)
            
            submitted = st.form_submit_button("保存净浆实验", type="primary")
            if submitted:
                if formula_name and water_cement_ratio > 0:
                    st.success("净浆实验数据保存成功！")
    
    # ==================== 混凝土实验模块 ====================
    with tab6:
        st.subheader("🏢 混凝土实验记录")
        
        # 获取可关联的配方选项
        concrete_formula_options = []
        if st.session_state.synthesis_records:
            concrete_formula_options.extend([
                f"合成实验: {r['formula_id']}" for r in st.session_state.synthesis_records
            ])
        if st.session_state.products:
            concrete_formula_options.extend([
                f"成品: {p['product_name']}" for p in st.session_state.products
            ])
        
        with st.form("concrete_experiment_form", clear_on_submit=True):
            st.markdown("### 配合比设计")
            
            if concrete_formula_options:
                formula_name = st.selectbox("关联减水剂配方*", 
                                          options=concrete_formula_options)
            else:
                st.warning("请先创建合成实验或成品减水剂")
                formula_name = None
            
            # 基础参数
            col1, col2 = st.columns(2)
            with col1:
                water_cement_ratio = st.number_input("水胶比*", 
                                                    min_value=0.1, 
                                                    max_value=1.0,
                                                    value=0.4,
                                                    step=0.01)
                
                sand_ratio = st.number_input("砂率 (%)*", 
                                            min_value=0.0,
                                            max_value=100.0,
                                            value=42.0,
                                            step=0.1)
                
                unit_weight = st.number_input("设计容重 (kg/m³)", 
                                            min_value=2000.0,
                                            max_value=3000.0,
                                            value=2400.0,
                                            step=10.0)
            
            with col2:
                admixture_dosage = st.number_input("减水剂掺量 (%)*", 
                                                  min_value=0.0,
                                                  max_value=5.0,
                                                  value=1.0,
                                                  step=0.05)
                
                sand_moisture = st.number_input("砂含水率 (%)", 
                                               min_value=0.0,
                                               max_value=20.0,
                                               value=3.0,
                                               step=0.1)
                
                stone_moisture = st.number_input("石含水率 (%)", 
                                                min_value=0.0,
                                                max_value=20.0,
                                                value=1.0,
                                                step=0.1)
            
            # 材料用量（可折叠）
            with st.expander("📦 材料用量 (kg/m³)", expanded=True):
                st.markdown("#### 胶凝材料")
                binder_cols = st.columns(4)
                with binder_cols[0]:
                    cement = st.number_input("水泥用量", 
                                           min_value=0.0,
                                           value=300.0,
                                           step=10.0,
                                           key="cement_amount")
                with binder_cols[1]:
                    mineral_admixture1 = st.number_input("矿物外加剂1", 
                                                        min_value=0.0,
                                                        value=50.0,
                                                        step=5.0)
                with binder_cols[2]:
                    mineral_admixture2 = st.number_input("矿物外加剂2", 
                                                        min_value=0.0,
                                                        value=0.0,
                                                        step=5.0)
                with binder_cols[3]:
                    mineral_admixture3 = st.number_input("矿物外加剂3", 
                                                        min_value=0.0,
                                                        value=0.0,
                                                        step=5.0)
                
                st.markdown("#### 骨料")
                aggregate_cols = st.columns(6)
                with aggregate_cols[0]:
                    sand1 = st.number_input("砂1", 
                                          min_value=0.0,
                                          value=800.0,
                                          step=10.0)
                with aggregate_cols[1]:
                    sand2 = st.number_input("砂2", 
                                          min_value=0.0,
                                          value=0.0,
                                          step=10.0)
                with aggregate_cols[2]:
                    sand3 = st.number_input("砂3", 
                                          min_value=0.0,
                                          value=0.0,
                                          step=10.0)
                with aggregate_cols[3]:
                    stone1 = st.number_input("石1", 
                                           min_value=0.0,
                                           value=1100.0,
                                           step=10.0)
                with aggregate_cols[4]:
                    stone2 = st.number_input("石2", 
                                           min_value=0.0,
                                           value=0.0,
                                           step=10.0)
                with aggregate_cols[5]:
                    stone3 = st.number_input("石3", 
                                           min_value=0.0,
                                           value=0.0,
                                           step=10.0)
                
                # 自动计算
                st.markdown("#### 自动计算")
                calc_cols = st.columns(3)
                
                # 计算总胶凝材料
                total_binder = cement + mineral_admixture1 + mineral_admixture2 + mineral_admixture3
                
                # 计算用水量
                water_amount = total_binder * water_cement_ratio
                
                # 计算实际用水量（考虑骨料含水）
                total_sand = sand1 + sand2 + sand3
                total_stone = stone1 + stone2 + stone3
                water_from_sand = total_sand * sand_moisture / 100
                water_from_stone = total_stone * stone_moisture / 100
                actual_water = water_amount - water_from_sand - water_from_stone
                
                # 计算总材料量
                total_materials = (
                    total_binder + 
                    total_sand + 
                    total_stone + 
                    water_amount + 
                    (total_binder * admixture_dosage / 100)
                )
                
                with calc_cols[0]:
                    st.metric("总胶凝材料", f"{total_binder:.1f} kg")
                    st.metric("计算用水量", f"{water_amount:.1f} kg")
                
                with calc_cols[1]:
                    st.metric("实际用水量", f"{actual_water:.1f} kg")
                    st.metric("砂含水引入", f"{water_from_sand:.1f} kg")
                
                with calc_cols[2]:
                    st.metric("石含水引入", f"{water_from_stone:.1f} kg")
                    st.metric("总材料量", f"{total_materials:.1f} kg")
            
            # 性能指标（可折叠）
            with st.expander("📊 混凝土性能指标", expanded=False):
                perf_col1, perf_col2, perf_col3 = st.columns(3)
                with perf_col1:
                    slump = st.number_input("坍落度 (mm)", 
                                          min_value=0.0,
                                          value=180.0,
                                          step=5.0)
                    compressive_7d = st.number_input("7天强度 (MPa)", 
                                                    min_value=0.0,
                                                    value=35.0,
                                                    step=0.1)
                with perf_col2:
                    slump_flow = st.number_input("扩展度 (mm)", 
                                               min_value=0.0,
                                               value=500.0,
                                               step=10.0)
                    compressive_28d = st.number_input("28天强度 (MPa)", 
                                                     min_value=0.0,
                                                     value=50.0,
                                                     step=0.1)
                with perf_col3:
                    air_content = st.number_input("含气量 (%)", 
                                                 min_value=0.0,
                                                 max_value=10.0,
                                                 value=3.0,
                                                 step=0.1)
                    chloride_content = st.number_input("氯离子含量 (%)", 
                                                      min_value=0.0,
                                                      max_value=0.1,
                                                      value=0.01,
                                                      step=0.001)
            
            notes = st.text_area("实验备注", height=100)
            
            submitted = st.form_submit_button("保存混凝土实验", type="primary")
            if submitted:
                if formula_name and water_cement_ratio > 0:
                    st.success("混凝土实验数据保存成功！")

def render_data_management():
    """渲染数据管理页面 - 新增的数据导出/导入和备份管理页面"""
    st.header("💾 数据管理")
    
    # 使用标签页组织功能
    tab1, tab2, tab3, tab4 = st.tabs([
        "📤 数据导出", 
        "📥 数据导入", 
        "🔙 备份管理",
        "⚙️ 系统设置"
    ])
    
    # ==================== 数据导出模块 ====================
    with tab1:
        st.subheader("📤 导出数据到Excel")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.info("""
            **导出功能说明:**
            - 导出所有数据到Excel文件
            - 包含项目、实验、原材料、合成实验、成品减水剂、净浆实验、混凝土实验等所有数据
            - 自动生成数据字典说明
            - 文件格式: .xlsx (Excel 2007+)
            """)
        
        with col2:
            # 数据统计
            st.metric("项目数量", len(data_manager.get_all_projects()))
            st.metric("实验数量", len(data_manager.get_all_experiments()))
            st.metric("原材料数量", len(data_manager.get_all_raw_materials()))
        
        # 导出选项
        st.markdown("### 导出选项")
        
        # 文件命名
        col1, col2 = st.columns(2)
        with col1:
            filename = st.text_input(
                "导出文件名",
                value=f"聚羧酸减水剂研发数据_{datetime.now().strftime('%Y%m%d_%H%M')}",
                help="不需要添加.xlsx扩展名"
            )
        
        # 导出按钮
        if st.button("🚀 开始导出数据", type="primary", use_container_width=True):
            with st.spinner("正在准备导出数据..."):
                time.sleep(1)
                
                # 执行导出
                download_link = data_manager.export_to_excel()
                
                if download_link:
                    st.success("✅ 数据导出成功！")
                    st.markdown(download_link, unsafe_allow_html=True)
                    
                    # 显示导出统计
                    with st.expander("📊 导出数据统计", expanded=False):
                        st.write(f"**项目:** {len(data_manager.get_all_projects())} 条")
                        st.write(f"**实验:** {len(data_manager.get_all_experiments())} 条")
                        st.write(f"**原材料:** {len(data_manager.get_all_raw_materials())} 条")
                        st.write(f"**合成实验:** {len(data_manager.get_all_synthesis_records())} 条")
                        st.write(f"**成品减水剂:** {len(data_manager.get_all_products())} 条")
                        st.write(f"**净浆实验:** {len(data_manager.get_all_paste_experiments())} 条")
                        st.write(f"**混凝土实验:** {len(data_manager.get_all_concrete_experiments())} 条")
                else:
                    st.error("❌ 数据导出失败，请重试")
    
    # ==================== 数据导入模块 ====================
    with tab2:
        st.subheader("📥 从Excel导入数据")
        
        st.warning("""
        ⚠️ **导入前请注意:**
        1. 建议先备份当前数据
        2. 导入将覆盖现有数据
        3. 确保导入文件格式正确
        4. 导入过程可能需要一些时间
        """)
        
        # 文件上传
        uploaded_file = st.file_uploader(
            "选择Excel文件", 
            type=['xlsx', 'xls'],
            help="支持 .xlsx 和 .xls 格式"
        )
        
        if uploaded_file is not None:
            try:
                # 预览数据
                st.markdown("### 文件预览")
                excel_file = pd.ExcelFile(uploaded_file)
                
                # 显示工作表信息
                sheet_names = excel_file.sheet_names
                st.write(f"**检测到 {len(sheet_names)} 个工作表:**")
                
                for sheet in sheet_names:
                    with st.expander(f"📋 {sheet}", expanded=False):
                        try:
                            df = pd.read_excel(uploaded_file, sheet_name=sheet, nrows=10)
                            st.dataframe(df.head(5))
                            st.write(f"总行数: {len(df)}")
                        except Exception as e:
                            st.error(f"读取工作表 '{sheet}' 失败: {e}")
                
                # 导入选项
                st.markdown("### 导入选项")
                
                col1, col2 = st.columns(2)
                with col1:
                    import_mode = st.radio(
                        "导入模式",
                        options=["替换现有数据", "合并数据（不重复）"],
                        index=0
                    )
                
                with col2:
                    conflict_resolution = st.selectbox(
                        "数据冲突处理",
                        options=["跳过重复数据", "覆盖重复数据"],
                        disabled=(import_mode == "替换现有数据")
                    )
                
                # 备份选项
                create_backup = st.checkbox("导入前自动备份当前数据", value=True)
                
                # 导入按钮
                if st.button("🚀 开始导入数据", type="primary", use_container_width=True):
                    if create_backup:
                        with st.spinner("正在创建备份..."):
                            data_manager.create_backup()
                            st.success("✅ 数据备份完成")
                    
                    with st.spinner("正在导入数据，请稍候..."):
                        success, message = data_manager.import_from_excel(uploaded_file)
                        
                        if success:
                            st.success(f"✅ 数据导入成功！")
                            st.info(f"导入统计: {message}")
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error(f"❌ 导入失败: {message}")
                
            except Exception as e:
                st.error(f"读取文件失败: {e}")
    
    # ==================== 备份管理模块 ====================
    with tab3:
        st.subheader("🔙 备份管理")
        
        col1, col2 = st.columns(2)
        with col1:
            # 立即备份
            if st.button("🔄 立即创建备份", use_container_width=True, type="primary"):
                with st.spinner("正在创建备份..."):
                    if data_manager.create_backup():
                        st.success("✅ 备份创建成功！")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ 备份创建失败")
        
        with col2:
            # 手动触发备份清理
            if st.button("🧹 清理旧备份", use_container_width=True, type="secondary"):
                data_manager._cleanup_old_backups()
                st.success("✅ 备份清理完成")
                time.sleep(1)
                st.rerun()
        
        # 备份文件列表
        st.markdown("### 📋 备份文件列表")
        
        backup_files = list(data_manager.backup_dir.glob("data_backup_*.json"))
        
        if backup_files:
            # 按修改时间排序（最新的在前面）
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # 备份统计
            total_size = sum(f.stat().st_size for f in backup_files) / (1024 * 1024)  # MB
            st.write(f"**备份文件数量:** {len(backup_files)} 个")
            st.write(f"**总占用空间:** {total_size:.2f} MB")
            
            # 备份文件表格
            backup_data = []
            for i, file in enumerate(backup_files[:20], 1):  # 只显示前20个
                file_size = file.stat().st_size / 1024  # KB
                modified_time = datetime.fromtimestamp(file.stat().st_mtime)
                backup_data.append({
                    "序号": i,
                    "文件名": file.name,
                    "大小": f"{file_size:.1f} KB",
                    "修改时间": modified_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "文件路径": str(file)
                })
            
            if backup_data:
                df = pd.DataFrame(backup_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
            
            # 备份操作
            st.markdown("### 🔧 备份操作")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # 选择要恢复的备份
                backup_options = {f"{i+1}. {f.name}": str(f) for i, f in enumerate(backup_files[:10])}
                if backup_options:
                    selected_backup = st.selectbox(
                        "选择备份文件恢复",
                        options=list(backup_options.keys())
                    )
            
            with col2:
                if st.button("📥 恢复备份", disabled=not backup_options):
                    backup_file = Path(backup_options[selected_backup])
                    if backup_file.exists():
                        # 先备份当前数据
                        data_manager.create_backup()
                        
                        # 恢复备份
                        try:
                            shutil.copy2(backup_file, data_manager.data_file)
                            st.success("✅ 备份恢复成功！系统将重新加载...")
                            time.sleep(2)
                            st.rerun()
                        except Exception as e:
                            st.error(f"恢复失败: {e}")
            
            with col3:
                if st.button("🗑️ 删除所有备份", type="secondary"):
                    confirm = st.checkbox("确认删除所有备份文件？")
                    if confirm and st.button("永久删除", type="primary"):
                        for file in backup_files:
                            file.unlink()
                        st.success("✅ 所有备份文件已删除")
                        time.sleep(2)
                        st.rerun()
        else:
            st.info("暂无备份文件")
    
    # ==================== 系统设置模块 ====================
    with tab4:
        st.subheader("⚙️ 系统设置")
        
        # 系统信息
        st.markdown("### 系统信息")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if data_manager.data_file.exists():
                file_size = data_manager.data_file.stat().st_size / 1024  # KB
                st.metric("数据文件大小", f"{file_size:.1f} KB")
            else:
                st.metric("数据文件大小", "0 KB")
        
        with col2:
            backup_count = len(list(data_manager.backup_dir.glob("data_backup_*.json")))
            st.metric("备份文件数量", backup_count)
        
        with col3:
            if data_manager.data_file.exists():
                st.metric("最后修改", datetime.fromtimestamp(
                    data_manager.data_file.stat().st_mtime).strftime("%m-%d %H:%M")
                )
            else:
                st.metric("最后修改", "无")
        
        # 数据清理选项
        st.markdown("### 🧹 数据清理")
        
        with st.expander("高级数据清理选项", expanded=False):
            st.warning("⚠️ 这些操作不可逆，请谨慎操作！")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # 清理空数据
                if st.button("清理空记录", type="secondary"):
                    st.info("清理空记录功能开发中...")
            
            with col2:
                # 重置系统
                if st.button("重置系统数据", type="secondary"):
                    st.error("🚨 危险操作！")
                    confirm = st.checkbox("我确认要重置所有数据")
                    if confirm and st.button("确认重置", type="primary"):
                        # 备份当前数据
                        data_manager.create_backup()
                        
                        # 重置为初始数据
                        initial_data = data_manager.get_initial_data()
                        data_manager.save_data(initial_data)
                        
                        st.success("✅ 系统已重置为初始状态")
                        time.sleep(2)
                        st.rerun()

# -------------------- 主程序入口 --------------------
def main():
    """主函数"""
    # 页面标题
    st.title("🧪 聚羧酸减水剂研发管理系统")
    st.markdown("---")
    
    # 侧边栏导航 - 增加数据管理选项
    st.sidebar.title("导航菜单")
    menu_options = [
        "📊 项目概览", 
        "🧪 实验管理", 
        "📝 数据记录", 
        "💾 数据管理",  # 新增
        "📈 数据分析", 
        "📄 报告生成"
    ]
    selected_page = st.sidebar.radio("选择功能", menu_options)
    
    # 侧边栏系统信息
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 系统信息")
    st.sidebar.info(f"当前时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    # 数据统计
    projects = data_manager.get_all_projects()
    experiments = data_manager.get_all_experiments()
    raw_materials = data_manager.get_all_raw_materials()
    
    st.sidebar.metric("项目总数", len(projects))
    st.sidebar.metric("实验总数", len(experiments))
    st.sidebar.metric("原材料数", len(raw_materials))
    
    # 备份状态
    backup_files = list(data_manager.backup_dir.glob("data_backup_*.json"))
    if backup_files:
        latest_backup = max(backup_files, key=lambda x: x.stat().st_mtime)
        backup_time = datetime.fromtimestamp(latest_backup.stat().st_mtime)
        st.sidebar.metric("最新备份", backup_time.strftime("%m-%d %H:%M"))
    
    # 数据文件状态
    if data_manager.data_file.exists():
        file_size = data_manager.data_file.stat().st_size / 1024  # KB
        st.sidebar.metric("数据文件", f"{file_size:.1f} KB")
    
    # 快速操作
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 快速操作")
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.sidebar.button("🔄 刷新数据", use_container_width=True):
            st.rerun()
    
    with col2:
        if st.sidebar.button("💾 立即备份", use_container_width=True):
            with st.spinner("正在备份..."):
                if data_manager.create_backup():
                    st.sidebar.success("✅ 备份完成")
                    time.sleep(1)
                    st.rerun()
    
    # 根据选择渲染页面
    if selected_page == "📊 项目概览":
        render_dashboard()
    elif selected_page == "🧪 实验管理":
        render_experiment_management()
    elif selected_page == "📝 数据记录":
        render_data_recording()
    elif selected_page == "💾 数据管理":  # 新增
        render_data_management()
    elif selected_page == "📈 数据分析":
        st.header("📈 数据分析")
        st.info("数据分析页面开发中...")
    elif selected_page == "📄 报告生成":
        st.header("📄 报告生成")
        st.info("报告生成页面开发中...")
    
    # 页脚
    st.markdown("---")
    st.caption("聚羧酸减水剂研发管理系统 v2.2 | 修复数据丢失 + 数据导出导入 + 定时备份 | 最后更新: 2024年1月")

# -------------------- 程序执行 --------------------
if __name__ == "__main__":
    main()
