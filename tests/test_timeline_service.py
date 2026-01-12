
import pytest
from datetime import date, timedelta
from app.services.timeline_service import TimelineService

def test_timeline_calculation_valid():
    """Test valid timeline calculation."""
    start = date.today() - timedelta(days=10)
    end = date.today() + timedelta(days=10)
    
    project = {
        "start_date": start.strftime("%Y-%m-%d"),
        "end_date": end.strftime("%Y-%m-%d")
    }
    
    timeline = TimelineService.calculate_timeline(project)
    
    assert timeline["is_valid"] is True
    assert timeline["total_days"] == 20
    assert timeline["passed_days"] == 10
    assert 49 < timeline["percent"] < 51
    assert timeline["status"] == "进行中"

def test_timeline_calculation_completed():
    """Test completed project timeline."""
    start = date.today() - timedelta(days=20)
    end = date.today() - timedelta(days=10)
    
    project = {
        "start_date": start.strftime("%Y-%m-%d"),
        "end_date": end.strftime("%Y-%m-%d")
    }
    
    timeline = TimelineService.calculate_timeline(project)
    
    assert timeline["status"] == "已完成"
    assert timeline["percent"] == 100

def test_timeline_calculation_not_started():
    """Test not started project timeline."""
    start = date.today() + timedelta(days=10)
    end = date.today() + timedelta(days=20)
    
    project = {
        "start_date": start.strftime("%Y-%m-%d"),
        "end_date": end.strftime("%Y-%m-%d")
    }
    
    timeline = TimelineService.calculate_timeline(project)
    
    assert timeline["status"] == "尚未开始"
    assert timeline["percent"] == 0

def test_timeline_invalid_dates():
    """Test invalid dates."""
    project = {
        "start_date": "2024-01-01",
        "end_date": "2023-01-01"  # End before start
    }
    
    timeline = TimelineService.calculate_timeline(project)
    
    assert timeline["is_valid"] is False
    assert "结束日期早于" in timeline["error_reason"]
