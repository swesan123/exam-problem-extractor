"""Integration tests for generation route with class-scoped retrieval."""

import json
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.database import Base, SessionLocal, engine
from app.db.models import Class
from app.main import app
from app.models.retrieval_models import RetrievedChunk


@pytest.fixture
def db_session():
    """Create a test database session."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
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
def mock_ocr_service():
    """Create a mock OCR service."""
    service = MagicMock()
    service.extract_text.return_value = "Extracted OCR text from image"
    return service


@pytest.fixture
def mock_retrieval_service():
    """Create a mock retrieval service."""
    service = MagicMock()
    return service


@pytest.fixture
def mock_generation_service():
    """Create a mock generation service."""
    service = MagicMock()
    service.generate_with_reference_types.return_value = {
        "question": "Generated question with references",
        "metadata": {"tokens_used": 100, "assessment_count": 2, "lecture_count": 2},
    }
    service.generate_question.return_value = "Generated question"
    service.generate_with_metadata.return_value = {
        "question": "Generated question",
        "metadata": {"tokens_used": 100},
    }
    return service


class TestGenerateWithClassScopedRetrieval:
    """Test generation with class-scoped retrieval."""

    def test_generation_with_class_id_retrieves_only_from_that_class(
        self, client, sample_class, mock_ocr_service, mock_retrieval_service, mock_generation_service
    ):
        """Test generation with class_id retrieves only from that class."""
        assessment_chunks = [
            RetrievedChunk(
                text="Assessment text 1",
                score=0.9,
                metadata={"class_id": "class_1", "source_file": "exam1.pdf", "reference_type": "assessment"},
                chunk_id="chunk_1",
            )
        ]
        lecture_chunks = [
            RetrievedChunk(
                text="Lecture text 1",
                score=0.85,
                metadata={"class_id": "class_1", "source_file": "lecture1.pdf", "reference_type": "lecture"},
                chunk_id="chunk_2",
            )
        ]

        mock_retrieval_service.retrieve_with_scores.side_effect = [
            assessment_chunks,
            lecture_chunks,
        ]

        with patch("app.routes.generate.OCRService", return_value=mock_ocr_service), patch(
            "app.routes.generate.RetrievalService", return_value=mock_retrieval_service
        ), patch("app.routes.generate.GenerationService", return_value=mock_generation_service):
            response = client.post(
                "/generate",
                data={"class_id": "class_1"},
                files={"image_file": ("test.png", BytesIO(b"fake image"), "image/png")},
            )

        assert response.status_code == 200
        data = response.json()
        assert "question" in data

        # Verify retrieval was called with class_id filter
        assert mock_retrieval_service.retrieve_with_scores.call_count == 2
        calls = mock_retrieval_service.retrieve_with_scores.call_args_list
        assert calls[0].kwargs["class_id"] == "class_1"
        assert calls[0].kwargs["reference_type"] == "assessment"
        assert calls[1].kwargs["class_id"] == "class_1"
        assert calls[1].kwargs["reference_type"] == "lecture"

    def test_generation_with_class_id_retrieves_assessment_and_lecture_separately(
        self, client, sample_class, mock_ocr_service, mock_retrieval_service, mock_generation_service
    ):
        """Test generation with class_id retrieves assessment and lecture separately."""
        assessment_chunks = [
            RetrievedChunk(
                text="Assessment 1",
                score=0.9,
                metadata={"class_id": "class_1", "source_file": "exam1.pdf", "reference_type": "assessment"},
                chunk_id="chunk_1",
            ),
            RetrievedChunk(
                text="Assessment 2",
                score=0.8,
                metadata={"class_id": "class_1", "source_file": "exam2.pdf", "reference_type": "assessment"},
                chunk_id="chunk_2",
            ),
        ]
        lecture_chunks = [
            RetrievedChunk(
                text="Lecture 1",
                score=0.85,
                metadata={"class_id": "class_1", "source_file": "lecture1.pdf", "reference_type": "lecture"},
                chunk_id="chunk_3",
            ),
        ]

        mock_retrieval_service.retrieve_with_scores.side_effect = [
            assessment_chunks,
            lecture_chunks,
        ]

        with patch("app.routes.generate.OCRService", return_value=mock_ocr_service), patch(
            "app.routes.generate.RetrievalService", return_value=mock_retrieval_service
        ), patch("app.routes.generate.GenerationService", return_value=mock_generation_service):
            response = client.post(
                "/generate",
                data={"class_id": "class_1"},
                files={"image_file": ("test.png", BytesIO(b"fake image"), "image/png")},
            )

        assert response.status_code == 200
        # Verify generation service was called with separate chunks
        mock_generation_service.generate_with_reference_types.assert_called_once()
        call_args = mock_generation_service.generate_with_reference_types.call_args
        assert len(call_args[0][1]) == 2  # assessment_chunks
        assert len(call_args[0][2]) == 1  # lecture_chunks

    def test_generation_without_class_id_uses_global_retrieval(
        self, client, mock_ocr_service, mock_retrieval_service, mock_generation_service
    ):
        """Test generation without class_id uses global retrieval (backward compatibility)."""
        retrieved_chunks = [
            RetrievedChunk(
                text="Generic text",
                score=0.9,
                metadata={"source_file": "generic.pdf"},
                chunk_id="chunk_1",
            )
        ]

        mock_retrieval_service.retrieve_with_scores.return_value = retrieved_chunks

        with patch("app.routes.generate.OCRService", return_value=mock_ocr_service), patch(
            "app.routes.generate.RetrievalService", return_value=mock_retrieval_service
        ), patch("app.routes.generate.GenerationService", return_value=mock_generation_service):
            response = client.post(
                "/generate",
                data={},
                files={"image_file": ("test.png", BytesIO(b"fake image"), "image/png")},
            )

        assert response.status_code == 200
        # Verify retrieval was called without filters
        mock_retrieval_service.retrieve_with_scores.assert_called_once()
        call_args = mock_retrieval_service.retrieve_with_scores.call_args
        assert call_args.kwargs.get("class_id") is None
        assert call_args.kwargs.get("reference_type") is None

    def test_generation_with_class_id_but_no_references_returns_empty(
        self, client, sample_class, mock_ocr_service, mock_retrieval_service, mock_generation_service
    ):
        """Test generation with class_id but no references returns empty."""
        mock_retrieval_service.retrieve_with_scores.return_value = []

        with patch("app.routes.generate.OCRService", return_value=mock_ocr_service), patch(
            "app.routes.generate.RetrievalService", return_value=mock_retrieval_service
        ), patch("app.routes.generate.GenerationService", return_value=mock_generation_service):
            response = client.post(
                "/generate",
                data={"class_id": "class_1"},
                files={"image_file": ("test.png", BytesIO(b"fake image"), "image/png")},
            )

        assert response.status_code == 200
        # Should still generate, just with empty chunks
        mock_generation_service.generate_with_reference_types.assert_called_once()
        call_args = mock_generation_service.generate_with_reference_types.call_args
        assert len(call_args[0][1]) == 0  # assessment_chunks empty
        assert len(call_args[0][2]) == 0  # lecture_chunks empty

    def test_generation_with_class_id_and_only_assessment_references(
        self, client, sample_class, mock_ocr_service, mock_retrieval_service, mock_generation_service
    ):
        """Test generation with class_id and only assessment references."""
        assessment_chunks = [
            RetrievedChunk(
                text="Assessment 1",
                score=0.9,
                metadata={"class_id": "class_1", "source_file": "exam1.pdf", "reference_type": "assessment"},
                chunk_id="chunk_1",
            )
        ]

        mock_retrieval_service.retrieve_with_scores.side_effect = [
            assessment_chunks,
            [],  # No lecture chunks
        ]

        with patch("app.routes.generate.OCRService", return_value=mock_ocr_service), patch(
            "app.routes.generate.RetrievalService", return_value=mock_retrieval_service
        ), patch("app.routes.generate.GenerationService", return_value=mock_generation_service):
            response = client.post(
                "/generate",
                data={"class_id": "class_1"},
                files={"image_file": ("test.png", BytesIO(b"fake image"), "image/png")},
            )

        assert response.status_code == 200
        mock_generation_service.generate_with_reference_types.assert_called_once()
        call_args = mock_generation_service.generate_with_reference_types.call_args
        assert len(call_args[0][1]) == 1  # assessment_chunks
        assert len(call_args[0][2]) == 0  # lecture_chunks empty

    def test_generation_with_class_id_and_only_lecture_references(
        self, client, sample_class, mock_ocr_service, mock_retrieval_service, mock_generation_service
    ):
        """Test generation with class_id and only lecture references."""
        lecture_chunks = [
            RetrievedChunk(
                text="Lecture 1",
                score=0.85,
                metadata={"class_id": "class_1", "source_file": "lecture1.pdf", "reference_type": "lecture"},
                chunk_id="chunk_1",
            )
        ]

        mock_retrieval_service.retrieve_with_scores.side_effect = [
            [],  # No assessment chunks
            lecture_chunks,
        ]

        with patch("app.routes.generate.OCRService", return_value=mock_ocr_service), patch(
            "app.routes.generate.RetrievalService", return_value=mock_retrieval_service
        ), patch("app.routes.generate.GenerationService", return_value=mock_generation_service):
            response = client.post(
                "/generate",
                data={"class_id": "class_1"},
                files={"image_file": ("test.png", BytesIO(b"fake image"), "image/png")},
            )

        assert response.status_code == 200
        mock_generation_service.generate_with_reference_types.assert_called_once()
        call_args = mock_generation_service.generate_with_reference_types.call_args
        assert len(call_args[0][1]) == 0  # assessment_chunks empty
        assert len(call_args[0][2]) == 1  # lecture_chunks

    def test_references_used_includes_correct_filenames(
        self, client, sample_class, mock_ocr_service, mock_retrieval_service, mock_generation_service
    ):
        """Test references_used includes correct filenames."""
        assessment_chunks = [
            RetrievedChunk(
                text="Assessment 1",
                score=0.9,
                metadata={"class_id": "class_1", "source_file": "exam1.pdf", "reference_type": "assessment"},
                chunk_id="chunk_1",
            )
        ]
        lecture_chunks = [
            RetrievedChunk(
                text="Lecture 1",
                score=0.85,
                metadata={"class_id": "class_1", "source_file": "lecture1.pdf", "reference_type": "lecture"},
                chunk_id="chunk_2",
            )
        ]

        mock_retrieval_service.retrieve_with_scores.side_effect = [
            assessment_chunks,
            lecture_chunks,
        ]

        with patch("app.routes.generate.OCRService", return_value=mock_ocr_service), patch(
            "app.routes.generate.RetrievalService", return_value=mock_retrieval_service
        ), patch("app.routes.generate.GenerationService", return_value=mock_generation_service):
            response = client.post(
                "/generate",
                data={"class_id": "class_1"},
                files={"image_file": ("test.png", BytesIO(b"fake image"), "image/png")},
            )

        assert response.status_code == 200
        data = response.json()
        assert "references_used" in data
        assert "assessment" in data["references_used"]
        assert "lecture" in data["references_used"]
        assert data["references_used"]["assessment"][0]["source_file"] == "exam1.pdf"
        assert data["references_used"]["lecture"][0]["source_file"] == "lecture1.pdf"

    def test_references_used_includes_correct_scores(
        self, client, sample_class, mock_ocr_service, mock_retrieval_service, mock_generation_service
    ):
        """Test references_used includes correct scores."""
        assessment_chunks = [
            RetrievedChunk(
                text="Assessment 1",
                score=0.9,
                metadata={"class_id": "class_1", "source_file": "exam1.pdf", "reference_type": "assessment"},
                chunk_id="chunk_1",
            )
        ]
        lecture_chunks = [
            RetrievedChunk(
                text="Lecture 1",
                score=0.85,
                metadata={"class_id": "class_1", "source_file": "lecture1.pdf", "reference_type": "lecture"},
                chunk_id="chunk_2",
            )
        ]

        mock_retrieval_service.retrieve_with_scores.side_effect = [
            assessment_chunks,
            lecture_chunks,
        ]

        with patch("app.routes.generate.OCRService", return_value=mock_ocr_service), patch(
            "app.routes.generate.RetrievalService", return_value=mock_retrieval_service
        ), patch("app.routes.generate.GenerationService", return_value=mock_generation_service):
            response = client.post(
                "/generate",
                data={"class_id": "class_1"},
                files={"image_file": ("test.png", BytesIO(b"fake image"), "image/png")},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["references_used"]["assessment"][0]["score"] == 0.9
        assert data["references_used"]["lecture"][0]["score"] == 0.85

    def test_references_used_includes_correct_reference_types(
        self, client, sample_class, mock_ocr_service, mock_retrieval_service, mock_generation_service
    ):
        """Test references_used includes correct reference_types."""
        assessment_chunks = [
            RetrievedChunk(
                text="Assessment 1",
                score=0.9,
                metadata={"class_id": "class_1", "source_file": "exam1.pdf", "reference_type": "assessment"},
                chunk_id="chunk_1",
            )
        ]
        lecture_chunks = [
            RetrievedChunk(
                text="Lecture 1",
                score=0.85,
                metadata={"class_id": "class_1", "source_file": "lecture1.pdf", "reference_type": "lecture"},
                chunk_id="chunk_2",
            )
        ]

        mock_retrieval_service.retrieve_with_scores.side_effect = [
            assessment_chunks,
            lecture_chunks,
        ]

        with patch("app.routes.generate.OCRService", return_value=mock_ocr_service), patch(
            "app.routes.generate.RetrievalService", return_value=mock_retrieval_service
        ), patch("app.routes.generate.GenerationService", return_value=mock_generation_service):
            response = client.post(
                "/generate",
                data={"class_id": "class_1"},
                files={"image_file": ("test.png", BytesIO(b"fake image"), "image/png")},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["references_used"]["assessment"][0]["reference_type"] == "assessment"
        assert data["references_used"]["lecture"][0]["reference_type"] == "lecture"

    def test_generation_with_manual_retrieved_context(
        self, client, mock_ocr_service, mock_generation_service
    ):
        """Test generation with manual retrieved_context (no class filtering)."""
        context_list = ["Context 1", "Context 2"]
        retrieved_context = json.dumps(context_list)

        with patch("app.routes.generate.OCRService", return_value=mock_ocr_service), patch(
            "app.routes.generate.GenerationService", return_value=mock_generation_service
        ):
            response = client.post(
                "/generate",
                data={"ocr_text": "Test text", "retrieved_context": retrieved_context},
            )

        assert response.status_code == 200
        # Should use old method with manual context
        mock_generation_service.generate_with_metadata.assert_called_once()

    def test_generation_with_pdf_file_and_class_id(
        self, client, sample_class, mock_ocr_service, mock_retrieval_service, mock_generation_service
    ):
        """Test generation with PDF file and class_id."""
        assessment_chunks = [
            RetrievedChunk(
                text="Assessment 1",
                score=0.9,
                metadata={"class_id": "class_1", "source_file": "exam1.pdf", "reference_type": "assessment"},
                chunk_id="chunk_1",
            )
        ]
        lecture_chunks = []

        mock_retrieval_service.retrieve_with_scores.side_effect = [
            assessment_chunks,
            lecture_chunks,
        ]

        with patch("app.routes.generate.OCRService", return_value=mock_ocr_service), patch(
            "app.routes.generate.RetrievalService", return_value=mock_retrieval_service
        ), patch("app.routes.generate.GenerationService", return_value=mock_generation_service), patch(
            "app.routes.generate.convert_pdf_to_images", return_value=[MagicMock()]
        ):
            response = client.post(
                "/generate",
                data={"class_id": "class_1"},
                files={"image_file": ("test.pdf", BytesIO(b"fake pdf"), "application/pdf")},
            )

        assert response.status_code == 200
        # Verify PDF was handled
        assert mock_ocr_service.extract_text.called

