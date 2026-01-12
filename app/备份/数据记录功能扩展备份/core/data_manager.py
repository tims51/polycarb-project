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

class DataManager:
    """统一数据管理器"""
    
    def __init__(self):
        self.data_file = Path(__file__).parent.parent / "data.json"
        self.backup_dir = Path(__file__).parent.parent / "backups"
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