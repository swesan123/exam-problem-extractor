"""Generation route endpoint."""
import json
import logging
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.generation_models import GenerateResponse, ReferenceCitation
from app.models.question_models import QuestionCreate
from app.services.generation_service import GenerationService
from app.services.ocr_service import OCRService
from app.services.embedding_service import EmbeddingService
from app.services.retrieval_service import RetrievalService
from app.services.question_service import QuestionService
from app.utils.file_utils import cleanup_temp_file, save_temp_file, validate_upload_file

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generate", tags=["generation"])


@router.post("", response_model=GenerateResponse, status_code=status.HTTP_200_OK)
async def generate_question(
    request: Request,
    ocr_text: Optional[str] = Form(None),
    image_file: Optional[UploadFile] = File(None),
    retrieved_context: Optional[str] = Form(None),  # JSON string
    include_solution: bool = Form(False),
    class_id: Optional[str] = Form(None),  # Optional class ID to save question to
    db: Session = Depends(get_db),
):
    """
    Generate exam question from image or text.

    Supports two modes:
    1. Image upload: Automatically performs OCR and retrieval
    2. Direct text: Uses provided ocr_text and optional retrieved_context

    If class_id is provided, the generated question will be automatically saved to that class.

    Args:
        request: FastAPI Request object
        ocr_text: Pre-extracted OCR text (alternative to image_file)
        image_file: Image file for OCR extraction (alternative to ocr_text)
        retrieved_context: JSON string of pre-retrieved context (optional)
        include_solution: Whether to include solution in generated question
        class_id: Optional class ID to automatically save question to
        db: Database session

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
            validate_upload_file(image_file)
            temp_path = save_temp_file(image_file)
            ocr_service = OCRService()
            
            # Handle PDF by converting pages to images first
            if image_file.content_type == "application/pdf":
                from app.utils.file_utils import convert_pdf_to_images
                image_paths = convert_pdf_to_images(temp_path)
                all_text_parts = []
                try:
                    for page_num, image_path in enumerate(image_paths, start=1):
                        text = ocr_service.extract_text(image_path)
                        page_header = f"=== Page {page_num} ===\n"
                        all_text_parts.append(page_header + text)
                    ocr_text = "\n\n".join(all_text_parts)
                finally:
                    # Clean up generated images
                    for img_path in image_paths:
                        cleanup_temp_file(img_path)
            else:
                # Handle regular image files
                ocr_text = ocr_service.extract_text(temp_path)
            
            processing_steps.append("ocr")

        if not ocr_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OCR text extraction failed or not provided",
            )

        # Step 2: Retrieval (if context not provided)
        assessment_chunks = []
        lecture_chunks = []
        references_used = {"assessment": [], "lecture": []}
        
        if retrieved_context:
            # Parse JSON string if provided
            try:
                context_list = json.loads(retrieved_context)
                if not isinstance(context_list, list):
                    context_list = [retrieved_context]
            except json.JSONDecodeError:
                # If not valid JSON, treat as single string
                context_list = [retrieved_context]
            # For manual context, treat as generic (no reference tracking)
            assessment_chunks = []
            lecture_chunks = []
        else:
            # Perform retrieval with class-scoped filtering if class_id provided
            embedding_service = EmbeddingService()
            retrieval_service = RetrievalService(embedding_service)
            
            if class_id:
                from app.config import settings
                
                # Retrieve assessment references separately (for structure/format)
                assessment_chunks_all = retrieval_service.retrieve_with_scores(
                    ocr_text, top_k=3, class_id=class_id, reference_type="assessment"
                )
                # Retrieve lecture references separately (for content/topics)
                lecture_chunks_all = retrieval_service.retrieve_with_scores(
                    ocr_text, top_k=3, class_id=class_id, reference_type="lecture"
                )
                
                # Filter chunks by similarity threshold
                min_threshold = settings.min_similarity_threshold
                assessment_chunks = [
                    chunk for chunk in assessment_chunks_all 
                    if chunk.score >= min_threshold
                ]
                lecture_chunks = [
                    chunk for chunk in lecture_chunks_all 
                    if chunk.score >= min_threshold
                ]
                
                # Build references_used tracking (include all retrieved, even if below threshold)
                # This allows us to show what was retrieved but not used
                for chunk in assessment_chunks_all:
                    references_used["assessment"].append(
                        ReferenceCitation(
                            source_file=chunk.metadata.get("source_file", "unknown"),
                            chunk_id=chunk.chunk_id,
                            reference_type=chunk.metadata.get("reference_type", "assessment"),
                            score=chunk.score,
                        )
                    )
                
                for chunk in lecture_chunks_all:
                    references_used["lecture"].append(
                        ReferenceCitation(
                            source_file=chunk.metadata.get("source_file", "unknown"),
                            chunk_id=chunk.chunk_id,
                            reference_type=chunk.metadata.get("reference_type", "lecture"),
                            score=chunk.score,
                        )
                    )
            else:
                # Fallback: retrieve without filtering (backward compatibility)
                retrieved_chunks = retrieval_service.retrieve_with_scores(ocr_text, top_k=5)
                # Try to categorize by reference_type if available
                for chunk in retrieved_chunks:
                    ref_type = chunk.metadata.get("reference_type", "").lower()
                    if ref_type == "assessment":
                        assessment_chunks.append(chunk)
                    elif ref_type == "lecture":
                        lecture_chunks.append(chunk)
                    else:
                        # If no type specified, add to both (generic)
                        if not assessment_chunks:
                            assessment_chunks.append(chunk)
                        if not lecture_chunks:
                            lecture_chunks.append(chunk)
            
            processing_steps.append("retrieval")

        # Step 3: Generation
        generation_service = GenerationService()
        
        # Use separate assessment/lecture contexts if available, otherwise fallback
        # Note: assessment_chunks and lecture_chunks are now filtered by similarity threshold
        if assessment_chunks or lecture_chunks:
            # Convert references_used to dict format for generation service
            # Only include references that passed the similarity threshold (those in assessment_chunks/lecture_chunks)
            refs_dict = None
            if references_used:
                from app.config import settings
                min_threshold = settings.min_similarity_threshold
                
                # Filter to only include references that passed threshold
                filtered_assessment = [
                    ref.dict() for ref in references_used.get("assessment", [])
                    if ref.score >= min_threshold
                ]
                filtered_lecture = [
                    ref.dict() for ref in references_used.get("lecture", [])
                    if ref.score >= min_threshold
                ]
                
                if filtered_assessment or filtered_lecture:
                    refs_dict = {
                        "assessment": filtered_assessment,
                        "lecture": filtered_lecture,
                    }
            
            # Use new method with reference types
            if include_solution:
                result = generation_service.generate_with_reference_types_and_solution(
                    ocr_text, assessment_chunks, lecture_chunks, refs_dict
                )
                question = result["question"]
                if result.get("solution"):
                    question += f"\n\nSolution:\n{result['solution']}"
            else:
                result = generation_service.generate_with_reference_types(
                    ocr_text, assessment_chunks, lecture_chunks, refs_dict
                )
                question = result["question"]
        else:
            # Fallback to old method if no chunks retrieved (manual context or no class_id)
            context_list: List[str] = []
            if retrieved_context:
                # Use manually provided context (already parsed above)
                try:
                    parsed = json.loads(retrieved_context)
                    context_list = parsed if isinstance(parsed, list) else [retrieved_context]
                except (json.JSONDecodeError, TypeError):
                    context_list = [retrieved_context] if isinstance(retrieved_context, str) else []
            else:
                # No context at all - use empty list
                context_list = []
            
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

        # Step 4: Save to class if class_id provided
        question_id = None
        saved_class_id = None
        if class_id:
            try:
                question_service = QuestionService(db)
                
                # Extract solution if included
                solution_text = None
                if include_solution and result.get("solution"):
                    solution_text = result["solution"]
                
                # Create question data
                question_data = QuestionCreate(
                    class_id=class_id,
                    question_text=question,
                    solution=solution_text,
                    metadata={
                        "generated": True,
                        "processing_steps": processing_steps,
                        "generation_metadata": metadata,
                    },
                    source_image=str(temp_path) if temp_path else None,
                )
                
                saved_question = question_service.create_question(question_data)
                question_id = saved_question.id
                saved_class_id = class_id
                
                logger.info(f"Saved generated question {question_id} to class {class_id}")
                
            except ValueError as e:
                # Class not found - log but don't fail the request
                logger.warning(f"Failed to save question to class {class_id}: {e}")
            except Exception as e:
                # Log error but don't fail the request
                logger.error(f"Error saving question to class: {e}", exc_info=True)

        return GenerateResponse(
            question=question,
            metadata=metadata,
            processing_steps=processing_steps,
            question_id=question_id,
            class_id=saved_class_id,
            references_used=references_used,
        )

    except HTTPException:
        raise
    except Exception as e:
        from app.config import settings
        from app.utils.error_utils import get_safe_error_detail

        logger.error(f"Question generation failed: {str(e)}", exc_info=True)
        is_production = settings.environment.lower() == "production"
        # Sanitize the full error message, not just the exception
        full_error_msg = f"Question generation failed: {str(e)}"
        from app.utils.error_utils import sanitize_error_message
        safe_detail = sanitize_error_message(full_error_msg, is_production)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=safe_detail,
        ) from e
    finally:
        # Clean up temporary file
        if temp_path:
            cleanup_temp_file(temp_path)

