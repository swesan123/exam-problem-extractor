"""Question management API endpoints."""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.question_models import (
    QuestionCreate,
    QuestionListResponse,
    QuestionResponse,
    QuestionUpdate,
)
from app.services.question_service import QuestionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/questions", tags=["questions"])


@router.get("", response_model=QuestionListResponse, status_code=status.HTTP_200_OK)
async def list_questions(
    class_id: Optional[str] = Query(None, description="Filter by class ID"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=100, description="Maximum number of records to return"),
    db: Session = Depends(get_db),
):
    """
    List all questions with optional class filter and pagination.

    Args:
        class_id: Optional class ID to filter by
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session

    Returns:
        List of questions with total count
    """
    try:
        service = QuestionService(db)
        questions, total = service.list_questions(class_id=class_id, skip=skip, limit=limit)

        question_responses = [QuestionResponse.model_validate(q) for q in questions]

        return QuestionListResponse(
            questions=question_responses,
            total=total,
            skip=skip,
            limit=limit,
        )

    except Exception as e:
        logger.error(f"Failed to list questions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list questions: {str(e)}",
        ) from e


@router.get("/classes/{class_id}/questions", response_model=QuestionListResponse, status_code=status.HTTP_200_OK)
async def list_class_questions(
    class_id: str,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=100, description="Maximum number of records to return"),
    db: Session = Depends(get_db),
):
    """
    List all questions for a specific class.

    Args:
        class_id: Class ID
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session

    Returns:
        List of questions for the class
    """
    try:
        service = QuestionService(db)
        questions, total = service.list_questions(class_id=class_id, skip=skip, limit=limit)

        question_responses = [QuestionResponse.model_validate(q) for q in questions]

        return QuestionListResponse(
            questions=question_responses,
            total=total,
            skip=skip,
            limit=limit,
        )

    except Exception as e:
        logger.error(f"Failed to list class questions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list class questions: {str(e)}",
        ) from e


@router.post("/classes/{class_id}/questions", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED)
async def create_question(
    class_id: str,
    question_data: QuestionCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new question for a class.

    Args:
        class_id: Class ID (must match question_data.class_id)
        question_data: Question creation data
        db: Database session

    Returns:
        Created question
    """
    try:
        # Validate class_id matches
        if question_data.class_id != class_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Class ID mismatch: path parameter '{class_id}' != body '{question_data.class_id}'",
            )

        service = QuestionService(db)
        new_question = service.create_question(question_data)

        # Map question_metadata to metadata for response
        return QuestionResponse(
            id=new_question.id,
            class_id=new_question.class_id,
            question_text=new_question.question_text,
            solution=new_question.solution,
            metadata=new_question.question_metadata or {},
            source_image=new_question.source_image,
            created_at=new_question.created_at,
            updated_at=new_question.updated_at,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create question: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create question: {str(e)}",
        ) from e


@router.get("/{question_id}", response_model=QuestionResponse, status_code=status.HTTP_200_OK)
async def get_question(
    question_id: str,
    db: Session = Depends(get_db),
):
    """
    Get a question by ID.

    Args:
        question_id: Question ID
        db: Database session

    Returns:
        Question details
    """
    try:
        service = QuestionService(db)
        question = service.get_question(question_id)

        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Question with ID '{question_id}' not found",
            )

        # Map question_metadata to metadata for response
        return QuestionResponse(
            id=question.id,
            class_id=question.class_id,
            question_text=question.question_text,
            solution=question.solution,
            metadata=question.question_metadata or {},
            source_image=question.source_image,
            created_at=question.created_at,
            updated_at=question.updated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get question: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get question: {str(e)}",
        ) from e


@router.put("/{question_id}", response_model=QuestionResponse, status_code=status.HTTP_200_OK)
async def update_question(
    question_id: str,
    question_data: QuestionUpdate,
    db: Session = Depends(get_db),
):
    """
    Update a question.

    Args:
        question_id: Question ID
        question_data: Question update data
        db: Database session

    Returns:
        Updated question
    """
    try:
        service = QuestionService(db)
        updated_question = service.update_question(question_id, question_data)

        if not updated_question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Question with ID '{question_id}' not found",
            )

        # Map question_metadata to metadata for response
        return QuestionResponse(
            id=updated_question.id,
            class_id=updated_question.class_id,
            question_text=updated_question.question_text,
            solution=updated_question.solution,
            metadata=updated_question.question_metadata or {},
            source_image=updated_question.source_image,
            created_at=updated_question.created_at,
            updated_at=updated_question.updated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update question: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update question: {str(e)}",
        ) from e


@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(
    question_id: str,
    db: Session = Depends(get_db),
):
    """
    Delete a question.

    Args:
        question_id: Question ID
        db: Database session

    Returns:
        No content on success
    """
    try:
        service = QuestionService(db)
        deleted = service.delete_question(question_id)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Question with ID '{question_id}' not found",
            )

        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete question: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete question: {str(e)}",
        ) from e
