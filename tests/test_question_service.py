"""Tests for question service."""
import pytest
from sqlalchemy.orm import Session

from app.db.models import Class, Question
from app.db.database import Base, engine, SessionLocal
from app.models.question_models import QuestionCreate, QuestionUpdate
from app.services.question_service import QuestionService


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
def sample_class(db_session: Session):
    """Create a sample class for testing."""
    test_class = Class(
        id="test_class_1",
        name="Test Class",
        description="Test Description"
    )
    db_session.add(test_class)
    db_session.commit()
    return test_class


@pytest.fixture
def question_service(db_session: Session):
    """Create a question service instance."""
    return QuestionService(db_session)


def test_create_question(question_service: QuestionService, sample_class: Class):
    """Test creating a question."""
    question_data = QuestionCreate(
        class_id=sample_class.id,
        question_text="What is 2 + 2?",
        solution="4",
        metadata={"source": "test"},
    )
    
    question = question_service.create_question(question_data)
    
    assert question.id.startswith("q_")
    assert question.class_id == sample_class.id
    assert question.question_text == "What is 2 + 2?"
    assert question.solution == "4"
    assert question.question_metadata == {"source": "test"}


def test_create_question_invalid_class(question_service: QuestionService):
    """Test creating a question with invalid class ID."""
    question_data = QuestionCreate(
        class_id="nonexistent",
        question_text="Test question",
    )
    
    with pytest.raises(ValueError, match="not found"):
        question_service.create_question(question_data)


def test_get_question(question_service: QuestionService, sample_class: Class):
    """Test getting a question by ID."""
    # Create a question first
    question_data = QuestionCreate(
        class_id=sample_class.id,
        question_text="Test question",
    )
    created = question_service.create_question(question_data)
    
    # Get it
    retrieved = question_service.get_question(created.id)
    
    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.question_text == "Test question"


def test_get_question_not_found(question_service: QuestionService):
    """Test getting a non-existent question."""
    question = question_service.get_question("nonexistent")
    assert question is None


def test_update_question(question_service: QuestionService, sample_class: Class):
    """Test updating a question."""
    # Create a question
    question_data = QuestionCreate(
        class_id=sample_class.id,
        question_text="Original question",
        solution="Original solution",
    )
    created = question_service.create_question(question_data)
    
    # Update it
    update_data = QuestionUpdate(
        question_text="Updated question",
        solution="Updated solution",
    )
    updated = question_service.update_question(created.id, update_data)
    
    assert updated is not None
    assert updated.question_text == "Updated question"
    assert updated.solution == "Updated solution"


def test_update_question_not_found(question_service: QuestionService):
    """Test updating a non-existent question."""
    update_data = QuestionUpdate(question_text="Updated")
    result = question_service.update_question("nonexistent", update_data)
    assert result is None


def test_delete_question(question_service: QuestionService, sample_class: Class):
    """Test deleting a question."""
    # Create a question
    question_data = QuestionCreate(
        class_id=sample_class.id,
        question_text="To be deleted",
    )
    created = question_service.create_question(question_data)
    
    # Delete it
    deleted = question_service.delete_question(created.id)
    assert deleted is True
    
    # Verify it's gone
    retrieved = question_service.get_question(created.id)
    assert retrieved is None


def test_delete_question_not_found(question_service: QuestionService):
    """Test deleting a non-existent question."""
    deleted = question_service.delete_question("nonexistent")
    assert deleted is False


def test_list_questions(question_service: QuestionService, sample_class: Class):
    """Test listing questions."""
    # Create multiple questions
    for i in range(5):
        question_data = QuestionCreate(
            class_id=sample_class.id,
            question_text=f"Question {i}",
        )
        question_service.create_question(question_data)
    
    # List all
    questions, total = question_service.list_questions()
    assert total >= 5
    assert len(questions) >= 5


def test_list_questions_with_class_filter(question_service: QuestionService, db_session: Session):
    """Test listing questions filtered by class."""
    # Create two classes
    class1 = Class(id="class1", name="Class 1")
    class2 = Class(id="class2", name="Class 2")
    db_session.add_all([class1, class2])
    db_session.commit()
    
    # Create questions for each class
    for i in range(3):
        question_data = QuestionCreate(
            class_id="class1",
            question_text=f"Class1 Question {i}",
        )
        question_service.create_question(question_data)
    
    for i in range(2):
        question_data = QuestionCreate(
            class_id="class2",
            question_text=f"Class2 Question {i}",
        )
        question_service.create_question(question_data)
    
    # List questions for class1
    questions, total = question_service.list_questions(class_id="class1")
    assert total == 3
    assert len(questions) == 3
    assert all(q.class_id == "class1" for q in questions)


def test_list_questions_pagination(question_service: QuestionService, sample_class: Class):
    """Test listing questions with pagination."""
    # Create multiple questions
    for i in range(10):
        question_data = QuestionCreate(
            class_id=sample_class.id,
            question_text=f"Question {i}",
        )
        question_service.create_question(question_data)
    
    # Get first page
    questions, total = question_service.list_questions(skip=0, limit=5)
    assert total >= 10
    assert len(questions) == 5
    
    # Get second page
    questions2, total2 = question_service.list_questions(skip=5, limit=5)
    assert total2 == total
    assert len(questions2) == 5
    assert questions[0].id != questions2[0].id
