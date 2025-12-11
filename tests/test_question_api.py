"""Integration tests for question API endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.database import Base, SessionLocal, engine
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


@pytest.fixture
def sample_class(db_session: Session):
    """Create a sample class for testing."""
    test_class = Class(
        id="test_class_1", name="Test Class", description="Test Description"
    )
    db_session.add(test_class)
    db_session.commit()
    return test_class


def test_list_questions(client: TestClient, sample_class: Class):
    """Test listing all questions."""
    response = client.get("/api/questions")

    assert response.status_code == 200
    data = response.json()
    assert "questions" in data
    assert "total" in data
    assert isinstance(data["questions"], list)


def test_list_class_questions(client: TestClient, sample_class: Class):
    """Test listing questions for a specific class."""
    response = client.get(f"/api/questions/classes/{sample_class.id}/questions")

    assert response.status_code == 200
    data = response.json()
    assert "questions" in data
    assert "total" in data


def test_create_question(client: TestClient, sample_class: Class):
    """Test creating a question."""
    question_data = {
        "class_id": sample_class.id,
        "question_text": "What is 2 + 2?",
        "solution": "4",
        "metadata": {"source": "test"},
    }

    response = client.post(
        f"/api/questions/classes/{sample_class.id}/questions", json=question_data
    )

    assert response.status_code == 201
    data = response.json()
    assert data["question_text"] == "What is 2 + 2?"
    assert data["solution"] == "4"
    assert data["class_id"] == sample_class.id
    assert data["id"].startswith("q_")


def test_create_question_class_mismatch(client: TestClient, sample_class: Class):
    """Test creating a question with class ID mismatch."""
    question_data = {
        "class_id": "different_class",
        "question_text": "Test question",
    }

    response = client.post(
        f"/api/questions/classes/{sample_class.id}/questions", json=question_data
    )

    assert response.status_code == 400
    assert "mismatch" in response.json()["detail"].lower()


def test_create_question_invalid_class(client: TestClient):
    """Test creating a question with invalid class ID."""
    question_data = {
        "class_id": "nonexistent",
        "question_text": "Test question",
    }

    response = client.post(
        "/api/questions/classes/nonexistent/questions", json=question_data
    )

    assert response.status_code == 400
    assert "not found" in response.json()["detail"].lower()


def test_get_question(client: TestClient, sample_class: Class):
    """Test getting a question by ID."""
    # Create a question first
    question_data = {
        "class_id": sample_class.id,
        "question_text": "Test question",
    }
    create_response = client.post(
        f"/api/questions/classes/{sample_class.id}/questions", json=question_data
    )
    question_id = create_response.json()["id"]

    # Get it
    response = client.get(f"/api/questions/{question_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == question_id
    assert data["question_text"] == "Test question"


def test_get_question_not_found(client: TestClient):
    """Test getting a non-existent question."""
    response = client.get("/api/questions/nonexistent")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_update_question(client: TestClient, sample_class: Class):
    """Test updating a question."""
    # Create a question
    question_data = {
        "class_id": sample_class.id,
        "question_text": "Original question",
        "solution": "Original solution",
    }
    create_response = client.post(
        f"/api/questions/classes/{sample_class.id}/questions", json=question_data
    )
    question_id = create_response.json()["id"]

    # Update it
    update_data = {
        "question_text": "Updated question",
        "solution": "Updated solution",
    }
    response = client.put(f"/api/questions/{question_id}", json=update_data)

    assert response.status_code == 200
    data = response.json()
    assert data["question_text"] == "Updated question"
    assert data["solution"] == "Updated solution"


def test_update_question_not_found(client: TestClient):
    """Test updating a non-existent question."""
    update_data = {"question_text": "Updated"}
    response = client.put("/api/questions/nonexistent", json=update_data)

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_delete_question(client: TestClient, sample_class: Class):
    """Test deleting a question."""
    # Create a question
    question_data = {
        "class_id": sample_class.id,
        "question_text": "To be deleted",
    }
    create_response = client.post(
        f"/api/questions/classes/{sample_class.id}/questions", json=question_data
    )
    question_id = create_response.json()["id"]

    # Delete it
    response = client.delete(f"/api/questions/{question_id}")

    assert response.status_code == 204

    # Verify it's gone
    get_response = client.get(f"/api/questions/{question_id}")
    assert get_response.status_code == 404


def test_delete_question_not_found(client: TestClient):
    """Test deleting a non-existent question."""
    response = client.delete("/api/questions/nonexistent")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_list_questions_pagination(client: TestClient, sample_class: Class):
    """Test listing questions with pagination."""
    # Create multiple questions
    for i in range(5):
        question_data = {
            "class_id": sample_class.id,
            "question_text": f"Question {i}",
        }
        client.post(
            f"/api/questions/classes/{sample_class.id}/questions", json=question_data
        )

    # Get first page
    response = client.get("/api/questions?skip=0&limit=3")
    assert response.status_code == 200
    data = response.json()
    assert len(data["questions"]) == 3
    assert data["skip"] == 0
    assert data["limit"] == 3

    # Get second page
    response2 = client.get("/api/questions?skip=3&limit=3")
    assert response2.status_code == 200
    data2 = response2.json()
    assert len(data2["questions"]) >= 2


def test_download_question_txt(client: TestClient, sample_class: Class):
    """Test downloading a question as TXT."""
    # Create a question first
    question_data = {
        "class_id": sample_class.id,
        "question_text": "Test question for download",
    }
    create_response = client.post(
        f"/api/questions/classes/{sample_class.id}/questions", json=question_data
    )
    question_id = create_response.json()["id"]

    response = client.get(f"/api/questions/{question_id}/download?format=txt")

    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "attachment" in response.headers["content-disposition"]
    assert "Test question for download" in response.text


def test_download_question_pdf(client: TestClient, sample_class: Class):
    """Test downloading a question as PDF."""
    # Create a question first
    question_data = {
        "class_id": sample_class.id,
        "question_text": "Test question for PDF download",
    }
    create_response = client.post(
        f"/api/questions/classes/{sample_class.id}/questions", json=question_data
    )
    question_id = create_response.json()["id"]

    response = client.get(f"/api/questions/{question_id}/download?format=pdf")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers["content-disposition"]


def test_download_question_with_solution(client: TestClient, sample_class: Class):
    """Test downloading a question with solution."""
    # Create a question first
    question_data = {
        "class_id": sample_class.id,
        "question_text": "Test question with solution",
    }
    create_response = client.post(
        f"/api/questions/classes/{sample_class.id}/questions", json=question_data
    )
    question_id = create_response.json()["id"]

    # Update question to have a solution
    client.put(
        f"/api/questions/{question_id}",
        json={"solution": "Test solution"},
    )

    response = client.get(
        f"/api/questions/{question_id}/download?format=txt&include_solution=true"
    )

    assert response.status_code == 200
    assert "Test solution" in response.text


def test_download_question_invalid_format(client: TestClient, sample_class: Class):
    """Test downloading with invalid format."""
    # Create a question first
    question_data = {
        "class_id": sample_class.id,
        "question_text": "Test question",
    }
    create_response = client.post(
        f"/api/questions/classes/{sample_class.id}/questions", json=question_data
    )
    question_id = create_response.json()["id"]

    response = client.get(f"/api/questions/{question_id}/download?format=invalid")

    assert response.status_code == 400
    assert "Unsupported format" in response.json()["detail"]


def test_download_question_not_found(client: TestClient):
    """Test downloading non-existent question."""
    response = client.get("/api/questions/nonexistent/download?format=txt")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
