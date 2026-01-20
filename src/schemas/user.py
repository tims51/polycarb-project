from typing import Optional
from pydantic import Field

from core.enums import UserRole
from .base import BaseSchema, DBModel

class UserLogin(BaseSchema):
    """用户登录模型"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")

class UserCreate(UserLogin):
    """用户创建模型"""
    role: UserRole = Field(default=UserRole.USER, description="角色")

class UserResponse(BaseSchema):
    """用户响应模型 (不包含密码)"""
    username: str
    role: UserRole
    created_at: Optional[str] = None
    last_login: Optional[str] = None
    
    # 允许从 User DB模型 (含 password_hash) 转换，自动忽略 password 字段
