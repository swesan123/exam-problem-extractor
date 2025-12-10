<<<<<<< HEAD
"""Service for question management operations."""
import uuid
import logging
from typing import Optional
=======
"""Service for managing questions."""
import logging
import uuid
from typing import Optional

>>>>>>> main
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.models import Question, Class
from app.models.question_models import QuestionCreate, QuestionUpdate

logger = logging.getLogger(__name__)


class QuestionService:
<<<<<<< HEAD
    """Service for managing questions."""
=======
    """Service for question management operations."""
>>>>>>> main

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
<<<<<<< HEAD
        # Verify class exists
=======
        # Validate class exists
>>>>>>> main
        class_obj = self.db.query(Class).filter(Class.id == question_data.class_id).first()
        if not class_obj:
            raise ValueError(f"Class with ID '{question_data.class_id}' not found")

<<<<<<< HEAD
        # Generate unique ID
        question_id = f"q_{uuid.uuid4().hex[:12]}"

        # Create question
        new_question = Question(
            id=question_id,
=======
        # Create question
        question = Question(
            id=f"q_{uuid.uuid4().hex[:12]}",
>>>>>>> main
            class_id=question_data.class_id,
            question_text=question_data.question_text,
            solution=question_data.solution,
            metadata=question_data.metadata or {},
            source_image=question_data.source_image,
        )

<<<<<<< HEAD
        self.db.add(new_question)
        self.db.commit()
        self.db.refresh(new_question)

        logger.info(f"Created question: {question_id} in class: {question_data.class_id}")
        return new_question
=======
        self.db.add(question)
        self.db.commit()
        self.db.refresh(question)

        logger.info(f"Created question {question.id} for class {question_data.class_id}")
        return question
>>>>>>> main

    def get_question(self, question_id: str) -> Optional[Question]:
        """
        Get a question by ID.

        Args:
            question_id: Question ID

        Returns:
            Question if found, None otherwise
        """
        return self.db.query(Question).filter(Question.id == question_id).first()

<<<<<<< HEAD
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
            Tuple of (list of questions, total count)
        """
        query = self.db.query(Question)
        
        if class_id:
            query = query.filter(Question.class_id == class_id)

        total = query.count()
        questions = query.offset(skip).limit(limit).all()
        
        return questions, total

=======
>>>>>>> main
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
            question.metadata = question_data.metadata
<<<<<<< HEAD
        if question_data.source_image is not None:
            question.source_image = question_data.source_image
=======
>>>>>>> main

        self.db.commit()
        self.db.refresh(question)

<<<<<<< HEAD
        logger.info(f"Updated question: {question_id}")
=======
        logger.info(f"Updated question {question_id}")
>>>>>>> main
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

<<<<<<< HEAD
        logger.info(f"Deleted question: {question_id}")
        return True

=======
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

>>>>>>> main
