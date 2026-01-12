
"""
Timeline Service Module
Handles project timeline calculations and management.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class TimelineService:
    """Service for handling project timeline calculations."""
    
    @staticmethod
    def calculate_timeline(project_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate timeline information for a project.
        
        Args:
            project_data: Dictionary containing project details with start_date and end_date.
            
        Returns:
            Dictionary containing timeline statistics and status.
        """
        try:
            # Extract date information
            start_date_str = project_data.get('start_date', '')
            end_date_str = project_data.get('end_date', '')
            
            # Validate necessary data
            if not start_date_str or not end_date_str:
                return TimelineService._create_invalid_timeline("缺少日期信息")
            
            # Parse dates
            try:
                start_date = datetime.strptime(str(start_date_str), "%Y-%m-%d").date()
                end_date = datetime.strptime(str(end_date_str), "%Y-%m-%d").date()
            except ValueError:
                # Try parsing if it's already a date object or different format if needed
                # For now assume string format or fail
                 return TimelineService._create_invalid_timeline("日期格式无效")

            today = datetime.now().date()
            
            # Validate logic
            if end_date <= start_date:
                return TimelineService._create_invalid_timeline("结束日期早于或等于开始日期")
            
            # Calculate basics
            total_days = (end_date - start_date).days
            passed_days = max(0, min((today - start_date).days, total_days))
            
            # Determine status
            if today < start_date:
                status = "尚未开始"
                status_emoji = "⏳"
                percent = 0.0
            elif today > end_date:
                status = "已完成"
                status_emoji = "✅"
                percent = 100.0
                passed_days = total_days
            else:
                status = "进行中"
                status_emoji = "📅"
                percent = (passed_days / total_days) * 100
            
            # Calculate estimated completion
            estimated_completion = None
            if 0 < percent < 100:
                remaining_days = total_days - passed_days
                estimated_completion = today + timedelta(days=remaining_days)
            
            # Construct timeline info object
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
            
        except Exception as e:
            logger.error(f"Error calculating timeline: {e}")
            return TimelineService._create_invalid_timeline(f"计算错误: {e}")
    
    @staticmethod
    def _create_invalid_timeline(reason: str = "") -> Dict[str, Any]:
        """Create an invalid timeline info object."""
        return {
            'is_valid': False,
            'error_reason': reason,
            'status': '未知',
            'status_emoji': '❓',
            'percent': 0.0,
            'passed_days': 0,
            'total_days': 0,
            'today': datetime.now().date()
        }
    
    @staticmethod
    def get_timeline_summary(timeline_info: Dict[str, Any]) -> str:
        """Get a text summary of the timeline."""
        if not timeline_info.get('is_valid'):
            return "时间线信息不可用"
        
        status = timeline_info.get('status', '未知')
        passed = timeline_info.get('passed_days', 0)
        total = timeline_info.get('total_days', 1)
        percent = timeline_info.get('percent', 0)
        
        if status == "尚未开始":
            start_date = timeline_info.get('start_date')
            date_str = start_date.strftime('%Y-%m-%d') if start_date else "?"
            return f"项目尚未开始 ({date_str})"
        elif status == "已完成":
            return f"项目已完成 ({passed}/{total}天)"
        else:  # 进行中
            remaining = total - passed
            return f"进行中: {passed}/{total}天 ({percent:.1f}%), 剩余{remaining}天"
