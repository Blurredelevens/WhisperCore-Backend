from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict, EmailStr


class TimestampMixin(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    created_at: datetime
    updated_at: datetime


class UserBase(BaseModel):
    model_config = ConfigDict()

    email: EmailStr


class BaseResponse(BaseModel):
    model_config = ConfigDict()

    message: str


class BaseModel(PydanticBaseModel):
    model_config = ConfigDict()
    pass


class ErrorResponseSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    msg: str | dict | list
    loc: Optional[str] = None
    type: Optional[str] = None
    ctx: Optional[dict] = None
