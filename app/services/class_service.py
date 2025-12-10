"""Service for class management operations."""
import uuid
import logging
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.models import Class, Question
from app.models.class_models import ClassCreate, ClassUpdate

logger = logging.getLogger(__name__)


class ClassService:
    """Service for managing classes."""

    def __init__(self, db: Session):
        """
        Initialize class service.

        Args:
            db: Database session
        """
        self.db = db

    def create_class(self, class_data: ClassCreate) -> Class:
        """
        Create a new class.

        Args:
            class_data: Class creation data

        Returns:
            Created class

        Raises:
            ValueError: If class name already exists
        """
        # Check if class with same name already exists
        existing = self.db.query(Class).filter(Class.name == class_data.name).first()
        if existing:
            raise ValueError(f"Class with name '{class_data.name}' already exists")

        # Generate unique ID
        class_id = f"class_{uuid.uuid4().hex[:12]}"

        # Create class
        new_class = Class(
            id=class_id,
            name=class_data.name,
            description=class_data.description,
            subject=class_data.subject,
        )

        self.db.add(new_class)
        self.db.commit()
        self.db.refresh(new_class)

        logger.info(f"Created class: {class_id} - {class_data.name}")
        return new_class

    def get_class(self, class_id: str) -> Optional[Class]:
        """
        Get a class by ID.

        Args:
            class_id: Class ID

        Returns:
            Class if found, None otherwise
        """
        return self.db.query(Class).filter(Class.id == class_id).first()

    def list_classes(self, skip: int = 0, limit: int = 100) -> tuple[list[Class], int]:
        """
        List all classes with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (list of classes, total count)
        """
        total = self.db.query(func.count(Class.id)).scalar()
        classes = self.db.query(Class).offset(skip).limit(limit).all()
        return classes, total

    def update_class(self, class_id: str, class_data: ClassUpdate) -> Optional[Class]:
        """
        Update a class.

        Args:
            class_id: Class ID
            class_data: Class update data

        Returns:
            Updated class if found, None otherwise

        Raises:
            ValueError: If new name conflicts with existing class
        """
        class_obj = self.get_class(class_id)
        if not class_obj:
            return None

        # Check name conflict if name is being updated
        if class_data.name and class_data.name != class_obj.name:
            existing = self.db.query(Class).filter(Class.name == class_data.name).first()
            if existing:
                raise ValueError(f"Class with name '{class_data.name}' already exists")

        # Update fields
        if class_data.name is not None:
            class_obj.name = class_data.name
        if class_data.description is not None:
            class_obj.description = class_data.description
        if class_data.subject is not None:
            class_obj.subject = class_data.subject

        self.db.commit()
        self.db.refresh(class_obj)

        logger.info(f"Updated class: {class_id}")
        return class_obj

    def delete_class(self, class_id: str) -> bool:
        """
        Delete a class.

        Args:
            class_id: Class ID

        Returns:
            True if deleted, False if not found
        """
        class_obj = self.get_class(class_id)
        if not class_obj:
            return False

        self.db.delete(class_obj)
        self.db.commit()

        logger.info(f"Deleted class: {class_id}")
        return True

    def get_class_with_question_count(self, class_id: str) -> Optional[dict]:
        """
        Get a class with question count.

        Args:
            class_id: Class ID

        Returns:
            Class data with question count, None if not found
        """
        class_obj = self.get_class(class_id)
        if not class_obj:
            return None

        question_count = self.db.query(func.count(Question.id)).filter(
            Question.class_id == class_id
        ).scalar()

        return {
            "id": class_obj.id,
            "name": class_obj.name,
            "description": class_obj.description,
            "subject": class_obj.subject,
            "question_count": question_count,
            "created_at": class_obj.created_at,
            "updated_at": class_obj.updated_at,
        }

