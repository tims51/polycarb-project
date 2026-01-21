"""时间线管理模块"""

from datetime import datetime, timedelta, date
from typing import Union, Dict, Any, Optional
from .models import Project, TimelineInfo
from .enums import ProjectStatus, StatusEmoji
from .constants import DATE_FORMAT

class TimelineManager:
    """专门处理项目时间线计算和管理的类"""
    
    @staticmethod
    def calculate_timeline(project_data: Union[Dict[str, Any], Project]) -> TimelineInfo:
        """
        计算项目时间线信息
        返回：时间线信息对象
        """
        try:
            # 转换为 Pydantic 模型
            if isinstance(project_data, dict):
                try:
                    project = Project(**project_data)
                except Exception as e:
                    return TimelineManager._create_invalid_timeline(f"数据格式错误: {e}")
            else:
                project = project_data

            # 提取日期信息
            start_date = project.start_date
            end_date = project.end_date
            
            # 验证必要数据
            if not start_date or not end_date:
                return TimelineManager._create_invalid_timeline("缺少日期信息")
            
            # 转换为 date 对象 (如果还是字符串的话，虽然模型应该已经处理了)
            if isinstance(start_date, str):
                start_date = datetime.strptime(start_date, DATE_FORMAT).date()
            if isinstance(end_date, str):
                end_date = datetime.strptime(end_date, DATE_FORMAT).date()
                
            today = datetime.now().date()
            
            # 验证日期逻辑
            if end_date <= start_date:
                return TimelineManager._create_invalid_timeline("结束日期早于或等于开始日期")
            
            # 计算基础信息
            total_days = (end_date - start_date).days
            passed_days = max(0, min((today - start_date).days, total_days))
            
            # 确定项目状态
            if today < start_date:
                status = ProjectStatus.NOT_STARTED
                status_emoji = StatusEmoji.WAITING.value
                percent = 0.0
            elif today > end_date:
                status = ProjectStatus.COMPLETED
                status_emoji = StatusEmoji.COMPLETED.value
                percent = 100.0
                passed_days = total_days
            else:
                status = ProjectStatus.IN_PROGRESS
                status_emoji = StatusEmoji.CALENDAR.value
                percent = (passed_days / total_days) * 100
            
            # 计算预计完成时间
            estimated_completion: Optional[date] = None
            if 0 < percent < 100:
                remaining_days = total_days - passed_days
                estimated_completion = today + timedelta(days=remaining_days)
            
            # 构建时间线信息对象
            return TimelineInfo(
                is_valid=True,
                status=status.value if hasattr(status, 'value') else status,
                status_emoji=status_emoji,
                percent=percent,
                passed_days=passed_days,
                total_days=total_days,
                start_date=start_date,
                end_date=end_date,
                today=today,
                estimated_completion=estimated_completion,
                remaining_days=total_days - passed_days if percent < 100 else 0,
                is_delayed=today > end_date and percent < 100,
                is_ahead=False
            )
            
        except ValueError as e:
            return TimelineManager._create_invalid_timeline(f"日期格式错误: {e}")
        except Exception as e:
            return TimelineManager._create_invalid_timeline(f"计算错误: {e}")
    
    @staticmethod
    def _create_invalid_timeline(reason: str = "") -> TimelineInfo:
        """创建无效时间线信息"""
        return TimelineInfo(
            is_valid=False,
            error_reason=reason,
            status='未知',
            status_emoji=StatusEmoji.UNKNOWN.value,
            percent=0.0,
            passed_days=0,
            total_days=0,
            today=datetime.now().date()
        )
    
    @staticmethod
    def get_timeline_summary(timeline_info: TimelineInfo) -> str:
        """获取时间线摘要文本"""
        if not timeline_info.is_valid:
            return "时间线信息不可用"
        
        status = timeline_info.status
        passed = timeline_info.passed_days
        total = timeline_info.total_days
        percent = timeline_info.percent
        
        if status == ProjectStatus.NOT_STARTED.value:
            return f"项目尚未开始 ({timeline_info.start_date.strftime(DATE_FORMAT)})"
        elif status == ProjectStatus.COMPLETED.value:
            return f"项目已完成 ({passed}/{total}天)"
        else:  # 进行中
            remaining = total - passed
            return f"进行中: {passed}/{total}天 ({percent:.1f}%), 剩余{remaining}天"
    
    @staticmethod
    def is_project_active(timeline_info: TimelineInfo) -> bool:
        """检查项目是否处于活跃状态（进行中或即将开始）"""
        if not timeline_info.is_valid:
            return False
        
        status = timeline_info.status
        return status in [ProjectStatus.IN_PROGRESS.value, ProjectStatus.NOT_STARTED.value]
