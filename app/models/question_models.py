"""Pydantic models for question management endpoints."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class QuestionCreate(BaseModel):
    """Request model for creating a question."""

    class_id: str = Field(..., description="ID of the class this question belongs to")
    question_text: str = Field(..., min_length=1, description="The question text")
    solution: Optional[str] = Field(None, description="Solution to the question")
    metadata: Optional[dict] = Field(None, default_factory=dict, description="Additional metadata")
    source_image: Optional[str] = Field(None, description="Path to original image if available")


class QuestionUpdate(BaseModel):
    """Request model for updating a question."""

    question_text: Optional[str] = Field(None, min_length=1, description="The question text")
    solution: Optional[str] = Field(None, description="Solution to the question")
    metadata: Optional[dict] = Field(None, description="Additional metadata")
    source_image: Optional[str] = Field(None, description="Path to original image if available")


class QuestionResponse(BaseModel):
    """Response model for question data."""

    id: str = Field(..., description="Question ID")
    class_id: str = Field(..., description="ID of the class this question belongs to")
    question_text: str = Field(..., description="The question text")
    solution: Optional[str] = Field(None, description="Solution to the question")
    metadata: Optional[dict] = Field(None, description="Additional metadata")
    source_image: Optional[str] = Field(None, description="Path to original image if available")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class QuestionListResponse(BaseModel):
    """Response model for listing questions."""

    questions: list[QuestionResponse] = Field(..., description="List of questions")
    total: int = Field(..., description="Total number of questions")
    page: int = Field(..., description="Current page number")
    limit: int = Field(..., description="Number of items per page")

