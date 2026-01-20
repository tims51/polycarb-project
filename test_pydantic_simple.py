from datetime import date, datetime
from typing import Union
from pydantic import BaseModel, Field

class TestModel(BaseModel):
    # Try without Union first
    d1: date = Field(default_factory=datetime.now().date)

class TestModelUnion(BaseModel):
    # Try with Union
    d2: Union[date, str] = Field(default_factory=lambda: datetime.now().date())

print("Defined models successfully")
