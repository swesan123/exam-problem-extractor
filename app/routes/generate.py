"""Generation route endpoint."""
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.models.generation_models import GenerateResponse
from app.services.generation_service import GenerationService
from app.services.ocr_service import OCRService
from app.services.embedding_service import EmbeddingService
from app.services.retrieval_service import RetrievalService
from app.utils.file_utils import cleanup_temp_file, save_temp_file, validate_image_file

router = APIRouter(prefix="/generate", tags=["generation"])


@router.post("", response_model=GenerateResponse, status_code=status.HTTP_200_OK)
async def generate_question(
    ocr_text: Optional[str] = Form(None),
    image_file: Optional[UploadFile] = File(None),
    retrieved_context: Optional[str] = Form(None),  # JSON string
    include_solution: bool = Form(False),
):
    """
    Generate exam question from image or text.

    Supports two modes:
    1. Image upload: Automatically performs OCR and retrieval
    2. Direct text: Uses provided ocr_text and optional retrieved_context

    Args:
        ocr_text: Pre-extracted OCR text (alternative to image_file)
        image_file: Image file for OCR extraction (alternative to ocr_text)
        retrieved_context: JSON string of pre-retrieved context (optional)
        include_solution: Whether to include solution in generated question

    Returns:
        GenerateResponse with formatted question and metadata
    """
    temp_path: Path | None = None
    processing_steps: List[str] = []

    try:
        # Validate that at least one input is provided
        if not ocr_text and not image_file:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one of 'ocr_text' or 'image_file' must be provided",
            )

        # Step 1: OCR extraction (if image provided)
        if image_file:
            validate_image_file(image_file)
            temp_path = save_temp_file(image_file)
            ocr_service = OCRService()
            ocr_text = ocr_service.extract_text(temp_path)
            processing_steps.append("ocr")

        if not ocr_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OCR text extraction failed or not provided",
            )

        # Step 2: Retrieval (if context not provided)
        context_list: List[str] = []
        if retrieved_context:
            # Parse JSON string if provided
            import json
            try:
                context_list = json.loads(retrieved_context)
                if not isinstance(context_list, list):
                    context_list = [retrieved_context]
            except json.JSONDecodeError:
                # If not valid JSON, treat as single string
                context_list = [retrieved_context]
        else:
            # Perform retrieval
            embedding_service = EmbeddingService()
            retrieval_service = RetrievalService(embedding_service)
            retrieved_chunks = retrieval_service.retrieve(ocr_text, top_k=5)
            context_list = [chunk.text for chunk in retrieved_chunks]
            processing_steps.append("retrieval")

        # Step 3: Generation
        generation_service = GenerationService()
        if include_solution:
            result = generation_service.generate_with_solution(ocr_text, context_list)
            question = result["question"]
            if result.get("solution"):
                question += f"\n\nSolution:\n{result['solution']}"
        else:
            result = generation_service.generate_with_metadata(ocr_text, context_list)
            question = result["question"]

        processing_steps.append("generation")

        # Build response
        metadata = result.get("metadata", {})
        metadata["processing_steps"] = processing_steps

        return GenerateResponse(
            question=question,
            metadata=metadata,
            processing_steps=processing_steps,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Question generation failed: {str(e)}",
        ) from e
    finally:
        # Clean up temporary file
        if temp_path:
            cleanup_temp_file(temp_path)

