from datetime import date as DateType, datetime
from typing import Union, Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class BaseModelWithConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True, extra='allow')

class GoodsReceipt(BaseModelWithConfig):
    id: int
    receipt_code: Optional[str] = None
    created_at: Optional[str] = None
    date: Union[DateType, str] = Field(default_factory=lambda: datetime.now().date())
    supplier: Optional[str] = ""
    operator: str = "User"
    items: List[Dict[str, Any]] = []
    status: str = "draft"
    remark: Optional[str] = ""
    model_config = ConfigDict(populate_by_name=True, from_attributes=True, extra='allow')

print("GoodsReceipt defined successfully")
