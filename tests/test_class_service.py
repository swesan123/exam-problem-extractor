"""Tests for class service."""
import pytest
from sqlalchemy.orm import Session

from app.db.models import Class, Question
from app.db.database import Base, engine, SessionLocal
from app.models.class_models import ClassCreate, ClassUpdate
from app.services.class_service import ClassService


@pytest.fixture
def db_session():
    """Create a test database session."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def class_service(db_session: Session):
    """Create a class service instance."""
    return ClassService(db_session)


def test_create_class_success(class_service: ClassService):
    """Test creating a class successfully."""
    class_data = ClassCreate(
        name="Mathematics 101",
        description="Introduction to Calculus",
        subject="Mathematics"
    )
    
    created_class = class_service.create_class(class_data)
    
    assert created_class.id is not None
    assert created_class.name == "Mathematics 101"
    assert created_class.description == "Introduction to Calculus"
    assert created_class.subject == "Mathematics"
    assert created_class.created_at is not None


def test_create_class_duplicate_name(class_service: ClassService):
    """Test creating a class with duplicate name fails."""
    class_data = ClassCreate(name="Test Class")
    class_service.create_class(class_data)
    
    # Try to create another with same name
    with pytest.raises(ValueError, match="already exists"):
        class_service.create_class(class_data)


def test_get_class_success(class_service: ClassService):
    """Test getting a class by ID."""
    class_data = ClassCreate(name="Test Class")
    created = class_service.create_class(class_data)
    
    retrieved = class_service.get_class(created.id)
    
    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.name == "Test Class"


def test_get_class_not_found(class_service: ClassService):
    """Test getting a non-existent class."""
    result = class_service.get_class("nonexistent_id")
    assert result is None


def test_list_classes(class_service: ClassService):
    """Test listing classes."""
    # Create multiple classes
    for i in range(5):
        class_data = ClassCreate(name=f"Class {i}")
        class_service.create_class(class_data)
    
    classes, total = class_service.list_classes()
    
    assert len(classes) == 5
    assert total == 5


def test_list_classes_pagination(class_service: ClassService):
    """Test listing classes with pagination."""
    # Create multiple classes
    for i in range(10):
        class_data = ClassCreate(name=f"Class {i}")
        class_service.create_class(class_data)
    
    classes, total = class_service.list_classes(skip=0, limit=5)
    assert len(classes) == 5
    assert total == 10
    
    classes, total = class_service.list_classes(skip=5, limit=5)
    assert len(classes) == 5
    assert total == 10


def test_update_class_success(class_service: ClassService):
    """Test updating a class."""
    class_data = ClassCreate(name="Original Name")
    created = class_service.create_class(class_data)
    
    update_data = ClassUpdate(name="Updated Name", description="New description")
    updated = class_service.update_class(created.id, update_data)
    
    assert updated is not None
    assert updated.name == "Updated Name"
    assert updated.description == "New description"


def test_update_class_not_found(class_service: ClassService):
    """Test updating a non-existent class."""
    update_data = ClassUpdate(name="New Name")
    result = class_service.update_class("nonexistent_id", update_data)
    assert result is None


def test_update_class_duplicate_name(class_service: ClassService):
    """Test updating to duplicate name fails."""
    class1 = class_service.create_class(ClassCreate(name="Class 1"))
    class2 = class_service.create_class(ClassCreate(name="Class 2"))
    
    # Try to rename class2 to class1's name
    update_data = ClassUpdate(name="Class 1")
    with pytest.raises(ValueError, match="already exists"):
        class_service.update_class(class2.id, update_data)


def test_delete_class_success(class_service: ClassService):
    """Test deleting a class."""
    class_data = ClassCreate(name="To Delete")
    created = class_service.create_class(class_data)
    
    result = class_service.delete_class(created.id)
    assert result is True
    
    # Verify deleted
    retrieved = class_service.get_class(created.id)
    assert retrieved is None


def test_delete_class_not_found(class_service: ClassService):
    """Test deleting a non-existent class."""
    result = class_service.delete_class("nonexistent_id")
    assert result is False


def test_get_class_with_question_count(class_service: ClassService, db_session: Session):
    """Test getting class with question count."""
    created = class_service.create_class(ClassCreate(name="Test Class"))
    
    # Add some questions
    for i in range(3):
        question = Question(
            id=f"q_{i}",
            class_id=created.id,
            question_text=f"Question {i}"
        )
        db_session.add(question)
    db_session.commit()
    
    class_data = class_service.get_class_with_question_count(created.id)
    
    assert class_data is not None
    assert class_data["question_count"] == 3
    assert class_data["id"] == created.id


def test_get_class_with_question_count_not_found(class_service: ClassService):
    """Test getting class with question count for non-existent class."""
    result = class_service.get_class_with_question_count("nonexistent_id")
    assert result is None

