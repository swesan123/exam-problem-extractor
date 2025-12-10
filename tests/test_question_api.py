"""Integration tests for question API endpoints."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.database import Base, engine, SessionLocal
from app.db.models import Class, Question
from app.main import app


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
def client(db_session):
    """Create a test client with database dependency override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    from app.db.database import get_db
    app.dependency_overrides[get_db] = override_get_db
    
    yield TestClient(app)
    
    app.dependency_overrides.clear()


def test_list_questions_empty(client: TestClient):
    """Test listing questions when none exist."""
    response = client.get("/api/questions")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert len(data["questions"]) == 0


def test_create_question_success(client: TestClient, sample_class: Class):
    """Test creating a question successfully."""
    response = client.post(
        f"/api/questions/classes/{sample_class.id}/questions",
        json={
            "class_id": sample_class.id,
            "question_text": "What is 2+2?",
            "solution": "4",
            "metadata": {"difficulty": "easy"}
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["question_text"] == "What is 2+2?"
    assert data["solution"] == "4"
    assert data["class_id"] == sample_class.id
    assert data["id"] is not None


def test_create_question_invalid_class(client: TestClient):
    """Test creating a question with invalid class ID fails."""
    response = client.post(
        "/api/questions/classes/nonexistent_class/questions",
        json={
            "class_id": "nonexistent_class",
            "question_text": "Test question"
        }
    )
    assert response.status_code == 400
    assert "not found" in response.json()["detail"]


def test_get_question_success(client: TestClient, sample_class: Class):
    """Test getting a question by ID."""
    create_response = client.post(
        f"/api/questions/classes/{sample_class.id}/questions",
        json={
            "class_id": sample_class.id,
            "question_text": "Test question"
        }
    )
    question_id = create_response.json()["id"]
    
    response = client.get(f"/api/questions/{question_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == question_id
    assert data["question_text"] == "Test question"


def test_get_question_not_found(client: TestClient):
    """Test getting a non-existent question."""
    response = client.get("/api/questions/nonexistent_id")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_update_question_success(client: TestClient, sample_class: Class):
    """Test updating a question."""
    create_response = client.post(
        f"/api/questions/classes/{sample_class.id}/questions",
        json={
            "class_id": sample_class.id,
            "question_text": "Original question"
        }
    )
    question_id = create_response.json()["id"]
    
    response = client.put(
        f"/api/questions/{question_id}",
        json={
            "question_text": "Updated question",
            "solution": "Updated solution"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["question_text"] == "Updated question"
    assert data["solution"] == "Updated solution"


def test_update_question_not_found(client: TestClient):
    """Test updating a non-existent question."""
    response = client.put(
        "/api/questions/nonexistent_id",
        json={"question_text": "New text"}
    )
    assert response.status_code == 404


def test_delete_question_success(client: TestClient, sample_class: Class):
    """Test deleting a question."""
    create_response = client.post(
        f"/api/questions/classes/{sample_class.id}/questions",
        json={
            "class_id": sample_class.id,
            "question_text": "To Delete"
        }
    )
    question_id = create_response.json()["id"]
    
    response = client.delete(f"/api/questions/{question_id}")
    assert response.status_code == 204
    
    # Verify deleted
    get_response = client.get(f"/api/questions/{question_id}")
    assert get_response.status_code == 404


def test_list_class_questions(client: TestClient, sample_class: Class):
    """Test listing questions for a specific class."""
    # Create questions
    for i in range(3):
        client.post(
            f"/api/questions/classes/{sample_class.id}/questions",
            json={
                "class_id": sample_class.id,
                "question_text": f"Question {i}"
            }
        )
    
    response = client.get(f"/api/questions/classes/{sample_class.id}/questions")
    assert response.status_code == 200
    data = response.json()
    assert len(data["questions"]) == 3
    assert data["total"] == 3
    assert all(q["class_id"] == sample_class.id for q in data["questions"])


def test_list_questions_pagination(client: TestClient, sample_class: Class):
    """Test listing questions with pagination."""
    # Create multiple questions
    for i in range(10):
        client.post(
            f"/api/questions/classes/{sample_class.id}/questions",
            json={
                "class_id": sample_class.id,
                "question_text": f"Question {i}"
            }
        )
    
    response = client.get("/api/questions?page=1&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data["questions"]) == 5
    assert data["total"] == 10
    assert data["page"] == 1
    assert data["limit"] == 5

