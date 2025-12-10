"""Pydantic models for retrieval endpoint."""
from typing import Dict, List

from pydantic import BaseModel, Field


class RetrievedChunk(BaseModel):
    """A retrieved chunk with similarity score."""

    text: str = Field(..., description="Text content of the retrieved chunk")
    score: float = Field(..., ge=0.0, le=1.0, description="Similarity score (0.0 to 1.0)")
    metadata: Dict = Field(..., description="Metadata associated with the chunk")
    chunk_id: str = Field(..., description="Unique identifier for the chunk")

    model_config = {
        "json_schema_extra": {
            "example": {
                "text": "Similar exam question...",
                "score": 0.87,
                "metadata": {"source": "exam_2023", "page": 1},
                "chunk_id": "chunk_001",
            }
        }
    }


class RetrieveRequest(BaseModel):
    """Request model for retrieval endpoint."""

    query: str = Field(..., min_length=1, description="Query text for semantic search")
    top_k: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Number of top results to retrieve",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "quadratic equations",
                "top_k": 5,
            }
        }
    }


class RetrieveResponse(BaseModel):
    """Response model for retrieval endpoint."""

    results: List[RetrievedChunk] = Field(..., description="List of retrieved chunks")
    query_embedding_dim: int = Field(..., ge=1, description="Dimension of the query embedding")

    model_config = {
        "json_schema_extra": {
            "example": {
                "results": [
                    {
                        "text": "Similar exam question...",
                        "score": 0.87,
                        "metadata": {"source": "exam_2023"},
                        "chunk_id": "chunk_001",
                    }
                ],
                "query_embedding_dim": 1536,
            }
        }
    }

