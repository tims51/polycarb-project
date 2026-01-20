
"""
Timeline Service Module
Handles project timeline calculations and management.
"""

from core.timeline_manager import TimelineManager
from core.models import TimelineInfo, Project
from typing import Dict, Any, Union, List, Optional
from datetime import date, datetime
from bisect import bisect_left, bisect_right
import logging

logger = logging.getLogger(__name__)

class TimelineService:
    """Service for handling project timeline calculations and queries."""
    
    def __init__(self, data_service=None):
        """
        Initialize TimelineService.
        Args:
            data_service: Optional DataService instance for querying projects.
        """
        self.data_service = data_service
    
    @staticmethod
    def calculate_timeline(project_data: Union[Dict[str, Any], Project]) -> TimelineInfo:
        """
        Calculate timeline information for a project.
        Delegates to core.timeline_manager.TimelineManager.
        """
        return TimelineManager.calculate_timeline(project_data)
    
    @staticmethod
    def _create_invalid_timeline(reason: str = "") -> TimelineInfo:
        return TimelineManager._create_invalid_timeline(reason)
    
    @staticmethod
    def get_timeline_summary(timeline_info: Dict[str, Any]) -> str:
        """Get a text summary of the timeline."""
        # Check if timeline_info is a dict or object (handle both for compatibility)
        is_valid = timeline_info.get('is_valid') if isinstance(timeline_info, dict) else getattr(timeline_info, 'is_valid', False)
        
        if not is_valid:
            return "时间线信息不可用"
        
        if isinstance(timeline_info, dict):
            status = timeline_info.get('status', '未知')
            passed = timeline_info.get('passed_days', 0)
            total = timeline_info.get('total_days', 1)
            percent = timeline_info.get('percent', 0)
            start_date = timeline_info.get('start_date')
        else:
            status = getattr(timeline_info, 'status', '未知')
            passed = getattr(timeline_info, 'passed_days', 0)
            total = getattr(timeline_info, 'total_days', 1)
            percent = getattr(timeline_info, 'percent', 0)
            start_date = getattr(timeline_info, 'start_date', None)
        
        if status == "尚未开始" or status == "not_started":
            date_str = start_date.strftime('%Y-%m-%d') if start_date else "?"
            return f"项目尚未开始 ({date_str})"
        elif status == "已完成" or status == "completed":
            return f"项目已完成 ({passed}/{total}天)"
        else:  # 进行中
            remaining = total - passed
            return f"进行中: {passed}/{total}天 ({percent:.1f}%), 剩余{remaining}天"

    def get_projects_in_time_range(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """
        Efficiently query projects that are active within the specified date range.
        Uses binary search on sorted start dates to reduce search space.
        
        Args:
            start_date: Query start date
            end_date: Query end date
            
        Returns:
            List of project dictionaries
        """
        if not self.data_service:
            logger.warning("DataService not initialized in TimelineService")
            return []
            
        all_projects = self.data_service.get_all_projects()
        if not all_projects:
            return []
            
        # Optimization:
        # 1. Sort projects by start_date (cache this if possible, here we assume it's fast enough or cached in DataService)
        # For true binary search, list must be sorted.
        # We sort a list of (start_date, project) tuples.
        
        # Pre-process dates: ensure they are date objects
        sorted_projects = []
        for p in all_projects:
            p_start = p.get('start_date')
            if isinstance(p_start, str):
                try:
                    p_start = datetime.strptime(p_start, "%Y-%m-%d").date()
                except:
                    continue
            if p_start:
                sorted_projects.append((p_start, p))
        
        # Sort by start date
        sorted_projects.sort(key=lambda x: x[0])
        
        # Extract keys for bisect
        keys = [x[0] for x in sorted_projects]
        
        # Binary search
        # We want projects where:
        # project.start_date <= query.end_date AND project.end_date >= query.start_date
        
        # Optimization: First, find projects that started BEFORE query.end_date
        # bisect_right returns insertion point after (so all items to left are <= end_date)
        right_idx = bisect_right(keys, end_date)
        
        # Now we only need to check projects up to right_idx
        # Filter strictly for the overlap condition: project.end_date >= query.start_date
        result = []
        for i in range(right_idx):
            p_start, project = sorted_projects[i]
            p_end = project.get('end_date')
            
            if isinstance(p_end, str):
                try:
                    p_end = datetime.strptime(p_end, "%Y-%m-%d").date()
                except:
                    continue
            
            if p_end and p_end >= start_date:
                result.append(project)
                
        return result
