"""Service for managing questions."""
import logging
import uuid
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.models import Question, Class
from app.models.question_models import QuestionCreate, QuestionUpdate

logger = logging.getLogger(__name__)


class QuestionService:
    """Service for question management operations."""

    def __init__(self, db: Session):
        """
        Initialize question service.

        Args:
            db: Database session
        """
        self.db = db

    def create_question(self, question_data: QuestionCreate) -> Question:
        """
        Create a new question.

        Args:
            question_data: Question creation data

        Returns:
            Created question

        Raises:
            ValueError: If class does not exist
        """
        # Validate class exists
        class_obj = self.db.query(Class).filter(Class.id == question_data.class_id).first()
        if not class_obj:
            raise ValueError(f"Class with ID '{question_data.class_id}' not found")

        # Create question
        question = Question(
            id=f"q_{uuid.uuid4().hex[:12]}",
            class_id=question_data.class_id,
            question_text=question_data.question_text,
            solution=question_data.solution,
            question_metadata=question_data.metadata or {},
            source_image=question_data.source_image,
        )

        self.db.add(question)
        self.db.commit()
        self.db.refresh(question)

        logger.info(f"Created question {question.id} for class {question_data.class_id}")
        return question

    def get_question(self, question_id: str) -> Optional[Question]:
        """
        Get a question by ID.

        Args:
            question_id: Question ID

        Returns:
            Question if found, None otherwise
        """
        return self.db.query(Question).filter(Question.id == question_id).first()

    def update_question(self, question_id: str, question_data: QuestionUpdate) -> Optional[Question]:
        """
        Update a question.

        Args:
            question_id: Question ID
            question_data: Question update data

        Returns:
            Updated question if found, None otherwise
        """
        question = self.get_question(question_id)
        if not question:
            return None

        # Update fields
        if question_data.question_text is not None:
            question.question_text = question_data.question_text
        if question_data.solution is not None:
            question.solution = question_data.solution
        if question_data.metadata is not None:
            question.question_metadata = question_data.metadata

        self.db.commit()
        self.db.refresh(question)

        logger.info(f"Updated question {question_id}")
        return question

    def delete_question(self, question_id: str) -> bool:
        """
        Delete a question.

        Args:
            question_id: Question ID

        Returns:
            True if deleted, False if not found
        """
        question = self.get_question(question_id)
        if not question:
            return False

        self.db.delete(question)
        self.db.commit()

        logger.info(f"Deleted question {question_id}")
        return True

    def list_questions(
        self, class_id: Optional[str] = None, skip: int = 0, limit: int = 100
    ) -> tuple[list[Question], int]:
        """
        List questions with optional class filter and pagination.

        Args:
            class_id: Optional class ID to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (questions list, total count)
        """
        query = self.db.query(Question)

        if class_id:
            query = query.filter(Question.class_id == class_id)

        # Get total count
        total = query.count()

        # Apply pagination
        questions = query.offset(skip).limit(limit).all()

        return questions, total
