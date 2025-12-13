"""Mock exam management API endpoints."""

import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import MockExam, Question
from app.services.class_service import ClassService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/mock-exams", tags=["mock-exams"])


class MockExamResponse(BaseModel):
    """Response model for mock exam."""

    id: str
    class_id: str
    title: Optional[str] = None
    instructions: Optional[str] = None
    exam_format: Optional[str] = None
    weighting_rules: Optional[Dict] = Field(default_factory=dict)
    exam_metadata: Optional[Dict] = Field(default_factory=dict)
    questions: List[Dict] = Field(default_factory=list)
    created_at: str
    updated_at: str

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "mock_exam_123",
                "class_id": "class_123",
                "title": "Midterm Practice Exam",
                "instructions": "Answer all questions",
                "exam_format": "5 multiple choice, 3 short answer",
                "weighting_rules": {"pre_midterm_weight": 1.0, "post_midterm_weight": 2.0},
                "questions": [],
            }
        }
    }


class MockExamUpdate(BaseModel):
    """Model for updating mock exam metadata."""

    title: Optional[str] = None
    instructions: Optional[str] = None
    exam_format: Optional[str] = None
    weighting_rules: Optional[Dict] = None
    exam_metadata: Optional[Dict] = None


class MockExamListResponse(BaseModel):
    """Response model for mock exam list."""

    mock_exams: List[MockExamResponse]
    total: int


@router.get("/{mock_exam_id}", response_model=MockExamResponse, status_code=status.HTTP_200_OK)
async def get_mock_exam(
    mock_exam_id: str,
    db: Session = Depends(get_db),
):
    """
    Get a mock exam by ID with all questions.

    Args:
        mock_exam_id: Mock exam ID
        db: Database session

    Returns:
        Mock exam with all questions
    """
    try:
        mock_exam = db.query(MockExam).filter(MockExam.id == mock_exam_id).first()

        if not mock_exam:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Mock exam with ID '{mock_exam_id}' not found",
            )

        # Get all questions for this mock exam
        questions = db.query(Question).filter(Question.mock_exam_id == mock_exam_id).all()

        # Convert questions to dict format
        questions_data = []
        for q in questions:
            questions_data.append({
                "id": q.id,
                "question_text": q.question_text,
                "solution": q.solution,
                "slideset": q.slideset,
                "slide": q.slide,
                "topic": q.topic,
                "user_confidence": q.user_confidence,
                "metadata": q.question_metadata or {},
                "created_at": q.created_at.isoformat() if q.created_at else None,
                "updated_at": q.updated_at.isoformat() if q.updated_at else None,
            })

        return MockExamResponse(
            id=mock_exam.id,
            class_id=mock_exam.class_id,
            title=mock_exam.title,
            instructions=mock_exam.instructions,
            exam_format=mock_exam.exam_format,
            weighting_rules=mock_exam.weighting_rules or {},
            exam_metadata=mock_exam.exam_metadata or {},
            questions=questions_data,
            created_at=mock_exam.created_at.isoformat() if mock_exam.created_at else "",
            updated_at=mock_exam.updated_at.isoformat() if mock_exam.updated_at else "",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get mock exam: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get mock exam: {str(e)}",
        ) from e


@router.get("/classes/{class_id}/mock-exams", response_model=MockExamListResponse, status_code=status.HTTP_200_OK)
async def list_class_mock_exams(
    class_id: str,
    db: Session = Depends(get_db),
):
    """
    List all mock exams for a specific class.

    Args:
        class_id: Class ID
        db: Database session

    Returns:
        List of mock exams for the class
    """
    try:
        # Validate class exists
        class_service = ClassService(db)
        class_obj = class_service.get_class(class_id)
        if not class_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Class with ID '{class_id}' not found",
            )

        # Get all mock exams for this class
        mock_exams = db.query(MockExam).filter(MockExam.class_id == class_id).all()

        # Convert to response format
        mock_exam_responses = []
        for mock_exam in mock_exams:
            # Get question count
            question_count = db.query(Question).filter(Question.mock_exam_id == mock_exam.id).count()

            mock_exam_responses.append(MockExamResponse(
                id=mock_exam.id,
                class_id=mock_exam.class_id,
                title=mock_exam.title,
                instructions=mock_exam.instructions,
                exam_format=mock_exam.exam_format,
                weighting_rules=mock_exam.weighting_rules or {},
                exam_metadata={
                    **(mock_exam.exam_metadata or {}),
                    "question_count": question_count,  # Add question count to metadata
                },
                questions=[],  # Don't include full questions in list view
                created_at=mock_exam.created_at.isoformat() if mock_exam.created_at else "",
                updated_at=mock_exam.updated_at.isoformat() if mock_exam.updated_at else "",
            ))

        return MockExamListResponse(
            mock_exams=mock_exam_responses,
            total=len(mock_exam_responses),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list mock exams: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list mock exams: {str(e)}",
        ) from e


@router.patch("/{mock_exam_id}", response_model=MockExamResponse, status_code=status.HTTP_200_OK)
async def update_mock_exam(
    mock_exam_id: str,
    update_data: MockExamUpdate,
    db: Session = Depends(get_db),
):
    """
    Update mock exam metadata.

    Args:
        mock_exam_id: Mock exam ID
        update_data: Update data
        db: Database session

    Returns:
        Updated mock exam
    """
    try:
        mock_exam = db.query(MockExam).filter(MockExam.id == mock_exam_id).first()

        if not mock_exam:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Mock exam with ID '{mock_exam_id}' not found",
            )

        # Update fields
        if update_data.title is not None:
            mock_exam.title = update_data.title
        if update_data.instructions is not None:
            mock_exam.instructions = update_data.instructions
        if update_data.exam_format is not None:
            mock_exam.exam_format = update_data.exam_format
        if update_data.weighting_rules is not None:
            mock_exam.weighting_rules = update_data.weighting_rules
        if update_data.exam_metadata is not None:
            mock_exam.exam_metadata = update_data.exam_metadata

        db.commit()
        db.refresh(mock_exam)

        # Get questions for response
        questions = db.query(Question).filter(Question.mock_exam_id == mock_exam_id).all()
        questions_data = []
        for q in questions:
            questions_data.append({
                "id": q.id,
                "question_text": q.question_text,
                "solution": q.solution,
                "slideset": q.slideset,
                "slide": q.slide,
                "topic": q.topic,
                "user_confidence": q.user_confidence,
                "metadata": q.question_metadata or {},
                "created_at": q.created_at.isoformat() if q.created_at else None,
                "updated_at": q.updated_at.isoformat() if q.updated_at else None,
            })

        return MockExamResponse(
            id=mock_exam.id,
            class_id=mock_exam.class_id,
            title=mock_exam.title,
            instructions=mock_exam.instructions,
            exam_format=mock_exam.exam_format,
            weighting_rules=mock_exam.weighting_rules or {},
            exam_metadata=mock_exam.exam_metadata or {},
            questions=questions_data,
            created_at=mock_exam.created_at.isoformat() if mock_exam.created_at else "",
            updated_at=mock_exam.updated_at.isoformat() if mock_exam.updated_at else "",
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update mock exam: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update mock exam: {str(e)}",
        ) from e
