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
        description="Test Description",
        subject="Test Subject"
    )
    db_session.add(test_class)
    db_session.commit()
    db_session.refresh(test_class)
    return test_class


@pytest.fixture
def question_service(db_session: Session):
    """Create a question service instance."""
    return QuestionService(db_session)


def test_create_question_success(question_service: QuestionService, sample_class: Class):
    """Test creating a question successfully."""
    question_data = QuestionCreate(
        class_id=sample_class.id,
        question_text="What is 2+2?",
        solution="4",
        metadata={"difficulty": "easy"}
    )
    
    created_question = question_service.create_question(question_data)
    
    assert created_question.id is not None
    assert created_question.class_id == sample_class.id
    assert created_question.question_text == "What is 2+2?"
    assert created_question.solution == "4"
    assert created_question.metadata == {"difficulty": "easy"}


def test_create_question_invalid_class(question_service: QuestionService):
    """Test creating a question with invalid class ID fails."""
    question_data = QuestionCreate(
        class_id="nonexistent_class",
        question_text="Test question"
    )
    
    with pytest.raises(ValueError, match="not found"):
        question_service.create_question(question_data)


def test_get_question_success(question_service: QuestionService, sample_class: Class):
    """Test getting a question by ID."""
    question_data = QuestionCreate(
        class_id=sample_class.id,
        question_text="Test question"
    )
    created = question_service.create_question(question_data)
    
    retrieved = question_service.get_question(created.id)
    
    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.question_text == "Test question"


def test_get_question_not_found(question_service: QuestionService):
    """Test getting a non-existent question."""
    result = question_service.get_question("nonexistent_id")
    assert result is None


def test_list_questions_all(question_service: QuestionService, sample_class: Class):
    """Test listing all questions."""
    # Create multiple questions
    for i in range(5):
        question_data = QuestionCreate(
            class_id=sample_class.id,
            question_text=f"Question {i}"
        )
        question_service.create_question(question_data)
    
    questions, total = question_service.list_questions()
    
    assert len(questions) == 5
    assert total == 5


def test_list_questions_by_class(question_service: QuestionService, db_session: Session):
    """Test listing questions filtered by class."""
    # Create two classes
    class1 = Class(id="class_1", name="Class 1")
    class2 = Class(id="class_2", name="Class 2")
    db_session.add_all([class1, class2])
    db_session.commit()
    
    # Create questions for each class
    for i in range(3):
        question_data = QuestionCreate(
            class_id="class_1",
            question_text=f"Class 1 Question {i}"
        )
        question_service.create_question(question_data)
    
    for i in range(2):
        question_data = QuestionCreate(
            class_id="class_2",
            question_text=f"Class 2 Question {i}"
        )
        question_service.create_question(question_data)
    
    # List questions for class_1
    questions, total = question_service.list_questions(class_id="class_1")
    assert len(questions) == 3
    assert total == 3
    assert all(q.class_id == "class_1" for q in questions)


def test_list_questions_pagination(question_service: QuestionService, sample_class: Class):
    """Test listing questions with pagination."""
    # Create multiple questions
    for i in range(10):
        question_data = QuestionCreate(
            class_id=sample_class.id,
            question_text=f"Question {i}"
        )
        question_service.create_question(question_data)
    
    questions, total = question_service.list_questions(skip=0, limit=5)
    assert len(questions) == 5
    assert total == 10
    
    questions, total = question_service.list_questions(skip=5, limit=5)
    assert len(questions) == 5
    assert total == 10


def test_update_question_success(question_service: QuestionService, sample_class: Class):
    """Test updating a question."""
    question_data = QuestionCreate(
        class_id=sample_class.id,
        question_text="Original question"
    )
    created = question_service.create_question(question_data)
    
    update_data = QuestionUpdate(
        question_text="Updated question",
        solution="Updated solution"
    )
    updated = question_service.update_question(created.id, update_data)
    
    assert updated is not None
    assert updated.question_text == "Updated question"
    assert updated.solution == "Updated solution"


def test_update_question_not_found(question_service: QuestionService):
    """Test updating a non-existent question."""
    update_data = QuestionUpdate(question_text="New text")
    result = question_service.update_question("nonexistent_id", update_data)
    assert result is None


def test_delete_question_success(question_service: QuestionService, sample_class: Class):
    """Test deleting a question."""
    question_data = QuestionCreate(
        class_id=sample_class.id,
        question_text="To Delete"
    )
    created = question_service.create_question(question_data)
    
    result = question_service.delete_question(created.id)
    assert result is True
    
    # Verify deleted
    retrieved = question_service.get_question(created.id)
    assert retrieved is None


def test_delete_question_not_found(question_service: QuestionService):
    """Test deleting a non-existent question."""
    result = question_service.delete_question("nonexistent_id")
    assert result is False

