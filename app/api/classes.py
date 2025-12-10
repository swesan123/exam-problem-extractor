"""Class management API endpoints."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Question
from app.models.class_models import (
    ClassCreate,
    ClassListResponse,
    ClassResponse,
    ClassUpdate,
)
from app.services.class_service import ClassService
from app.services.export_service import ExportFormat, ExportService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/classes", tags=["classes"])


@router.get("", response_model=ClassListResponse, status_code=status.HTTP_200_OK)
async def list_classes(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=100, description="Maximum number of records to return"),
    db: Session = Depends(get_db),
):
    """
    List all classes with pagination.

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session

    Returns:
        List of classes with total count
    """
    try:
        service = ClassService(db)
        classes, total = service.list_classes(skip=skip, limit=limit)

        # Convert to response models with question counts
        class_responses = []
        for class_obj in classes:
            class_data = service.get_class_with_question_count(class_obj.id)
            if class_data:
                class_responses.append(ClassResponse(**class_data))

        return ClassListResponse(classes=class_responses, total=total)

    except Exception as e:
        logger.error(f"Failed to list classes: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list classes: {str(e)}",
        ) from e


@router.post("", response_model=ClassResponse, status_code=status.HTTP_201_CREATED)
async def create_class(
    class_data: ClassCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new class.

    Args:
        class_data: Class creation data
        db: Database session

    Returns:
        Created class
    """
    try:
        service = ClassService(db)
        new_class = service.create_class(class_data)

        # Get with question count
        class_data_response = service.get_class_with_question_count(new_class.id)
        if not class_data_response:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve created class",
            )

        return ClassResponse(**class_data_response)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Failed to create class: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create class: {str(e)}",
        ) from e


@router.get("/{class_id}", response_model=ClassResponse, status_code=status.HTTP_200_OK)
async def get_class(
    class_id: str,
    db: Session = Depends(get_db),
):
    """
    Get a class by ID.

    Args:
        class_id: Class ID
        db: Database session

    Returns:
        Class details
    """
    try:
        service = ClassService(db)
        class_data = service.get_class_with_question_count(class_id)

        if not class_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Class with ID '{class_id}' not found",
            )

        return ClassResponse(**class_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get class: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get class: {str(e)}",
        ) from e


@router.put("/{class_id}", response_model=ClassResponse, status_code=status.HTTP_200_OK)
async def update_class(
    class_id: str,
    class_data: ClassUpdate,
    db: Session = Depends(get_db),
):
    """
    Update a class.

    Args:
        class_id: Class ID
        class_data: Class update data
        db: Database session

    Returns:
        Updated class
    """
    try:
        service = ClassService(db)
        updated_class = service.update_class(class_id, class_data)

        if not updated_class:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Class with ID '{class_id}' not found",
            )

        # Get with question count
        class_data_response = service.get_class_with_question_count(class_id)
        if not class_data_response:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve updated class",
            )

        return ClassResponse(**class_data_response)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Failed to update class: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update class: {str(e)}",
        ) from e


@router.delete("/{class_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_class(
    class_id: str,
    db: Session = Depends(get_db),
):
    """
    Delete a class.

    Args:
        class_id: Class ID
        db: Database session

    Returns:
        No content on success
    """
    try:
        service = ClassService(db)
        deleted = service.delete_class(class_id)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Class with ID '{class_id}' not found",
            )

        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete class: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete class: {str(e)}",
        ) from e


@router.get("/{class_id}/export", status_code=status.HTTP_200_OK)
async def export_class_questions(
    class_id: str,
    format: str = Query("txt", description="Export format (txt, pdf, docx, json)"),
    include_solutions: bool = Query(False, description="Include solutions in export"),
    db: Session = Depends(get_db),
):
    """
    Export all questions from a class to a file.

    Args:
        class_id: Class ID
        format: Export format (txt, pdf, docx, json)
        include_solutions: Whether to include solutions
        db: Database session

    Returns:
        File download response
    """
    try:
        # Validate class exists
        service = ClassService(db)
        class_obj = service.get_class(class_id)
        if not class_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Class with ID '{class_id}' not found",
            )

        # Get all questions for the class
        questions = db.query(Question).filter(Question.class_id == class_id).all()

        if not questions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No questions found for class '{class_id}'",
            )

        # Validate format
        try:
            export_format = ExportFormat(format.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported format '{format}'. Supported formats: txt, pdf, docx, json",
            )

        # Export questions
        export_service = ExportService()
        content, content_type, file_ext = export_service.export_questions(
            questions, export_format, include_solutions
        )

        # Generate filename
        filename = f"{class_obj.name.replace(' ', '_')}_questions.{file_ext}"

        # Return file response
        return Response(
            content=content,
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Failed to export class questions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export questions: {str(e)}",
        ) from e

