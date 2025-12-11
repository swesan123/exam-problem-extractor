"""Integration tests for export API endpoint."""

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


@pytest.fixture
def sample_questions(db_session: Session, sample_class: Class):
    """Create sample questions for testing."""
    from datetime import datetime

    questions = [
        Question(
            id="q1",
            class_id=sample_class.id,
            question_text="What is 2 + 2?",
            solution="4",
            metadata={"source": "test"},
            created_at=datetime.now(),
        ),
        Question(
            id="q2",
            class_id=sample_class.id,
            question_text="What is the capital of France?",
            solution="Paris",
            metadata={"source": "test"},
            created_at=datetime.now(),
        ),
    ]
    db_session.add_all(questions)
    db_session.commit()
    return questions


def test_export_txt(client: TestClient, sample_class: Class, sample_questions):
    """Test export endpoint with TXT format."""
    response = client.get(
        f"/api/classes/{sample_class.id}/export?format=txt&include_solutions=false"
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/plain; charset=utf-8"
    assert "attachment" in response.headers["content-disposition"]
    assert "Test_Class_questions.txt" in response.headers["content-disposition"]
    assert b"EXAM QUESTIONS" in response.content
    assert b"What is 2 + 2?" in response.content
    assert b"4" not in response.content  # Solutions not included


def test_export_txt_with_solutions(
    client: TestClient, sample_class: Class, sample_questions
):
    """Test export endpoint with TXT format including solutions."""
    response = client.get(
        f"/api/classes/{sample_class.id}/export?format=txt&include_solutions=true"
    )

    assert response.status_code == 200
    assert b"EXAM QUESTIONS" in response.content
    assert b"Solution:" in response.content
    assert b"4" in response.content
    assert b"Paris" in response.content


def test_export_json(client: TestClient, sample_class: Class, sample_questions):
    """Test export endpoint with JSON format."""
    response = client.get(
        f"/api/classes/{sample_class.id}/export?format=json&include_solutions=false"
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    data = response.json()
    assert "questions" in data
    assert "total" in data
    assert data["total"] == 2


def test_export_pdf(client: TestClient, sample_class: Class, sample_questions):
    """Test export endpoint with PDF format."""
    response = client.get(
        f"/api/classes/{sample_class.id}/export?format=pdf&include_solutions=false"
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


def test_export_docx(client: TestClient, sample_class: Class, sample_questions):
    """Test export endpoint with DOCX format."""
    response = client.get(
        f"/api/classes/{sample_class.id}/export?format=docx&include_solutions=false"
    )

    assert response.status_code == 200
    assert "wordprocessingml" in response.headers["content-type"]
    assert response.content.startswith(b"PK")


def test_export_invalid_class(client: TestClient):
    """Test export endpoint with invalid class ID."""
    response = client.get("/api/classes/nonexistent/export?format=txt")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_export_class_without_questions(client: TestClient, sample_class: Class):
    """Test export endpoint for class with no questions."""
    response = client.get(f"/api/classes/{sample_class.id}/export?format=txt")

    assert response.status_code == 404
    assert "no questions" in response.json()["detail"].lower()


def test_export_invalid_format(
    client: TestClient, sample_class: Class, sample_questions
):
    """Test export endpoint with invalid format."""
    response = client.get(f"/api/classes/{sample_class.id}/export?format=invalid")

    assert response.status_code == 400
    assert "unsupported format" in response.json()["detail"].lower()
