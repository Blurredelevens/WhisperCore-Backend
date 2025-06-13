from pydantic import BaseModel, constr
from typing import Optional
from datetime import datetime
from enum import Enum
from .base import BaseResponse, TimestampMixin

class ReflectionType(str, Enum):
    WEEKLY = 'weekly'
    MONTHLY = 'monthly'

class ReflectionBase(BaseModel):
    content: constr(min_length=1)
    reflection_type: ReflectionType

class ReflectionCreate(ReflectionBase):
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None

class ReflectionResponse(ReflectionBase, TimestampMixin):
    id: int
    user_id: int
    period_start: datetime
    period_end: datetime

class ReflectionListResponse(BaseModel):
    reflections: list[ReflectionResponse]

class ReflectionDeleteResponse(BaseResponse):
    pass 