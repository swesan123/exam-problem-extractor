"""Pydantic models for generation endpoint."""
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


class GenerateRequest(BaseModel):
    """Request model for generation endpoint.
    
    Note: image_file is handled separately via FastAPI's File() parameter
    in the route handler, not as a Pydantic field.
    """

    ocr_text: Optional[str] = Field(
        None,
        min_length=1,
        description="Pre-extracted OCR text (alternative to image_file)",
    )
    retrieved_context: Optional[List[str]] = Field(
        None,
        description="Pre-retrieved context (optional, will retrieve if not provided)",
    )
    include_solution: bool = Field(
        default=False,
        description="Whether to include solution in the generated question",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "ocr_text": "Extracted text from image...",
                "retrieved_context": ["Context 1", "Context 2"],
                "include_solution": False,
            }
        }
    }


class GenerateResponse(BaseModel):
    """Response model for generation endpoint."""

    question: str = Field(..., description="Generated exam-style question")
    metadata: dict = Field(..., description="Metadata about the generation process")
    processing_steps: List[str] = Field(..., description="List of processing steps performed")

    model_config = {
        "json_schema_extra": {
            "example": {
                "question": "Formatted exam question...",
                "metadata": {
                    "model": "gpt-4",
                    "tokens_used": 1234,
                    "retrieved_count": 5,
                },
                "processing_steps": ["ocr", "retrieval", "generation"],
            }
        }
    }

