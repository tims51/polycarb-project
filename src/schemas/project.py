from typing import Optional, Union
from datetime import date, datetime
from pydantic import Field, field_validator

from core.enums import ProjectStatus, ExperimentType, ExperimentStatus
from .base import BaseSchema, DBModel

# ---------------------- Project Models ----------------------

class ProjectBase(BaseSchema):
    name: str = Field(..., description="项目名称")
    leader: str = Field(..., description="项目负责人")
    start_date: Union[date, str] = Field(..., description="开始日期")
    end_date: Union[date, str] = Field(..., description="结束日期")
    description: Optional[str] = Field("", description="项目描述")

    @field_validator('start_date', 'end_date', mode='before')
    @classmethod
    def parse_date(cls, v):
        if isinstance(v, str):
            try:
                return datetime.strptime(v, "%Y-%m-%d").date()
            except ValueError:
                return v
        return v

class ProjectCreate(ProjectBase):
    """创建项目时不需要 ID 和状态"""
    pass

class Project(ProjectBase, DBModel):
    """完整的项目模型"""
    status: ProjectStatus = Field(default=ProjectStatus.IN_PROGRESS, description="项目状态")
    progress: float = Field(default=0.0, ge=0, le=100, description="项目进度 (0-100)")

# ---------------------- Experiment Models ----------------------

class ExperimentBase(BaseSchema):
    name: str = Field(..., description="实验名称")
    type: ExperimentType = Field(..., description="实验类型")
    project_id: int = Field(..., description="关联的项目ID")
    planned_date: Union[date, str] = Field(..., description="计划日期")
    actual_date: Optional[Union[date, str]] = Field(None, description="实际日期")
    priority: str = Field("中", description="优先级")
    description: Optional[str] = Field("", description="实验描述")

    @field_validator('planned_date', 'actual_date', mode='before')
    @classmethod
    def parse_date(cls, v):
        if isinstance(v, str) and v:
            try:
                return datetime.strptime(v, "%Y-%m-%d").date()
            except ValueError:
                return v
        return v

class ExperimentCreate(ExperimentBase):
    pass

class Experiment(ExperimentBase, DBModel):
    status: ExperimentStatus = Field(default=ExperimentStatus.PLANNED, description="实验状态")
