"""Pydantic models for class management endpoints."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ClassCreate(BaseModel):
    """Request model for creating a class."""

    name: str = Field(..., min_length=1, max_length=200, description="Class name")
    description: Optional[str] = Field(
        None, max_length=1000, description="Class description"
    )
    subject: Optional[str] = Field(None, max_length=100, description="Subject area")


class ClassUpdate(BaseModel):
    """Request model for updating a class."""

    name: Optional[str] = Field(
        None, min_length=1, max_length=200, description="Class name"
    )
    description: Optional[str] = Field(
        None, max_length=1000, description="Class description"
    )
    subject: Optional[str] = Field(None, max_length=100, description="Subject area")


class ClassResponse(BaseModel):
    """Response model for class data."""

    id: str = Field(..., description="Class ID")
    name: str = Field(..., description="Class name")
    description: Optional[str] = Field(None, description="Class description")
    subject: Optional[str] = Field(None, description="Subject area")
    question_count: int = Field(0, description="Number of questions in this class")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class ClassListResponse(BaseModel):
    """Response model for listing classes."""

    classes: list[ClassResponse] = Field(..., description="List of classes")
    total: int = Field(..., description="Total number of classes")
