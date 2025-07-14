from pydantic import BaseModel, Field, ConfigDict
from typing import Any, Optional

class TaskCreate(BaseModel):
    model_config = ConfigDict()
    
    query: str = Field(..., description="The query to process.")
    

class TaskCreationResponse(BaseModel):
    model_config = ConfigDict()
    
    task_id: str = Field(..., description="The ID of the created task.")

class TaskStatusResponse(BaseModel):
    model_config = ConfigDict()
    
    task_id: str = Field(..., description="The ID of the task.")
    state: str = Field(..., description="The state of the task.")
    status: Optional[str] = Field(None, description="The status message of the task.")
    result: Optional[Any] = Field(None, description="The result of the task, if completed.") 