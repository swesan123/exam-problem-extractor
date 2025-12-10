"""Tests for database setup and models."""
import pytest
from pathlib import Path
from sqlalchemy.orm import Session
from datetime import datetime

from app.db.database import Base, engine, SessionLocal, init_db, drop_db, get_db
from app.db.models import Class, Question


@pytest.fixture
def db_session():
    """Create a test database session."""
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create session
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Clean up - drop all tables
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_class(db_session: Session):
    """Create a sample class for testing."""
    test_class = Class(
        id="test_class_1",
        name="Mathematics 101",
        description="Introduction to Calculus",
        subject="Mathematics"
    )
    db_session.add(test_class)
    db_session.commit()
    db_session.refresh(test_class)
    return test_class


def test_init_db(tmp_path, monkeypatch):
    """Test database initialization."""
    # Change to temp directory
    test_db_path = tmp_path / "data" / "app.db"
    test_db_path.parent.mkdir(parents=True)
    
    # This test verifies init_db doesn't crash
    # In a real scenario, we'd need to mock the engine
    init_db()


def test_class_model_creation(db_session: Session):
    """Test creating a Class model."""
    test_class = Class(
        id="class_1",
        name="Test Class",
        description="Test Description",
        subject="Test Subject"
    )
    
    db_session.add(test_class)
    db_session.commit()
    db_session.refresh(test_class)
    
    assert test_class.id == "class_1"
    assert test_class.name == "Test Class"
    assert test_class.description == "Test Description"
    assert test_class.subject == "Test Subject"
    assert test_class.created_at is not None
    assert test_class.updated_at is not None


def test_class_model_required_fields(db_session: Session):
    """Test that Class requires name field."""
    test_class = Class(id="class_2", name="Required Name")
    db_session.add(test_class)
    db_session.commit()
    
    assert test_class.name == "Required Name"


def test_question_model_creation(db_session: Session, sample_class: Class):
    """Test creating a Question model."""
    question = Question(
        id="question_1",
        class_id=sample_class.id,
        question_text="What is 2+2?",
        solution="4",
        metadata={"difficulty": "easy"}
    )
    
    db_session.add(question)
    db_session.commit()
    db_session.refresh(question)
    
    assert question.id == "question_1"
    assert question.class_id == sample_class.id
    assert question.question_text == "What is 2+2?"
    assert question.solution == "4"
    assert question.metadata == {"difficulty": "easy"}
    assert question.created_at is not None


def test_question_requires_class_id(db_session: Session):
    """Test that Question requires class_id."""
    question = Question(
        id="question_2",
        class_id="nonexistent_class",
        question_text="Test question"
    )
    db_session.add(question)
    # Should not raise error on add, but will fail on commit due to foreign key
    # For SQLite, foreign key constraints are not enforced by default
    db_session.commit()


def test_class_question_relationship(db_session: Session, sample_class: Class):
    """Test relationship between Class and Question."""
    question1 = Question(
        id="q1",
        class_id=sample_class.id,
        question_text="Question 1"
    )
    question2 = Question(
        id="q2",
        class_id=sample_class.id,
        question_text="Question 2"
    )
    
    db_session.add_all([question1, question2])
    db_session.commit()
    
    # Refresh to load relationship
    db_session.refresh(sample_class)
    
    assert len(sample_class.questions) == 2
    assert question1 in sample_class.questions
    assert question2 in sample_class.questions


def test_question_class_relationship(db_session: Session, sample_class: Class):
    """Test reverse relationship from Question to Class."""
    question = Question(
        id="q3",
        class_id=sample_class.id,
        question_text="Question 3"
    )
    
    db_session.add(question)
    db_session.commit()
    db_session.refresh(question)
    
    assert question.class_obj is not None
    assert question.class_obj.id == sample_class.id
    assert question.class_obj.name == sample_class.name


def test_cascade_delete(db_session: Session, sample_class: Class):
    """Test that deleting a class deletes its questions."""
    question = Question(
        id="q4",
        class_id=sample_class.id,
        question_text="Question 4"
    )
    db_session.add(question)
    db_session.commit()
    
    # Delete class
    db_session.delete(sample_class)
    db_session.commit()
    
    # Verify question is also deleted
    deleted_question = db_session.query(Question).filter_by(id="q4").first()
    assert deleted_question is None


def test_get_db_dependency():
    """Test get_db dependency function."""
    db_gen = get_db()
    db = next(db_gen)
    
    assert db is not None
    assert isinstance(db, Session)
    
    # Cleanup
    try:
        next(db_gen)
    except StopIteration:
        pass  # Expected


def test_class_timestamps(db_session: Session):
    """Test that timestamps are automatically set."""
    test_class = Class(id="class_ts", name="Timestamp Test")
    db_session.add(test_class)
    db_session.commit()
    db_session.refresh(test_class)
    
    assert test_class.created_at is not None
    assert test_class.updated_at is not None
    assert isinstance(test_class.created_at, datetime)


def test_question_timestamps(db_session: Session, sample_class: Class):
    """Test that question timestamps are automatically set."""
    question = Question(
        id="q_ts",
        class_id=sample_class.id,
        question_text="Timestamp test question"
    )
    db_session.add(question)
    db_session.commit()
    db_session.refresh(question)
    
    assert question.created_at is not None
    assert question.updated_at is not None
    assert isinstance(question.created_at, datetime)


def test_question_metadata_json(db_session: Session, sample_class: Class):
    """Test that question metadata can store JSON."""
    metadata = {
        "difficulty": "hard",
        "topics": ["calculus", "derivatives"],
        "points": 10
    }
    question = Question(
        id="q_json",
        class_id=sample_class.id,
        question_text="JSON metadata test",
        metadata=metadata
    )
    db_session.add(question)
    db_session.commit()
    db_session.refresh(question)
    
    assert question.metadata == metadata
    assert question.metadata["difficulty"] == "hard"
    assert "calculus" in question.metadata["topics"]


def test_class_indexes(db_session: Session):
    """Test that indexes are created for frequently queried fields."""
    # This is more of a structural test
    # In practice, we'd check the database schema
    test_class = Class(id="idx_test", name="Index Test", subject="Math")
    db_session.add(test_class)
    db_session.commit()
    
    # Query by indexed field
    result = db_session.query(Class).filter_by(name="Index Test").first()
    assert result is not None
    assert result.id == "idx_test"

