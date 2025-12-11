"""Integration tests for class API endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.database import Base, SessionLocal, engine
from app.db.models import Class, Question
from app.main import app


@pytest.fixture
def db_session():
    """Create a test database session."""
    # Clean up before creating
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Clean up any existing data
        db.query(Question).delete()
        db.query(Class).delete()
        db.commit()
        yield db
    finally:
        db.rollback()
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


def test_list_classes_empty(client: TestClient):
    """Test listing classes when none exist."""
    response = client.get("/api/classes")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert len(data["classes"]) == 0


def test_create_class_success(client: TestClient):
    """Test creating a class successfully."""
    response = client.post(
        "/api/classes",
        json={
            "name": "Mathematics 101",
            "description": "Introduction to Calculus",
            "subject": "Mathematics",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Mathematics 101"
    assert data["description"] == "Introduction to Calculus"
    assert data["subject"] == "Mathematics"
    assert data["id"] is not None
    assert data["question_count"] == 0


def test_create_class_duplicate_name(client: TestClient):
    """Test creating a class with duplicate name fails."""
    client.post("/api/classes", json={"name": "Test Class"})

    response = client.post("/api/classes", json={"name": "Test Class"})
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_get_class_success(client: TestClient):
    """Test getting a class by ID."""
    create_response = client.post("/api/classes", json={"name": "Test Class"})
    class_id = create_response.json()["id"]

    response = client.get(f"/api/classes/{class_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == class_id
    assert data["name"] == "Test Class"


def test_get_class_not_found(client: TestClient):
    """Test getting a non-existent class."""
    response = client.get("/api/classes/nonexistent_id")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_update_class_success(client: TestClient):
    """Test updating a class."""
    create_response = client.post("/api/classes", json={"name": "Original Name"})
    class_id = create_response.json()["id"]

    response = client.put(
        f"/api/classes/{class_id}",
        json={"name": "Updated Name", "description": "New description"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["description"] == "New description"


def test_update_class_not_found(client: TestClient):
    """Test updating a non-existent class."""
    response = client.put("/api/classes/nonexistent_id", json={"name": "New Name"})
    assert response.status_code == 404


def test_delete_class_success(client: TestClient):
    """Test deleting a class."""
    create_response = client.post("/api/classes", json={"name": "To Delete"})
    class_id = create_response.json()["id"]

    response = client.delete(f"/api/classes/{class_id}")
    assert response.status_code == 204

    # Verify deleted
    get_response = client.get(f"/api/classes/{class_id}")
    assert get_response.status_code == 404


def test_delete_class_not_found(client: TestClient):
    """Test deleting a non-existent class."""
    response = client.delete("/api/classes/nonexistent_id")
    assert response.status_code == 404


def test_list_classes_pagination(client: TestClient):
    """Test listing classes with pagination."""
    # Create multiple classes
    for i in range(10):
        client.post("/api/classes", json={"name": f"Class {i}"})

    response = client.get("/api/classes?skip=0&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data["classes"]) == 5
    assert data["total"] == 10

    response = client.get("/api/classes?skip=5&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data["classes"]) == 5


def test_class_with_questions(client: TestClient, db_session: Session):
    """Test getting a class with question count."""
    create_response = client.post("/api/classes", json={"name": "Test Class"})
    class_id = create_response.json()["id"]

    # Add questions directly to database
    for i in range(3):
        question = Question(
            id=f"q_{i}", class_id=class_id, question_text=f"Question {i}"
        )
        db_session.add(question)
    db_session.commit()

    response = client.get(f"/api/classes/{class_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["question_count"] == 3
