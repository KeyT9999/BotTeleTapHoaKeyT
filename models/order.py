from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class Order(BaseModel):
    id: str = Field(..., alias="_id")
    tg_user_id: int
    product_id: int
    qty: int
    bonus: int = 0
    deliver_qty: int
    amount: int
    pay_method: str = "payos"
    status: str = "CREATED"
    payment_link_id: Optional[str] = None
    checkout_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expired_at: Optional[datetime] = None

    model_config = {"populate_by_name": True}


class TopupOrder(BaseModel):
    id: str = Field(..., alias="_id")
    tg_user_id: int
    amount: int
    status: str = "CREATED"
    payment_link_id: Optional[str] = None
    checkout_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expired_at: Optional[datetime] = None

    model_config = {"populate_by_name": True}
