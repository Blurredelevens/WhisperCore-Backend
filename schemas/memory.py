from typing import List, Optional

from pydantic import BaseModel, constr

from .base import BaseResponse, TimestampMixin


class MemoryBase(BaseModel):
    content: constr(min_length=1)
    chat_id: Optional[str] = None
    mood_emoji: Optional[str] = None
    tags: Optional[List[str]] = []
    memory_weight: Optional[int] = None


class MemoryCreate(MemoryBase):
    pass


class MemoryUpdate(BaseModel):
    content: Optional[constr(min_length=1)] = None
    chat_id: Optional[str] = None
    mood_emoji: Optional[str] = None
    tags: Optional[List[str]] = None


class MemoryResponse(MemoryBase, TimestampMixin):
    id: int
    user_id: int


class MemoryListResponse(BaseModel):
    memories: List[MemoryResponse]


class MemoryDeleteResponse(BaseResponse):
    pass
