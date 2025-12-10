"""Pydantic models for OCR endpoint."""
from typing import Optional

from fastapi import UploadFile
from pydantic import BaseModel, Field


class OCRResponse(BaseModel):
    """Response model for OCR endpoint."""

    text: str = Field(..., description="Extracted text content")
    confidence: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Confidence score of OCR extraction (0.0 to 1.0)",
    )
    processing_time_ms: Optional[int] = Field(
        None,
        ge=0,
        description="Processing time in milliseconds",
    )

    model_config = {"json_schema_extra": {"example": {"text": "Sample extracted text", "confidence": 0.95, "processing_time_ms": 1234}}}

