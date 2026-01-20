from services.data_service import DataService
from services.auth_service import AuthService
from services.inventory_service import InventoryService
from services.bom_service import BOMService

class ServiceContainer:
    """
    服务容器 (Service Container)
    负责初始化并管理所有业务服务实例，实现依赖注入。
    """
    def __init__(self):
        # 1. 初始化核心数据服务 (Core Data Layer)
        # DataService 负责底层 JSON 文件的读写与原子操作
        self.data_service = DataService()
        
        # 2. 初始化业务逻辑服务 (Business Logic Layer)
        # 通过构造函数注入 data_service，确保所有服务共享同一个数据访问层
        
        # 用户认证服务
        self.auth_service = AuthService(self.data_service)
        
        # 库存管理服务 (原材料 + 成品)
        self.inventory_service = InventoryService(self.data_service)
        
        # BOM 配方服务
        self.bom_service = BOMService(self.data_service)
