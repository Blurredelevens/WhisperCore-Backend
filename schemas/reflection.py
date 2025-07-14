from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, constr

from .base import BaseResponse, TimestampMixin


class ReflectionType(str, Enum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ReflectionBase(BaseModel):
    model_config = ConfigDict()

    content: constr(min_length=1)
    reflection_type: ReflectionType


class ReflectionCreate(ReflectionBase):
    model_config = ConfigDict()

    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


class ReflectionResponse(ReflectionBase, TimestampMixin):
    model_config = ConfigDict()

    id: int
    user_id: int
    period_start: datetime
    period_end: datetime


class ReflectionListResponse(BaseModel):
    model_config = ConfigDict()

    reflections: list[ReflectionResponse]


class ReflectionDeleteResponse(BaseResponse):
    model_config = ConfigDict()
    pass
