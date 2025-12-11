"""Integration tests for reference content API endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import MagicMock, patch

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


@pytest.fixture
def sample_class(db_session: Session):
    """Create a sample class for testing."""
    test_class = Class(
        id="class_1",
        name="Test Class",
        description="Test Description",
        subject="Test Subject",
    )
    db_session.add(test_class)
    db_session.commit()
    db_session.refresh(test_class)
    return test_class


@pytest.fixture
def mock_embedding_service():
    """Create a mock embedding service."""
    with patch("app.api.reference_content.EmbeddingService") as mock_service_class:
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        yield mock_service


class TestListClassReferenceContent:
    """Test listing reference content by class."""

    def test_list_reference_content_success(
        self, client, mock_embedding_service, sample_class
    ):
        """Test successfully listing reference content for a class."""
        mock_embedding_service.list_embeddings_by_class.return_value = [
            {
                "chunk_id": "chunk_1",
                "text": "Sample text 1",
                "metadata": {"source": "test_exam", "class_id": "class_1"},
            },
            {
                "chunk_id": "chunk_2",
                "text": "Sample text 2",
                "metadata": {"source": "test_exam", "class_id": "class_1"},
            },
        ]

        response = client.get("/api/reference-content/classes/class_1")

        assert response.status_code == 200
        data = response.json()
        assert data["class_id"] == "class_1"
        assert len(data["items"]) == 2
        assert data["count"] == 2
        assert data["items"][0]["chunk_id"] == "chunk_1"

    def test_list_reference_content_empty(
        self, client, mock_embedding_service, sample_class
    ):
        """Test listing reference content when class has none."""
        mock_embedding_service.list_embeddings_by_class.return_value = []

        response = client.get("/api/reference-content/classes/class_1")

        assert response.status_code == 200
        data = response.json()
        assert data["class_id"] == "class_1"
        assert len(data["items"]) == 0
        assert data["count"] == 0

    def test_list_reference_content_class_not_found(
        self, client, mock_embedding_service
    ):
        """Test listing reference content for non-existent class."""
        response = client.get("/api/reference-content/classes/nonexistent_class")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_list_reference_content_service_error(
        self, client, mock_embedding_service, sample_class
    ):
        """Test handling service errors when listing reference content."""
        mock_embedding_service.list_embeddings_by_class.side_effect = Exception(
            "Service error"
        )

        response = client.get("/api/reference-content/classes/class_1")

        assert response.status_code == 500
        assert "Failed to list reference content" in response.json()["detail"]


class TestDeleteReferenceContent:
    """Test deleting reference content."""

    def test_delete_reference_content_success(self, client, mock_embedding_service):
        """Test successfully deleting reference content."""
        mock_embedding_service.delete_embedding.return_value = True

        response = client.delete("/api/reference-content/chunk_123")

        assert response.status_code == 204

    def test_delete_reference_content_not_found(self, client, mock_embedding_service):
        """Test deleting non-existent reference content."""
        mock_embedding_service.delete_embedding.return_value = False

        response = client.delete("/api/reference-content/chunk_999")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_delete_reference_content_service_error(
        self, client, mock_embedding_service
    ):
        """Test handling service errors when deleting reference content."""
        mock_embedding_service.delete_embedding.side_effect = Exception("Service error")

        response = client.delete("/api/reference-content/chunk_123")

        assert response.status_code == 500
        assert "Failed to delete reference content" in response.json()["detail"]
