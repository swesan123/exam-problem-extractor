"""Pydantic models for generation endpoint."""

from typing import Dict, List, Optional

from fastapi import UploadFile
from pydantic import BaseModel, Field, model_validator


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

    @model_validator(mode="after")
    def validate_at_least_one_provided(self):
        """Ensure at least one of ocr_text or image_file is provided."""
        if not self.ocr_text and not self.image_file:
            raise ValueError(
                "At least one of 'ocr_text' or 'image_file' must be provided"
            )
        return self

    model_config = {
        "json_schema_extra": {
            "example": {
                "ocr_text": "Extracted text from image...",
                "retrieved_context": ["Context 1", "Context 2"],
                "include_solution": False,
            }
        }
    }


class ReferenceCitation(BaseModel):
    """Citation for a reference used in question generation."""

    source_file: str = Field(..., description="Original filename of the reference")
    chunk_id: str = Field(..., description="Chunk ID of the reference")
    reference_type: str = Field(
        ..., description="Type of reference (e.g., assessment, lecture)"
    )
    score: float = Field(
        ..., ge=0.0, le=1.0, description="Similarity score of the reference"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "source_file": "midterm_2023.pdf",
                "chunk_id": "midterm_2023_chunk_0",
                "reference_type": "assessment",
                "score": 0.87,
            }
        }
    }


class GenerateResponse(BaseModel):
    """Response model for generation endpoint."""

    question: str = Field(..., description="Generated exam-style question")
    metadata: dict = Field(..., description="Metadata about the generation process")
    processing_steps: List[str] = Field(
        ..., description="List of processing steps performed"
    )
    question_id: Optional[str] = Field(
        None, description="ID of saved question (if class_id provided)"
    )
    class_id: Optional[str] = Field(
        None, description="ID of class question was saved to (if provided)"
    )
    references_used: Dict[str, List[ReferenceCitation]] = Field(
        default_factory=dict,
        description="References used for generation (assessment and lecture)",
    )

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
                "references_used": {
                    "assessment": [
                        {
                            "source_file": "midterm_2023.pdf",
                            "chunk_id": "midterm_2023_chunk_0",
                            "reference_type": "assessment",
                            "score": 0.87,
                        }
                    ],
                    "lecture": [
                        {
                            "source_file": "lecture_5.pdf",
                            "chunk_id": "lecture_5_chunk_2",
                            "reference_type": "lecture",
                            "score": 0.82,
                        }
                    ],
                },
            }
        }
    }
