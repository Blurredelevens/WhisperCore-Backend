from pydantic import BaseModel, Field
from typing import Any, Optional

class TaskCreate(BaseModel):
    query: str = Field(..., description="The query to process.")
    

class TaskCreationResponse(BaseModel):
    task_id: str = Field(..., description="The ID of the created task.")

class TaskStatusResponse(BaseModel):
    task_id: str = Field(..., description="The ID of the task.")
    state: str = Field(..., description="The state of the task.")
    status: Optional[str] = Field(None, description="The status message of the task.")
    result: Optional[Any] = Field(None, description="The result of the task, if completed.") 