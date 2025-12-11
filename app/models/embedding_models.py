"""Pydantic models for embedding endpoint."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class EmbeddingMetadata(BaseModel):
    """Metadata for embedding storage."""

    source: str = Field(..., description="Source identifier (e.g., exam name)")
    page: Optional[int] = Field(None, ge=1, description="Page number if applicable")
    chunk_id: str = Field(..., description="Unique identifier for this chunk")
    timestamp: Optional[datetime] = Field(
        None,
        description="Timestamp when the content was created",
    )
    class_id: Optional[str] = Field(
        None, description="Class ID this reference content belongs to"
    )
    exam_type: Optional[str] = Field(
        None, description="Type of exam (e.g., midterm, final, practice)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "source": "exam_2023",
                "page": 1,
                "chunk_id": "chunk_001",
                "timestamp": "2023-01-01T00:00:00Z",
                "class_id": "class_abc123",
                "exam_type": "midterm",
            }
        }
    }


class EmbeddingRequest(BaseModel):
    """Request model for embedding endpoint."""

    text: str = Field(..., min_length=1, description="Text content to embed")
    metadata: EmbeddingMetadata = Field(..., description="Metadata for the embedding")

    model_config = {
        "json_schema_extra": {
            "example": {
                "text": "Sample exam question text...",
                "metadata": {
                    "source": "exam_2023",
                    "page": 1,
                    "chunk_id": "chunk_001",
                },
            }
        }
    }


class EmbeddingResponse(BaseModel):
    """Response model for embedding endpoint."""

    embedding_id: str = Field(
        ..., description="Unique identifier for the stored embedding"
    )
    status: str = Field(..., description="Status of the embedding operation")
    vector_dimension: int = Field(
        ..., ge=1, description="Dimension of the embedding vector"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "embedding_id": "emb_abc123",
                "status": "stored",
                "vector_dimension": 1536,
            }
        }
    }
