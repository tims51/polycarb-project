from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

class BaseSchema(BaseModel):
    """
    基础模型，配置了 Pydantic V2 的通用设置
    """
    model_config = ConfigDict(
        populate_by_name=True, 
        from_attributes=True,  # 相当于 V1 的 orm_mode=True
        extra='ignore'         # 忽略多余字段
    )

class DBModel(BaseSchema):
    """
    数据库模型基类，强制包含 id 和 created_at
    """
    id: int = Field(..., description="唯一标识符，必须为整数")
    created_at: Optional[str] = Field(None, description="创建时间 (YYYY-MM-DD HH:MM:SS)")
