from typing import Optional, List, Union
from datetime import datetime, date
from pydantic import Field, field_validator

from core.enums import StockMovementType, UnitType, ProductCategory, MaterialType
from .base import BaseSchema, DBModel

# ---------------------- Raw Material Models ----------------------

class RawMaterialBase(BaseSchema):
    name: str = Field(..., description="原料名称")
    type: str = Field("普通原料", description="原料类型")
    unit: str = Field("kg", description="计量单位")
    description: Optional[str] = Field("", description="描述")

class RawMaterialCreate(RawMaterialBase):
    stock_quantity: float = Field(0.0, description="初始库存")

class RawMaterial(RawMaterialBase, DBModel):
    stock_quantity: float = Field(0.0, description="当前库存")
    created_date: Optional[str] = None
    last_stock_update: Optional[str] = None

# ---------------------- Inventory Record Models ----------------------

class InventoryRecordBase(BaseSchema):
    material_id: int = Field(..., description="物料ID")
    type: StockMovementType = Field(..., description="移动类型 (in/out/adjust/return_in)")
    quantity: float = Field(..., description="变动数量")
    reason: Optional[str] = Field("", description="变动原因")
    operator: str = Field(..., description="操作人")
    snapshot_stock: Optional[float] = Field(None, description="变动后快照库存")
    related_doc_type: Optional[str] = Field(None, description="关联单据类型")
    related_doc_id: Optional[int] = Field(None, description="关联单据ID")

class InventoryRecordCreate(InventoryRecordBase):
    pass

class InventoryRecord(InventoryRecordBase, DBModel):
    date: Optional[str] = None

# ---------------------- Product Models ----------------------

class Ingredient(BaseSchema):
    name: str
    ratio: float
    description: Optional[str] = ""

class ProductBase(BaseSchema):
    product_name: str = Field(..., alias="name", description="产品名称") # Alias for compatibility
    product_code: Optional[str] = Field("", description="产品编码")
    type: str = Field(ProductCategory.OTHER.value, description="产品类型")
    unit: str = Field("吨", description="单位")
    description: Optional[str] = ""

class ProductCreate(ProductBase):
    ingredients: List[Ingredient] = []

class Product(ProductBase, DBModel):
    stock_quantity: float = Field(0.0, description="成品库存")
    ingredients: List[Ingredient] = []
    last_modified: Optional[str] = None

# ---------------------- Product Inventory Record Models ----------------------

class ProductInventoryRecordBase(BaseSchema):
    product_name: str
    product_type: str
    type: str = Field(..., description="移动类型")
    quantity: float
    reason: Optional[str] = ""
    operator: str
    snapshot_stock: Optional[float] = None
    batch_number: Optional[str] = None
    date: Union[date, str] = Field(default_factory=lambda: datetime.now().date())

    @field_validator('date', mode='before')
    @classmethod
    def parse_date(cls, v):
        if isinstance(v, str) and v:
            try:
                return datetime.strptime(v, "%Y-%m-%d").date()
            except ValueError:
                return v
        return v

class ProductInventoryRecord(ProductInventoryRecordBase, DBModel):
    pass
