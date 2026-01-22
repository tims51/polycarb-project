from typing import List, Optional, Dict, Any, Union
from datetime import date as DateType, datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict
from .enums import ProjectStatus, ExperimentStatus, ExperimentType, UserRole, MotherLiquorSourceType, StockMovementType, BOMStatus, ProductionOrderStatus, IssueStatus, ProductCategory, ReceiptStatus, ShippingStatus, UnitType, MaterialType
from config import DEFAULT_UNIT
from .constants import DEFAULT_UNIT_KG, DEFAULT_UNIT_TON

class BaseModelWithConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

class Project(BaseModelWithConfig):
    id: int
    name: str
    leader: str
    start_date: Union[DateType, str]
    end_date: Union[DateType, str]
    status: ProjectStatus = ProjectStatus.IN_PROGRESS
    progress: float = Field(default=0.0, ge=0, le=100)
    description: Optional[str] = ""

    @field_validator('start_date', 'end_date', mode='before')
    @classmethod
    def parse_date(cls, v):
        if isinstance(v, str):
            try:
                return datetime.strptime(v, "%Y-%m-%d").date()
            except ValueError:
                return v
        return v

class Experiment(BaseModelWithConfig):
    id: int
    name: str
    type: ExperimentType
    project_id: int
    planned_date: Union[DateType, str]
    actual_date: Optional[Union[DateType, str]] = None
    priority: str = "中"
    status: ExperimentStatus = ExperimentStatus.PLANNED
    description: Optional[str] = ""

    @field_validator('planned_date', 'actual_date', mode='before')
    @classmethod
    def parse_date(cls, v):
        if isinstance(v, str):
            try:
                return datetime.strptime(v, "%Y-%m-%d").date()
            except ValueError:
                return v
        return v

class RawMaterial(BaseModelWithConfig):
    id: int
    name: str
    type: str = "普通原料"
    usage_category: str = "其他"  # 已升级：用途分类 (锁定字段名)
    stock_quantity: float = 0.0
    unit: str = "kg"
    created_date: Optional[str] = None
    description: Optional[str] = ""
    last_stock_update: Optional[str] = None

class MaterialUsage(BaseModelWithConfig):
    material_name: str
    quantity: float
    unit: str = "g"
    material_id: Optional[int] = None

class SynthesisRecord(BaseModelWithConfig):
    id: int
    formula_name: str
    formula_id: Optional[str] = None
    experiment_date: Union[DateType, str]
    operator: str
    reactor_materials: List[MaterialUsage] = []
    a_materials: List[MaterialUsage] = []
    b_materials: List[MaterialUsage] = []
    process_desc: Optional[str] = ""
    created_at: Optional[str] = None
    last_modified: Optional[str] = None
    
    @field_validator('experiment_date', mode='before')
    @classmethod
    def parse_date(cls, v):
        if isinstance(v, str):
            try:
                return datetime.strptime(v, "%Y-%m-%d").date()
            except ValueError:
                return v
        return v

class Ingredient(BaseModelWithConfig):
    name: str
    ratio: float
    description: Optional[str] = ""

class Product(BaseModelWithConfig):
    id: int
    product_name: str
    product_code: Optional[str] = ""
    description: Optional[str] = ""
    ingredients: List[Ingredient] = []
    created_at: Optional[str] = None
    last_modified: Optional[str] = None

class TimelineInfo(BaseModelWithConfig):
    is_valid: bool
    status: str
    status_emoji: str
    percent: float
    passed_days: int
    total_days: int
    start_date: Optional[DateType] = None
    end_date: Optional[DateType] = None
    today: DateType
    estimated_completion: Optional[DateType] = None
    remaining_days: int = 0
    is_delayed: bool = False
    is_ahead: bool = False
    error_reason: Optional[str] = None

class User(BaseModelWithConfig):
    username: str
    password_hash: Optional[str] = None
    role: UserRole = UserRole.USER
    created_at: Optional[str] = None
    last_login: Optional[str] = None

class InventoryRecord(BaseModelWithConfig):
    id: int
    material_id: int
    type: StockMovementType
    quantity: float
    reason: Optional[str] = ""
    operator: str
    created_at: Optional[str] = None
    snapshot_stock: Optional[float] = None

class MotherLiquor(BaseModelWithConfig):
    id: int
    name: str
    source_type: MotherLiquorSourceType
    source_id: Optional[int] = None
    batch_number: Optional[str] = None
    production_date: Optional[Union[DateType, str]] = None
    production_mode: Optional[str] = None
    manufacturer: Optional[str] = None
    mother_liquor_type: Optional[str] = None
    solid_content: float = 0.0
    ph_value: float = 7.0
    density: float = 1.05
    color: str = "无色透明"
    description: Optional[str] = ""
    created_at: Optional[str] = None
    last_modified: Optional[str] = None

    @field_validator('production_date', mode='before')
    @classmethod
    def parse_date(cls, v):
        if isinstance(v, str) and v:
            try:
                return datetime.strptime(v, "%Y-%m-%d").date()
            except ValueError:
                return v
        return v

class BOMLine(BaseModelWithConfig):
    material_id: Optional[int] = None
    material_name: str
    quantity: float
    unit: str = "kg"
    note: Optional[str] = ""

class BOMVersion(BaseModelWithConfig):
    id: int
    bom_id: int
    version_number: str
    status: BOMStatus = BOMStatus.PENDING
    effective_from: Union[DateType, str]
    lines: List[BOMLine] = []
    description: Optional[str] = ""
    created_at: Optional[str] = None
    created_by: Optional[str] = None
    
    @field_validator('effective_from', mode='before')
    @classmethod
    def parse_date(cls, v):
        if isinstance(v, str) and v:
            try:
                return datetime.strptime(v, "%Y-%m-%d").date()
            except ValueError:
                return v
        return v

class BOM(BaseModelWithConfig):
    id: int
    product_id: int
    created_at: Optional[str] = None
    last_modified: Optional[str] = None

class BOMExplosionItem(BaseModelWithConfig):
    item_id: int
    item_name: str
    item_type: str = MaterialType.RAW_MATERIAL.value
    required_qty: float
    uom: str = DEFAULT_UNIT_KG
    phase: Optional[str] = None

class ProductionOrder(BaseModelWithConfig):
    id: int
    order_code: str
    bom_id: int
    bom_version_id: int
    plan_qty: float
    start_date: Union[DateType, str]
    end_date: Optional[Union[DateType, str]] = None
    status: ProductionOrderStatus = ProductionOrderStatus.PLANNED
    created_at: Optional[str] = None
    last_modified: Optional[str] = None
    finished_at: Optional[str] = None
    
    @field_validator('start_date', 'end_date', mode='before')
    @classmethod
    def parse_date(cls, v):
        if isinstance(v, str) and v:
            try:
                return datetime.strptime(v, "%Y-%m-%d").date()
            except ValueError:
                return v
        return v

class IssueLine(BaseModelWithConfig):
    item_id: int
    item_name: str
    item_type: str = "raw_material" 
    required_qty: float
    uom: str = "kg"
    phase: Optional[str] = ""

class MaterialIssue(BaseModelWithConfig):
    id: int
    issue_code: str
    production_order_id: int
    status: IssueStatus = IssueStatus.DRAFT
    created_at: Optional[str] = None
    lines: List[IssueLine] = []

class ProductStock(BaseModelWithConfig):
    id: int
    name: str
    type: str = ProductCategory.OTHER.value
    stock_quantity: float = 0.0
    unit: str = DEFAULT_UNIT
    last_update: Optional[str] = None

class PasteExperiment(BaseModelWithConfig):
    id: int
    experiment_date: Union[DateType, str]
    operator: str
    formula_name: Optional[str] = ""
    created_at: Optional[str] = None
    last_modified: Optional[str] = None
    model_config = ConfigDict(populate_by_name=True, from_attributes=True, extra='allow')

    @field_validator('experiment_date', mode='before')
    @classmethod
    def parse_date(cls, v):
        if isinstance(v, str) and v:
            try:
                return datetime.strptime(v, "%Y-%m-%d").date()
            except ValueError:
                return v
        return v

class MortarExperiment(BaseModelWithConfig):
    id: int
    experiment_date: Union[DateType, str]
    operator: str
    formula_name: Optional[str] = ""
    created_at: Optional[str] = None
    last_modified: Optional[str] = None
    model_config = ConfigDict(populate_by_name=True, from_attributes=True, extra='allow')

    @field_validator('experiment_date', mode='before')
    @classmethod
    def parse_date(cls, v):
        if isinstance(v, str) and v:
            try:
                return datetime.strptime(v, "%Y-%m-%d").date()
            except ValueError:
                return v
        return v

class ConcreteExperiment(BaseModelWithConfig):
    id: int
    experiment_date: Union[DateType, str]
    operator: str
    formula_name: Optional[str] = ""
    created_at: Optional[str] = None
    last_modified: Optional[str] = None
    model_config = ConfigDict(populate_by_name=True, from_attributes=True, extra='allow')

    @field_validator('experiment_date', mode='before')
    @classmethod
    def parse_date(cls, v):
        if isinstance(v, str) and v:
            try:
                return datetime.strptime(v, "%Y-%m-%d").date()
            except ValueError:
                return v
        return v

class ProductInventoryRecord(BaseModelWithConfig):
    id: int
    date: Union[DateType, str]
    created_at: Optional[str] = None
    product_name: str
    product_type: str
    type: str 
    quantity: float
    reason: Optional[str] = ""
    operator: str
    snapshot_stock: Optional[float] = None
    batch_number: Optional[str] = None

    @field_validator('date', mode='before')
    @classmethod
    def parse_date(cls, v):
        if isinstance(v, str) and v:
            try:
                return datetime.strptime(v, "%Y-%m-%d").date()
            except ValueError:
                return v
        return v

class GoodsReceiptItem(BaseModelWithConfig):
    product_name: str
    product_type: str = ProductCategory.OTHER.value
    quantity: float
    unit: str = DEFAULT_UNIT_KG
    price: Optional[float] = None
    batch_number: Optional[str] = None
    note: Optional[str] = ""

class GoodsReceipt(BaseModelWithConfig):
    id: int
    receipt_code: Optional[str] = None
    created_at: Optional[str] = None
    date: Union[DateType, str] = Field(default_factory=lambda: datetime.now().date())
    supplier: Optional[str] = ""
    operator: str = "User"
    items: List[GoodsReceiptItem] = []
    status: ReceiptStatus = ReceiptStatus.DRAFT
    remark: Optional[str] = ""
    model_config = ConfigDict(populate_by_name=True, from_attributes=True, extra='allow')

    @field_validator('date', mode='before')
    @classmethod
    def parse_date(cls, v):
        if isinstance(v, str) and v:
            try:
                return datetime.strptime(v, "%Y-%m-%d").date()
            except ValueError:
                return v
        return v

class ShippingOrderItem(BaseModelWithConfig):
    product_name: str
    product_type: str = ProductCategory.OTHER.value
    quantity: float
    unit: str = DEFAULT_UNIT_KG
    price: Optional[float] = None
    batch_number: Optional[str] = None
    note: Optional[str] = ""

class ShippingOrder(BaseModelWithConfig):
    id: int
    shipping_code: Optional[str] = None
    created_at: Optional[str] = None
    date: Union[DateType, str] = Field(default_factory=lambda: datetime.now().date())
    customer: Optional[str] = ""
    operator: str = "User"
    items: List[ShippingOrderItem] = []
    status: ShippingStatus = ShippingStatus.DRAFT
    remark: Optional[str] = ""
    model_config = ConfigDict(populate_by_name=True, from_attributes=True, extra='allow')

    @field_validator('date', mode='before')
    @classmethod
    def parse_date(cls, v):
        if isinstance(v, str) and v:
            try:
                return datetime.strptime(v, "%Y-%m-%d").date()
            except ValueError:
                return v
        return v
