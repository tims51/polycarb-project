from typing import Union, Optional
from datetime import date, datetime
from pydantic import BaseModel, Field, ConfigDict

class BaseModelWithConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

try:
    class GoodsReceipt(BaseModelWithConfig):
        id: int
        date: Union[date, str] = Field(default_factory=lambda: datetime.now().date())
        
    print("GoodsReceipt defined successfully")
    
    obj = GoodsReceipt(id=1)
    print(obj)
except Exception as e:
    print(f"Error defining GoodsReceipt: {e}")
    import traceback
    traceback.print_exc()
