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


class TestUploadReferenceContent:
    """Test uploading reference content with reference_type."""

    @pytest.fixture
    def sample_file(self):
        """Create a sample file for upload."""
        from io import BytesIO
        return ("test.pdf", BytesIO(b"fake pdf content"), "application/pdf")

    @pytest.fixture
    def mock_reference_processor(self):
        """Create a mock reference processor."""
        with patch("app.api.reference_content._processor") as mock_processor:
            yield mock_processor

    @pytest.fixture
    def mock_job_service(self):
        """Create a mock job service."""
        with patch("app.api.reference_content.JobService") as mock_service_class:
            mock_service = MagicMock()
            mock_job = MagicMock()
            mock_job.id = "job_123"
            mock_job.status = "pending"
            mock_service.create_job.return_value = mock_job
            mock_service_class.return_value = mock_service
            yield mock_service

    def test_upload_with_reference_type_assessment(
        self, client, sample_class, sample_file, mock_reference_processor, mock_job_service
    ):
        """Test upload with reference_type='assessment'."""
        files = [sample_file]
        data = {
            "class_id": "class_1",
            "reference_type": "assessment",
        }

        response = client.post(
            "/api/reference-content/upload",
            files=[("files", files[0])],
            data=data,
        )

        assert response.status_code == 202
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "pending"

        # Verify processor was called with reference_type in metadata
        mock_reference_processor.process_job.assert_called_once()
        call_args = mock_reference_processor.process_job.call_args
        metadata = call_args[0][2]  # Third positional argument
        assert metadata["reference_type"] == "assessment"
        assert metadata["class_id"] == "class_1"

    def test_upload_with_reference_type_lecture(
        self, client, sample_class, sample_file, mock_reference_processor, mock_job_service
    ):
        """Test upload with reference_type='lecture'."""
        files = [sample_file]
        data = {
            "class_id": "class_1",
            "reference_type": "lecture",
        }

        response = client.post(
            "/api/reference-content/upload",
            files=[("files", files[0])],
            data=data,
        )

        assert response.status_code == 202
        # Verify processor was called with reference_type in metadata
        call_args = mock_reference_processor.process_job.call_args
        metadata = call_args[0][2]
        assert metadata["reference_type"] == "lecture"

    def test_upload_with_custom_reference_type(
        self, client, sample_class, sample_file, mock_reference_processor, mock_job_service
    ):
        """Test upload with custom reference_type."""
        files = [sample_file]
        data = {
            "class_id": "class_1",
            "reference_type": "homework",
        }

        response = client.post(
            "/api/reference-content/upload",
            files=[("files", files[0])],
            data=data,
        )

        assert response.status_code == 202
        call_args = mock_reference_processor.process_job.call_args
        metadata = call_args[0][2]
        assert metadata["reference_type"] == "homework"

    def test_upload_without_reference_type(
        self, client, sample_class, sample_file, mock_reference_processor, mock_job_service
    ):
        """Test upload without reference_type (backward compatibility)."""
        files = [sample_file]
        data = {
            "class_id": "class_1",
        }

        response = client.post(
            "/api/reference-content/upload",
            files=[("files", files[0])],
            data=data,
        )

        assert response.status_code == 202
        call_args = mock_reference_processor.process_job.call_args
        metadata = call_args[0][2]
        # reference_type should be None if not provided
        assert metadata.get("reference_type") is None

    def test_original_filename_preserved_in_metadata(
        self, client, sample_class, sample_file, mock_reference_processor, mock_job_service
    ):
        """Test original filename preserved in metadata."""
        files = [sample_file]
        data = {
            "class_id": "class_1",
            "reference_type": "assessment",
        }

        response = client.post(
            "/api/reference-content/upload",
            files=[("files", files[0])],
            data=data,
        )

        assert response.status_code == 202
        # Verify file_info_list contains original filename
        call_args = mock_reference_processor.process_job.call_args
        file_info_list = call_args[0][1]  # Second positional argument
        assert len(file_info_list) == 1
        assert file_info_list[0][1] == "test.pdf"  # Original filename

    def test_multiple_files_with_same_reference_type(
        self, client, sample_class, mock_reference_processor, mock_job_service
    ):
        """Test multiple files with same reference_type."""
        from io import BytesIO
        files = [
            ("file1.pdf", BytesIO(b"content1"), "application/pdf"),
            ("file2.pdf", BytesIO(b"content2"), "application/pdf"),
        ]
        data = {
            "class_id": "class_1",
            "reference_type": "assessment",
        }

        response = client.post(
            "/api/reference-content/upload",
            files=[("files", f) for f in files],
            data=data,
        )

        assert response.status_code == 202
        call_args = mock_reference_processor.process_job.call_args
        metadata = call_args[0][2]
        assert metadata["reference_type"] == "assessment"
        file_info_list = call_args[0][1]
        assert len(file_info_list) == 2

    def test_job_creation_includes_reference_type(
        self, client, sample_class, sample_file, mock_reference_processor, mock_job_service
    ):
        """Test job creation includes reference_type."""
        files = [sample_file]
        data = {
            "class_id": "class_1",
            "reference_type": "lecture",
        }

        response = client.post(
            "/api/reference-content/upload",
            files=[("files", files[0])],
            data=data,
        )

        assert response.status_code == 202
        # Job service should be called (already mocked)
        assert mock_job_service.create_job.called

    def test_upload_with_special_characters_in_filename(
        self, client, sample_class, mock_reference_processor, mock_job_service
    ):
        """Test upload with special characters in filename."""
        from io import BytesIO
        files = [("test file (2024).pdf", BytesIO(b"content"), "application/pdf")]
        data = {
            "class_id": "class_1",
            "reference_type": "assessment",
        }

        response = client.post(
            "/api/reference-content/upload",
            files=[("files", files[0])],
            data=data,
        )

        assert response.status_code == 202
        call_args = mock_reference_processor.process_job.call_args
        file_info_list = call_args[0][1]
        assert file_info_list[0][1] == "test file (2024).pdf"

    def test_upload_with_long_filename(
        self, client, sample_class, mock_reference_processor, mock_job_service
    ):
        """Test upload with long filename."""
        from io import BytesIO
        long_filename = "a" * 200 + ".pdf"
        files = [(long_filename, BytesIO(b"content"), "application/pdf")]
        data = {
            "class_id": "class_1",
            "reference_type": "assessment",
        }

        response = client.post(
            "/api/reference-content/upload",
            files=[("files", files[0])],
            data=data,
        )

        assert response.status_code == 202
        call_args = mock_reference_processor.process_job.call_args
        file_info_list = call_args[0][1]
        assert file_info_list[0][1] == long_filename

    def test_upload_with_missing_filename_fallback(
        self, client, sample_class, mock_reference_processor, mock_job_service
    ):
        """Test upload with missing filename (fallback)."""
        from io import BytesIO
        files = [("", BytesIO(b"content"), "application/pdf")]
        data = {
            "class_id": "class_1",
            "reference_type": "assessment",
        }

        response = client.post(
            "/api/reference-content/upload",
            files=[("files", files[0])],
            data=data,
        )

        assert response.status_code == 202
        # Should still work, filename will be derived from temp file
        call_args = mock_reference_processor.process_job.call_args
        file_info_list = call_args[0][1]
        assert len(file_info_list) == 1
