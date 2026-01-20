from enum import Enum

class ProjectStatus(str, Enum):
    NOT_STARTED = "尚未开始"
    IN_PROGRESS = "进行中"
    COMPLETED = "已完成"

class ExperimentStatus(str, Enum):
    PLANNED = "计划中"
    IN_PROGRESS = "进行中"
    COMPLETED = "已完成"
    CANCELLED = "已取消"

class ExperimentType(str, Enum):
    SYNTHESIS = "合成实验"
    PASTE = "净浆实验"
    MORTAR = "砂浆实验"
    CONCRETE = "混凝土实验"

class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"

class MaterialType(str, Enum):
    RAW_MATERIAL = "raw_material"
    PRODUCT = "product"

class IssueStatus(str, Enum):
    DRAFT = "draft"
    POSTED = "posted"
    CANCELLED = "cancelled"

class ReceiptStatus(str, Enum):
    DRAFT = "draft"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class ShippingStatus(str, Enum):
    DRAFT = "draft"
    SHIPPED = "shipped"
    CANCELLED = "cancelled"

class PermissionAction(str, Enum):
    VIEW_DASHBOARD = "view_dashboard"
    MANAGE_EXPERIMENTS = "manage_experiments"
    MANAGE_RAW_MATERIALS = "manage_raw_materials"
    VIEW_ANALYSIS = "view_analysis"
    MANAGE_BOM = "manage_bom"
    MANAGE_INVENTORY = "manage_inventory"
    MANAGE_DATA = "manage_data"
    MANAGE_USERS = "manage_users"

class StockMovementType(str, Enum):
    IN = "in"
    OUT = "out"
    RETURN_IN = "return_in"
    RETURN_OUT = "return_out"
    ADJUSTMENT = "adjustment"
    PRODUCE_IN = "produce_in"
    CONSUME_OUT = "consume_out"
    ADJUST_IN = "adjust_in"
    ADJUST_OUT = "adjust_out"
    SHIP_OUT = "ship_out"

class MotherLiquorSourceType(str, Enum):
    SYNTHESIS = "synthesis"
    PRODUCTION = "production"
    EXTERNAL = "external"

class BOMStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    REJECTED = "rejected"
    ARCHIVED = "archived"

class ProductionOrderStatus(str, Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"
    CANCELLED = "cancelled"

class ProductCategory(str, Enum):
    MOTHER_LIQUOR = "母液"
    ACCELERATOR = "速凝剂"
    ANTIFREEZE = "防冻剂"
    WATER_REDUCER = "减水剂"
    OTHER = "其他"

class UnitType(str, Enum):
    TON = "吨"
    KG = "kg"
    GRAM = "g"
    LITER = "L"

class PriorityType(str, Enum):
    HIGH = "高"
    MEDIUM = "中"
    LOW = "低"

class DataCategory(str, Enum):
    PROJECTS = "projects"
    EXPERIMENTS = "experiments"
    PERFORMANCE_DATA = "performance_data"
    RAW_MATERIALS = "raw_materials"
    SYNTHESIS_RECORDS = "synthesis_records"
    PRODUCTS = "products"
    PASTE_EXPERIMENTS = "paste_experiments"
    MORTAR_EXPERIMENTS = "mortar_experiments"
    CONCRETE_EXPERIMENTS = "concrete_experiments"
    GOODS_RECEIPTS = "goods_receipts"
    SHIPPING_ORDERS = "shipping_orders"
    INVENTORY_RECORDS = "inventory_records"
    PRODUCTION_ORDERS = "production_orders"
    BOMS = "boms"
    BOM_VERSIONS = "bom_versions"
    MOTHER_LIQUORS = "mother_liquors"
    MATERIAL_ISSUES = "material_issues"
    USERS = "users"
    AUDIT_LOGS = "audit_logs"
    PRODUCT_INVENTORY = "product_inventory"
    PRODUCT_INVENTORY_RECORDS = "product_inventory_records"

class StatusEmoji(str, Enum):
    WAITING = "⏳"
    COMPLETED = "✅"
    CALENDAR = "📅"
    UNKNOWN = "❓"
