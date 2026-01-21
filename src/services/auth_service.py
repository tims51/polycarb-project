import hashlib
import secrets
from datetime import datetime
from typing import Optional, Tuple, Dict, Any

from schemas.user import UserCreate, UserLogin, UserResponse
from core.enums import UserRole, DataCategory
from services.data_service import DataService

class AuthService:
    def __init__(self, data_service: DataService = None):
        self.data_service = data_service or DataService()

    def _hash_password(self, password: str, salt: str) -> str:
        value = f"{salt}:{password}".encode("utf-8")
        return hashlib.sha256(value).hexdigest()

    def create_user(self, user_data: UserCreate) -> Tuple[bool, str]:
        username = user_data.username.strip()
        password = user_data.password
        role = user_data.role

        if not username or not password:
            return False, "用户名和密码不能为空"
        
        # 简单校验
        if role != UserRole.ADMIN:
            parts = username.split()
            if len(parts) != 2:
                return False, "用户名格式应为“姓名 手机号”"
            name, mobile = parts[0], parts[1]
            if not mobile.isdigit() or len(mobile) != 11 or not mobile.startswith("1"):
                return False, "手机号格式不正确，请输入11位手机号码"

        # Check existence
        existing_user = self.get_user_by_username(username)
        if existing_user:
            return False, "用户名已存在"

        data = self.data_service.load_data()
        users = data.get(DataCategory.USERS.value, [])
        
        # Use DataService's safe ID generation
        new_id = self.data_service._get_next_id(users)
        
        salt = secrets.token_hex(16)
        pwd_hash = self._hash_password(password, salt)
        
        new_user = {
            "id": new_id,
            "username": username,
            "password_hash": pwd_hash,
            "salt": salt,
            "role": role.value if hasattr(role, 'value') else role,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "active": True
        }
        
        users.append(new_user)
        data[DataCategory.USERS.value] = users
        
        if self.data_service.save_data(data):
            return True, "注册成功"
        return False, "保存失败"

    def authenticate_user(self, login_data: UserLogin) -> Tuple[bool, Optional[UserResponse]]:
        user = self.get_user_by_username(login_data.username)
        if not user or not user.get("active", True):
            return False, None
            
        salt = user.get("salt", "")
        expected = user.get("password_hash", "")
        calc = self._hash_password(login_data.password, salt)
        
        if secrets.compare_digest(calc, expected):
            # Return UserResponse (safe model)
            return True, UserResponse(
                username=user.get("username"),
                role=user.get("role", UserRole.USER.value),
                created_at=user.get("created_at"),
                last_login=datetime.now().strftime("%Y-%m-%d %H:%M:%S") # Note: updating last_login might require a write, skipping for now or adding a separate update
            )
        return False, None

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        username = str(username or "").strip().lower()
        users = self.data_service._get_items(DataCategory.USERS.value)
        for u in users:
            if str(u.get("username", "")).strip().lower() == username:
                return u
        return None

    def ensure_default_admin(self):
        """确保默认管理员存在"""
        users = self.data_service._get_items(DataCategory.USERS.value)
        if not users:
            # Create default admin
            # Use internal method to avoid recursive checks or strict validations if any
            # But calling create_user is safer if I mock UserCreate
            from schemas.user import UserCreate
            admin_data = UserCreate(username="admin", password="admin123", role="admin")
            self.create_user(admin_data)

    def get_all_users(self) -> list[dict]:
        data = self.data_service.load_data()
        return data.get(DataCategory.USERS.value, [])

    def get_admin_users(self) -> list[dict]:
        users = self.get_all_users()
        return [u for u in users if str(u.get("role", UserRole.USER.value)) == UserRole.ADMIN.value and u.get("active", True)]

    def change_user_password(self, user_id: int, old_password: str, new_password: str) -> tuple[bool, str]:
        data = self.data_service.load_data()
        users = data.get(DataCategory.USERS.value, [])
        idx = -1
        for i, u in enumerate(users):
            if u.get("id") == user_id:
                idx = i
                break
        if idx == -1:
            return False, "用户不存在"
        user = users[idx]
        salt = user.get("salt", "")
        expected = user.get("password_hash", "")
        if not salt or not expected:
            return False, "当前密码校验失败"
        calc = self._hash_password(old_password, salt)
        if not secrets.compare_digest(calc, expected):
            return False, "当前密码错误"
        new_salt = secrets.token_hex(16)
        new_hash = self._hash_password(new_password, new_salt)
        user["salt"] = new_salt
        user["password_hash"] = new_hash
        users[idx] = user
        data[DataCategory.USERS.value] = users
        if self.data_service.save_data(data):
            return True, "登录密码已更新"
        return False, "保存失败"

    def update_user(self, user_id: int, fields: dict) -> bool:
        data = self.data_service.load_data()
        users = data.get(DataCategory.USERS.value, [])
        updated = False
        for i, u in enumerate(users):
            if u.get("id") == user_id:
                users[i].update(fields)
                updated = True
                break
        if updated:
            data[DataCategory.USERS.value] = users
            return self.data_service.save_data(data)
        return False
