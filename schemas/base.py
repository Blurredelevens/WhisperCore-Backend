from pydantic import BaseModel, EmailStr, constr
from datetime import datetime
from typing import Optional
from pydantic import BaseModel as PydanticBaseModel

class TimestampMixin(BaseModel):
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserBase(BaseModel):
    email: EmailStr

class BaseResponse(BaseModel):
    message: str 

class BaseModel(PydanticBaseModel):
    pass

class ErrorResponseSchema(BaseModel, extra="ignore"):
    msg: str | dict | list
    loc: Optional[str] = None
    type: Optional[str] = None
    ctx: Optional[dict] = None 