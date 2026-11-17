from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class StockCreate(BaseModel):
    symbol: str
    name: Optional[str] = None

class StockResponse(BaseModel):
    symbol: str
    name: Optional[str] = None
    added_at: datetime

class PriceResponse(BaseModel):
    symbol: str
    price: float
    timestamp: datetime
    cached: bool