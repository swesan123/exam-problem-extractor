<<<<<<< HEAD
"""Pydantic models for question management endpoints."""
from datetime import datetime
from typing import Optional
=======
"""Pydantic models for question management API."""
from datetime import datetime
from typing import Any, Dict, Optional
>>>>>>> main

from pydantic import BaseModel, Field


class QuestionCreate(BaseModel):
<<<<<<< HEAD
    """Request model for creating a question."""
=======
    """Model for creating a new question."""
>>>>>>> main

    class_id: str = Field(..., description="ID of the class this question belongs to")
    question_text: str = Field(..., min_length=1, description="The question text")
    solution: Optional[str] = Field(None, description="Solution to the question")
<<<<<<< HEAD
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
=======
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional metadata"
    )
    source_image: Optional[str] = Field(None, description="Path to source image if available")

    model_config = {
        "json_schema_extra": {
            "example": {
                "class_id": "class_123",
                "question_text": "What is 2 + 2?",
                "solution": "4",
                "metadata": {"source": "manual"},
            }
        }
    }


class QuestionUpdate(BaseModel):
    """Model for updating an existing question."""

    question_text: Optional[str] = Field(None, min_length=1, description="The question text")
    solution: Optional[str] = Field(None, description="Solution to the question")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    model_config = {
        "json_schema_extra": {
            "example": {
                "question_text": "What is 2 + 2?",
                "solution": "4",
            }
        }
    }


class QuestionResponse(BaseModel):
    """Model for question response."""

    id: str
    class_id: str
    question_text: str
    solution: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    source_image: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "q_123",
                "class_id": "class_123",
                "question_text": "What is 2 + 2?",
                "solution": "4",
                "metadata": {"source": "manual"},
                "source_image": None,
                "created_at": "2025-12-10T12:00:00Z",
                "updated_at": "2025-12-10T12:00:00Z",
            }
        }
    }


class QuestionListResponse(BaseModel):
    """Model for paginated question list response."""

    questions: list[QuestionResponse]
    total: int
    skip: int
    limit: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "questions": [],
                "total": 0,
                "skip": 0,
                "limit": 100,
            }
        }
    }
>>>>>>> main

