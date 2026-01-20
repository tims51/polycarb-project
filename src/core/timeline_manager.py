"""时间线管理模块"""

from datetime import datetime, timedelta

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
                'is_ahead': False
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