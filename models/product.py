from pydantic import BaseModel, Field
from typing import Optional


class Product(BaseModel):
    id: int = Field(..., alias="_id")
    name: str
    price: int
    stock: int = 0
    active: bool = True
    promo_buy: Optional[int] = None
    promo_bonus: Optional[int] = None

    model_config = {"populate_by_name": True}
