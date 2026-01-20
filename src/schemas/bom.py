from typing import Optional, List, Union
from datetime import datetime, date
from pydantic import Field, field_validator

from core.enums import BOMStatus, ProductionOrderStatus, IssueStatus, MaterialType
from .base import BaseSchema, DBModel

# ---------------------- BOM Models ----------------------

class BOMItem(BaseSchema):
    """BOM 行项目"""
    material_id: Optional[int] = Field(None, description="原料ID")
    material_name: str = Field(..., description="原料名称")
    quantity: float = Field(..., description="数量")
    unit: str = Field("kg", description="单位")
    note: Optional[str] = Field("", description="备注")

class BOMVersionBase(BaseSchema):
    version_number: str = Field(..., description="版本号")
    status: BOMStatus = Field(default=BOMStatus.PENDING, description="状态")
    effective_from: Union[date, str] = Field(..., description="生效日期")
    description: Optional[str] = ""
    
    @field_validator('effective_from', mode='before')
    @classmethod
    def parse_date(cls, v):
        if isinstance(v, str) and v:
            try:
                return datetime.strptime(v, "%Y-%m-%d").date()
            except ValueError:
                return v
        return v

class BOMVersionCreate(BOMVersionBase):
    lines: List[BOMItem] = []

class BOMVersion(BOMVersionBase, DBModel):
    bom_id: int = Field(..., description="关联BOM主表ID")
    lines: List[BOMItem] = []
    created_by: Optional[str] = None

class BOMBase(BaseSchema):
    product_id: int = Field(..., description="关联产品ID")
    bom_code: Optional[str] = Field(None, description="配方编码")
    bom_name: Optional[str] = Field(None, description="配方名称")
    bom_type: Optional[str] = Field(None, description="配方类型")

class BOMCreate(BOMBase):
    pass

class BOM(BOMBase, DBModel):
    last_modified: Optional[str] = None

# ---------------------- Production Order Models ----------------------

class ProductionOrderBase(BaseSchema):
    order_code: str = Field(..., description="生产单号")
    bom_id: int
    bom_version_id: int
    plan_qty: float = Field(..., description="计划产量")
    start_date: Union[date, str]
    end_date: Optional[Union[date, str]] = None
    status: ProductionOrderStatus = ProductionOrderStatus.PLANNED
    
    @field_validator('start_date', 'end_date', mode='before')
    @classmethod
    def parse_date(cls, v):
        if isinstance(v, str) and v:
            try:
                return datetime.strptime(v, "%Y-%m-%d").date()
            except ValueError:
                return v
        return v

class ProductionOrder(ProductionOrderBase, DBModel):
    last_modified: Optional[str] = None
    finished_at: Optional[str] = None

# ---------------------- Material Issue Models ----------------------

class IssueLine(BaseSchema):
    item_id: int
    item_name: str
    item_type: str = MaterialType.RAW_MATERIAL.value
    required_qty: float
    uom: str = "kg"
    phase: Optional[str] = ""

class MaterialIssueBase(BaseSchema):
    issue_code: str
    production_order_id: int
    status: IssueStatus = IssueStatus.DRAFT
    lines: List[IssueLine] = []

class MaterialIssue(MaterialIssueBase, DBModel):
    pass
