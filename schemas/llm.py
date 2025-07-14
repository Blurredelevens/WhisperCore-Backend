from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class LLMGenerateRequest(BaseModel):
    """Schema for LLM API generate request"""

    model: str = Field(..., description="Model name to use for generation")
    prompt: str = Field(..., description="Input prompt for text generation")
    stream: bool = Field(default=False, description="Whether to stream the response")


class LLMGenerateResponse(BaseModel):
    """Schema for LLM API generate response"""

    model: str = Field(..., description="Model name used for generation")
    created_at: datetime = Field(..., description="Timestamp when response was created")
    response: str = Field(..., description="Generated text response")
    done: bool = Field(..., description="Whether generation is complete")
    done_reason: Optional[str] = Field(None, description="Reason why generation stopped")
    context: Optional[List[int]] = Field(None, description="Token context")
    total_duration: Optional[int] = Field(None, description="Total generation duration in nanoseconds")
    load_duration: Optional[int] = Field(None, description="Model load duration in nanoseconds")
    prompt_eval_count: Optional[int] = Field(None, description="Number of prompt tokens evaluated")
    prompt_eval_duration: Optional[int] = Field(None, description="Prompt evaluation duration in nanoseconds")
    eval_count: Optional[int] = Field(None, description="Number of tokens evaluated")
    eval_duration: Optional[int] = Field(None, description="Evaluation duration in nanoseconds")


class LLMModelInfo(BaseModel):
    """Schema for individual model information"""

    name: str = Field(..., description="Model name")
    model: str = Field(..., description="Model identifier")
    modified_at: datetime = Field(..., description="Last modification timestamp")
    size: int = Field(..., description="Model size in bytes")
    digest: str = Field(..., description="Model digest/hash")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional model details")


class LLMModelsResponse(BaseModel):
    """Schema for LLM API models response"""

    models: List[LLMModelInfo] = Field(..., description="List of available models")


class LLMErrorResponse(BaseModel):
    """Schema for LLM API error response"""

    error: str = Field(..., description="Error message")
    code: Optional[int] = Field(None, description="Error code")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class LLMHealthResponse(BaseModel):
    """Schema for LLM API health check response"""

    status: str = Field(..., description="Health status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    version: Optional[str] = Field(None, description="API version")
