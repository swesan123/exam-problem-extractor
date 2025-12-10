"""Pydantic models for generation endpoint."""
from typing import List, Optional

from fastapi import UploadFile
from pydantic import BaseModel, Field, field_validator


class GenerateRequest(BaseModel):
    """Request model for generation endpoint."""

    ocr_text: Optional[str] = Field(
        None,
        min_length=1,
        description="Pre-extracted OCR text (alternative to image_file)",
    )
    image_file: Optional[UploadFile] = Field(
        None,
        description="Image file for OCR extraction (alternative to ocr_text)",
    )
    retrieved_context: Optional[List[str]] = Field(
        None,
        description="Pre-retrieved context (optional, will retrieve if not provided)",
    )
    include_solution: bool = Field(
        default=False,
        description="Whether to include solution in the generated question",
    )

    @field_validator("ocr_text", "image_file")
    @classmethod
    def validate_at_least_one_provided(cls, v, info):
        """Ensure at least one of ocr_text or image_file is provided."""
        values = info.data
        if not values.get("ocr_text") and not values.get("image_file"):
            raise ValueError("At least one of 'ocr_text' or 'image_file' must be provided")
        return v

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

