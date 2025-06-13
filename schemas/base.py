from pydantic import BaseModel, EmailStr, constr
from datetime import datetime
from typing import Optional

class TimestampMixin(BaseModel):
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class UserBase(BaseModel):
    email: EmailStr

class BaseResponse(BaseModel):
    message: str 