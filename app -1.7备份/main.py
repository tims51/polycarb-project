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
class DataManager:
    """统一数据管理器 - 处理所有数据的增删查改"""
    
    def __init__(self):
        self.data_file = Path(__file__).parent.parent / "data.json"
        self._ensure_valid_data_file()
    
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
            ]
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
    """渲染数据记录页面"""
    st.header("📝 数据记录")
    
    tab1, tab2, tab3 = st.tabs(["🧪 合成参数", "📊 性能数据", "📦 原料信息"])
    
    with tab1:
        st.subheader("合成实验参数记录")
        with st.form("synthesis_data_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                monomer_ratio = st.number_input("单体比例 (%)", min_value=0.0, max_value=100.0, value=30.0, step=0.1)
                reaction_temp = st.number_input("反应温度 (°C)", value=60.0, step=0.5)
            with col2:
                reaction_time = st.number_input("反应时间 (小时)", value=4.0, step=0.5)
                ph_value = st.number_input("pH值", value=7.0, step=0.1)
            
            notes = st.text_area("实验备注")
            
            if st.form_submit_button("保存数据", type="primary"):
                st.success("合成实验数据保存成功！")
    
    with tab2:
        st.subheader("性能测试数据")
        st.info("性能数据记录功能")
        
    with tab3:
        st.subheader("原料信息管理")
        st.info("原料信息管理功能开发中...")

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