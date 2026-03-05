from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class User(BaseModel):
    tg_user_id: int
    username: Optional[str] = None
    balance: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
