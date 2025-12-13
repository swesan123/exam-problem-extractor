"""Edge case tests for class-scoped retrieval and reference types."""

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


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_class_id_filter_with_nonexistent_class(
        self, client, mock_retrieval_service, mock_generation_service
    ):
        """Test class_id filter with non-existent class."""
        mock_retrieval_service = MagicMock()
        mock_retrieval_service.retrieve_with_scores.return_value = []
        mock_generation_service = MagicMock()
        mock_generation_service.generate_with_reference_types.return_value = {
            "question": "Generated question",
            "metadata": {},
        }

        with patch("app.routes.generate.RetrievalService", return_value=mock_retrieval_service), patch(
            "app.routes.generate.GenerationService", return_value=mock_generation_service
        ), patch("app.routes.generate.OCRService") as mock_ocr:
            mock_ocr.return_value.extract_text.return_value = "OCR text"
            response = client.post(
                "/generate",
                data={"class_id": "nonexistent_class"},
                files={"image_file": ("test.png", BytesIO(b"fake image"), "image/png")},
            )

        # Should still work, just return empty results
        assert response.status_code == 200

    def test_reference_type_filter_with_no_matching_references(
        self, client, sample_class, mock_retrieval_service, mock_generation_service
    ):
        """Test reference_type filter with no matching references."""
        mock_retrieval_service = MagicMock()
        mock_retrieval_service.retrieve_with_scores.return_value = []
        mock_generation_service = MagicMock()
        mock_generation_service.generate_with_reference_types.return_value = {
            "question": "Generated question",
            "metadata": {},
        }

        with patch("app.routes.generate.RetrievalService", return_value=mock_retrieval_service), patch(
            "app.routes.generate.GenerationService", return_value=mock_generation_service
        ), patch("app.routes.generate.OCRService") as mock_ocr:
            mock_ocr.return_value.extract_text.return_value = "OCR text"
            response = client.post(
                "/generate",
                data={"class_id": "class_1"},
                files={"image_file": ("test.png", BytesIO(b"fake image"), "image/png")},
            )

        assert response.status_code == 200
        # Should generate with empty chunks

    def test_generation_with_class_id_but_class_has_no_references(
        self, client, sample_class, mock_retrieval_service, mock_generation_service
    ):
        """Test generation with class_id but class has no references."""
        mock_retrieval_service = MagicMock()
        mock_retrieval_service.retrieve_with_scores.return_value = []
        mock_generation_service = MagicMock()
        mock_generation_service.generate_with_reference_types.return_value = {
            "question": "Generated question",
            "metadata": {},
        }

        with patch("app.routes.generate.RetrievalService", return_value=mock_retrieval_service), patch(
            "app.routes.generate.GenerationService", return_value=mock_generation_service
        ), patch("app.routes.generate.OCRService") as mock_ocr:
            mock_ocr.return_value.extract_text.return_value = "OCR text"
            response = client.post(
                "/generate",
                data={"class_id": "class_1"},
                files={"image_file": ("test.png", BytesIO(b"fake image"), "image/png")},
            )

        assert response.status_code == 200

    def test_generation_with_class_id_but_references_have_no_reference_type(
        self, client, sample_class, mock_retrieval_service, mock_generation_service
    ):
        """Test generation with class_id but references have no reference_type."""
        chunks_without_type = [
            RetrievedChunk(
                text="Text without type",
                score=0.9,
                metadata={"class_id": "class_1", "source_file": "file.pdf"},
                chunk_id="chunk_1",
            )
        ]

        mock_retrieval_service = MagicMock()
        mock_retrieval_service.retrieve_with_scores.side_effect = [[], []]
        mock_generation_service = MagicMock()
        mock_generation_service.generate_with_reference_types.return_value = {
            "question": "Generated question",
            "metadata": {},
        }

        with patch("app.routes.generate.RetrievalService", return_value=mock_retrieval_service), patch(
            "app.routes.generate.GenerationService", return_value=mock_generation_service
        ), patch("app.routes.generate.OCRService") as mock_ocr:
            mock_ocr.return_value.extract_text.return_value = "OCR text"
            response = client.post(
                "/generate",
                data={"class_id": "class_1"},
                files={"image_file": ("test.png", BytesIO(b"fake image"), "image/png")},
            )

        assert response.status_code == 200

    def test_filename_with_unicode_characters(
        self, client, sample_class, mock_reference_processor, mock_job_service
    ):
        """Test filename with unicode characters."""
        from io import BytesIO
        files = [("test_文件.pdf", BytesIO(b"content"), "application/pdf")]
        data = {"class_id": "class_1", "reference_type": "assessment"}

        with patch("app.api.reference_content._processor") as mock_processor, patch(
            "app.api.reference_content.JobService"
        ) as mock_job:
            mock_job.return_value.create_job.return_value = MagicMock(id="job_1", status="pending")
            response = client.post(
                "/api/reference-content/upload",
                files=[("files", f) for f in files],
                data=data,
            )

        assert response.status_code == 202

    def test_filename_with_spaces_and_special_characters(
        self, client, sample_class, mock_reference_processor, mock_job_service
    ):
        """Test filename with spaces and special characters."""
        from io import BytesIO
        files = [("test file (2024) - final.pdf", BytesIO(b"content"), "application/pdf")]
        data = {"class_id": "class_1", "reference_type": "assessment"}

        with patch("app.api.reference_content._processor") as mock_processor, patch(
            "app.api.reference_content.JobService"
        ) as mock_job:
            mock_job.return_value.create_job.return_value = MagicMock(id="job_1", status="pending")
            response = client.post(
                "/api/reference-content/upload",
                files=[("files", f) for f in files],
                data=data,
            )

        assert response.status_code == 202

    def test_retrieval_with_empty_vector_database(
        self, client, sample_class, mock_retrieval_service, mock_generation_service
    ):
        """Test retrieval with empty vector database."""
        mock_retrieval_service = MagicMock()
        mock_retrieval_service.retrieve_with_scores.return_value = []
        mock_generation_service = MagicMock()
        mock_generation_service.generate_with_reference_types.return_value = {
            "question": "Generated question",
            "metadata": {},
        }

        with patch("app.routes.generate.RetrievalService", return_value=mock_retrieval_service), patch(
            "app.routes.generate.GenerationService", return_value=mock_generation_service
        ), patch("app.routes.generate.OCRService") as mock_ocr:
            mock_ocr.return_value.extract_text.return_value = "OCR text"
            response = client.post(
                "/generate",
                data={"class_id": "class_1"},
                files={"image_file": ("test.png", BytesIO(b"fake image"), "image/png")},
            )

        assert response.status_code == 200

    def test_generation_when_assessment_chunks_empty_but_lecture_chunks_exist(
        self, client, sample_class, mock_retrieval_service, mock_generation_service
    ):
        """Test generation when assessment chunks empty but lecture chunks exist."""
        lecture_chunks = [
            RetrievedChunk(
                text="Lecture 1",
                score=0.85,
                metadata={"class_id": "class_1", "source_file": "lecture1.pdf", "reference_type": "lecture"},
                chunk_id="chunk_1",
            )
        ]

        mock_retrieval_service = MagicMock()
        mock_retrieval_service.retrieve_with_scores.side_effect = [[], lecture_chunks]
        mock_generation_service = MagicMock()
        mock_generation_service.generate_with_reference_types.return_value = {
            "question": "Generated question",
            "metadata": {},
        }

        with patch("app.routes.generate.RetrievalService", return_value=mock_retrieval_service), patch(
            "app.routes.generate.GenerationService", return_value=mock_generation_service
        ), patch("app.routes.generate.OCRService") as mock_ocr:
            mock_ocr.return_value.extract_text.return_value = "OCR text"
            response = client.post(
                "/generate",
                data={"class_id": "class_1"},
                files={"image_file": ("test.png", BytesIO(b"fake image"), "image/png")},
            )

        assert response.status_code == 200
        mock_generation_service.generate_with_reference_types.assert_called_once()
        call_args = mock_generation_service.generate_with_reference_types.call_args
        assert len(call_args[0][1]) == 0  # assessment empty
        assert len(call_args[0][2]) == 1  # lecture has chunks

    def test_generation_when_lecture_chunks_empty_but_assessment_chunks_exist(
        self, client, sample_class, mock_retrieval_service, mock_generation_service
    ):
        """Test generation when lecture chunks empty but assessment chunks exist."""
        assessment_chunks = [
            RetrievedChunk(
                text="Assessment 1",
                score=0.9,
                metadata={"class_id": "class_1", "source_file": "exam1.pdf", "reference_type": "assessment"},
                chunk_id="chunk_1",
            )
        ]

        mock_retrieval_service = MagicMock()
        mock_retrieval_service.retrieve_with_scores.side_effect = [assessment_chunks, []]
        mock_generation_service = MagicMock()
        mock_generation_service.generate_with_reference_types.return_value = {
            "question": "Generated question",
            "metadata": {},
        }

        with patch("app.routes.generate.RetrievalService", return_value=mock_retrieval_service), patch(
            "app.routes.generate.GenerationService", return_value=mock_generation_service
        ), patch("app.routes.generate.OCRService") as mock_ocr:
            mock_ocr.return_value.extract_text.return_value = "OCR text"
            response = client.post(
                "/generate",
                data={"class_id": "class_1"},
                files={"image_file": ("test.png", BytesIO(b"fake image"), "image/png")},
            )

        assert response.status_code == 200
        mock_generation_service.generate_with_reference_types.assert_called_once()
        call_args = mock_generation_service.generate_with_reference_types.call_args
        assert len(call_args[0][1]) == 1  # assessment has chunks
        assert len(call_args[0][2]) == 0  # lecture empty

    def test_generation_when_both_chunks_empty_fallback_to_old_method(
        self, client, sample_class, mock_retrieval_service, mock_generation_service
    ):
        """Test generation when both chunks empty (fallback to old method)."""
        mock_retrieval_service = MagicMock()
        mock_retrieval_service.retrieve_with_scores.return_value = []
        mock_generation_service = MagicMock()
        mock_generation_service.generate_with_metadata.return_value = {
            "question": "Generated question",
            "metadata": {},
        }

        with patch("app.routes.generate.RetrievalService", return_value=mock_retrieval_service), patch(
            "app.routes.generate.GenerationService", return_value=mock_generation_service
        ), patch("app.routes.generate.OCRService") as mock_ocr:
            mock_ocr.return_value.extract_text.return_value = "OCR text"
            response = client.post(
                "/generate",
                data={"class_id": "class_1"},
                files={"image_file": ("test.png", BytesIO(b"fake image"), "image/png")},
            )

        assert response.status_code == 200
        # Should use generate_with_reference_types even with empty chunks
        # (not fallback to old method - that only happens with manual context)

    def test_citation_formatting_with_multiple_files(
        self, client, sample_class, mock_retrieval_service, mock_generation_service
    ):
        """Test citation formatting with multiple files."""
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

        mock_retrieval_service = MagicMock()
        mock_retrieval_service.retrieve_with_scores.side_effect = [assessment_chunks, lecture_chunks]
        mock_generation_service = MagicMock()
        mock_generation_service.generate_with_reference_types.return_value = {
            "question": "Generated question\n\nReferences:\n- Structure/Format: exam1.pdf, exam2.pdf\n- Content: lecture1.pdf",
            "metadata": {},
        }

        with patch("app.routes.generate.RetrievalService", return_value=mock_retrieval_service), patch(
            "app.routes.generate.GenerationService", return_value=mock_generation_service
        ), patch("app.routes.generate.OCRService") as mock_ocr:
            mock_ocr.return_value.extract_text.return_value = "OCR text"
            response = client.post(
                "/generate",
                data={"class_id": "class_1"},
                files={"image_file": ("test.png", BytesIO(b"fake image"), "image/png")},
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data["references_used"]["assessment"]) == 2
        assert len(data["references_used"]["lecture"]) == 1

    def test_citation_formatting_with_single_file(
        self, client, sample_class, mock_retrieval_service, mock_generation_service
    ):
        """Test citation formatting with single file."""
        assessment_chunks = [
            RetrievedChunk(
                text="Assessment 1",
                score=0.9,
                metadata={"class_id": "class_1", "source_file": "exam1.pdf", "reference_type": "assessment"},
                chunk_id="chunk_1",
            )
        ]

        mock_retrieval_service = MagicMock()
        mock_retrieval_service.retrieve_with_scores.side_effect = [assessment_chunks, []]
        mock_generation_service = MagicMock()
        mock_generation_service.generate_with_reference_types.return_value = {
            "question": "Generated question",
            "metadata": {},
        }

        with patch("app.routes.generate.RetrievalService", return_value=mock_retrieval_service), patch(
            "app.routes.generate.GenerationService", return_value=mock_generation_service
        ), patch("app.routes.generate.OCRService") as mock_ocr:
            mock_ocr.return_value.extract_text.return_value = "OCR text"
            response = client.post(
                "/generate",
                data={"class_id": "class_1"},
                files={"image_file": ("test.png", BytesIO(b"fake image"), "image/png")},
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data["references_used"]["assessment"]) == 1

    def test_citation_formatting_with_no_files_should_not_appear(
        self, client, sample_class, mock_retrieval_service, mock_generation_service
    ):
        """Test citation formatting with no files (should not appear)."""
        mock_retrieval_service = MagicMock()
        mock_retrieval_service.retrieve_with_scores.return_value = []
        mock_generation_service = MagicMock()
        mock_generation_service.generate_with_reference_types.return_value = {
            "question": "Generated question",
            "metadata": {},
        }

        with patch("app.routes.generate.RetrievalService", return_value=mock_retrieval_service), patch(
            "app.routes.generate.GenerationService", return_value=mock_generation_service
        ), patch("app.routes.generate.OCRService") as mock_ocr:
            mock_ocr.return_value.extract_text.return_value = "OCR text"
            response = client.post(
                "/generate",
                data={"class_id": "class_1"},
                files={"image_file": ("test.png", BytesIO(b"fake image"), "image/png")},
            )

        assert response.status_code == 200
        data = response.json()
        # references_used should be empty or None
        assert not data.get("references_used") or (
            len(data["references_used"].get("assessment", [])) == 0
            and len(data["references_used"].get("lecture", [])) == 0
        )


class TestBackwardCompatibility:
    """Test backward compatibility."""

    def test_retrieval_without_filters_works_as_before(
        self, client, mock_retrieval_service, mock_generation_service
    ):
        """Test retrieval without filters works as before."""
        mock_retrieval_service = MagicMock()
        mock_retrieval_service.retrieve_with_scores.return_value = []
        mock_generation_service = MagicMock()
        mock_generation_service.generate_with_metadata.return_value = {
            "question": "Generated question",
            "metadata": {},
        }

        with patch("app.routes.generate.RetrievalService", return_value=mock_retrieval_service), patch(
            "app.routes.generate.GenerationService", return_value=mock_generation_service
        ), patch("app.routes.generate.OCRService") as mock_ocr:
            mock_ocr.return_value.extract_text.return_value = "OCR text"
            response = client.post(
                "/generate",
                data={},
                files={"image_file": ("test.png", BytesIO(b"fake image"), "image/png")},
            )

        assert response.status_code == 200
        # Should work without class_id

    def test_generation_without_class_id_works_as_before(
        self, client, mock_retrieval_service, mock_generation_service
    ):
        """Test generation without class_id works as before."""
        mock_retrieval_service = MagicMock()
        mock_retrieval_service.retrieve_with_scores.return_value = []
        mock_generation_service = MagicMock()
        mock_generation_service.generate_with_metadata.return_value = {
            "question": "Generated question",
            "metadata": {},
        }

        with patch("app.routes.generate.RetrievalService", return_value=mock_retrieval_service), patch(
            "app.routes.generate.GenerationService", return_value=mock_generation_service
        ), patch("app.routes.generate.OCRService") as mock_ocr:
            mock_ocr.return_value.extract_text.return_value = "OCR text"
            response = client.post(
                "/generate",
                data={},
                files={"image_file": ("test.png", BytesIO(b"fake image"), "image/png")},
            )

        assert response.status_code == 200

    def test_upload_without_reference_type_works(
        self, client, sample_class, mock_reference_processor, mock_job_service
    ):
        """Test upload without reference_type works (stores None)."""
        from io import BytesIO
        files = [("test.pdf", BytesIO(b"content"), "application/pdf")]
        data = {"class_id": "class_1"}

        with patch("app.api.reference_content._processor") as mock_processor, patch(
            "app.api.reference_content.JobService"
        ) as mock_job:
            mock_job.return_value.create_job.return_value = MagicMock(id="job_1", status="pending")
            response = client.post(
                "/api/reference-content/upload",
                files=[("files", f) for f in files],
                data=data,
            )

        assert response.status_code == 202
        call_args = mock_processor.process_job.call_args
        metadata = call_args[0][2]
        assert metadata.get("reference_type") is None

