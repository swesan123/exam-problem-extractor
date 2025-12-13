"""End-to-end integration tests for full workflow."""

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


class TestEndToEndWorkflow:
    """End-to-end integration tests for full workflow."""

    def test_full_flow_upload_assessment_upload_lecture_generate(
        self, client, sample_class
    ):
        """Full flow: Upload assessment reference → Upload lecture reference → Generate question with class_id."""
        # Step 1: Upload assessment reference
        with patch("app.api.reference_content._processor") as mock_processor, patch(
            "app.api.reference_content.JobService"
        ) as mock_job_service:
            mock_job_service.return_value.create_job.return_value = MagicMock(
                id="job_1", status="pending"
            )

            files = [("assessment.pdf", BytesIO(b"assessment content"), "application/pdf")]
            data = {"class_id": "class_1", "reference_type": "assessment"}

            response = client.post(
                "/api/reference-content/upload",
                files=[("files", f) for f in files],
                data=data,
            )

            assert response.status_code == 202
            job_id_1 = response.json()["job_id"]

            # Verify metadata includes reference_type
            call_args = mock_processor.process_job.call_args
            metadata = call_args[0][2]
            assert metadata["reference_type"] == "assessment"

        # Step 2: Upload lecture reference
        with patch("app.api.reference_content._processor") as mock_processor, patch(
            "app.api.reference_content.JobService"
        ) as mock_job_service:
            mock_job_service.return_value.create_job.return_value = MagicMock(
                id="job_2", status="pending"
            )

            files = [("lecture.pdf", BytesIO(b"lecture content"), "application/pdf")]
            data = {"class_id": "class_1", "reference_type": "lecture"}

            response = client.post(
                "/api/reference-content/upload",
                files=[("files", f) for f in files],
                data=data,
            )

            assert response.status_code == 202
            job_id_2 = response.json()["job_id"]

            # Verify metadata includes reference_type
            call_args = mock_processor.process_job.call_args
            metadata = call_args[0][2]
            assert metadata["reference_type"] == "lecture"

        # Step 3: Generate question with class_id
        assessment_chunks = [
            RetrievedChunk(
                text="Assessment question example",
                score=0.9,
                metadata={
                    "class_id": "class_1",
                    "source_file": "assessment.pdf",
                    "reference_type": "assessment",
                },
                chunk_id="chunk_1",
            )
        ]
        lecture_chunks = [
            RetrievedChunk(
                text="Lecture content example",
                score=0.85,
                metadata={
                    "class_id": "class_1",
                    "source_file": "lecture.pdf",
                    "reference_type": "lecture",
                },
                chunk_id="chunk_2",
            )
        ]

        mock_retrieval_service = MagicMock()
        mock_retrieval_service.retrieve_with_scores.side_effect = [
            assessment_chunks,
            lecture_chunks,
        ]
        mock_generation_service = MagicMock()
        mock_generation_service.generate_with_reference_types.return_value = {
            "question": "Generated question\n\nReferences:\n- Structure/Format: assessment.pdf\n- Content: lecture.pdf",
            "metadata": {"tokens_used": 100, "assessment_count": 1, "lecture_count": 1},
        }

        with patch("app.routes.generate.OCRService") as mock_ocr, patch(
            "app.routes.generate.RetrievalService", return_value=mock_retrieval_service
        ), patch(
            "app.routes.generate.GenerationService", return_value=mock_generation_service
        ):
            mock_ocr.return_value.extract_text.return_value = "OCR text"
            response = client.post(
                "/generate",
                data={"class_id": "class_1"},
                files={"image_file": ("test.png", BytesIO(b"fake image"), "image/png")},
            )

            assert response.status_code == 200
            data = response.json()

            # Verify assessment reference used for structure
            assert "assessment.pdf" in data["question"]
            assert len(data["references_used"]["assessment"]) == 1
            assert data["references_used"]["assessment"][0]["source_file"] == "assessment.pdf"

            # Verify lecture reference used for content
            assert "lecture.pdf" in data["question"]
            assert len(data["references_used"]["lecture"]) == 1
            assert data["references_used"]["lecture"][0]["source_file"] == "lecture.pdf"

            # Verify citations include both filenames
            assert "assessment.pdf" in data["question"]
            assert "lecture.pdf" in data["question"]

            # Verify references_used metadata correct
            assert data["references_used"]["assessment"][0]["reference_type"] == "assessment"
            assert data["references_used"]["lecture"][0]["reference_type"] == "lecture"

    def test_full_flow_upload_without_reference_type_generate(
        self, client, sample_class
    ):
        """Full flow: Upload without reference_type → Generate (should work)."""
        # Upload without reference_type
        with patch("app.api.reference_content._processor") as mock_processor, patch(
            "app.api.reference_content.JobService"
        ) as mock_job_service:
            mock_job_service.return_value.create_job.return_value = MagicMock(
                id="job_1", status="pending"
            )

            files = [("generic.pdf", BytesIO(b"content"), "application/pdf")]
            data = {"class_id": "class_1"}

            response = client.post(
                "/api/reference-content/upload",
                files=[("files", f) for f in files],
                data=data,
            )

            assert response.status_code == 202

        # Generate (should still work)
        mock_retrieval_service = MagicMock()
        mock_retrieval_service.retrieve_with_scores.return_value = []
        mock_generation_service = MagicMock()
        mock_generation_service.generate_with_reference_types.return_value = {
            "question": "Generated question",
            "metadata": {},
        }

        with patch("app.routes.generate.OCRService") as mock_ocr, patch(
            "app.routes.generate.RetrievalService", return_value=mock_retrieval_service
        ), patch(
            "app.routes.generate.GenerationService", return_value=mock_generation_service
        ):
            mock_ocr.return_value.extract_text.return_value = "OCR text"
            response = client.post(
                "/generate",
                data={"class_id": "class_1"},
                files={"image_file": ("test.png", BytesIO(b"fake image"), "image/png")},
            )

            assert response.status_code == 200

    def test_full_flow_multiple_classes_with_same_reference_type(
        self, client, db_session
    ):
        """Full flow: Multiple classes with same reference_type → Generate filters correctly."""
        # Create two classes
        class_1 = Class(id="class_1", name="Class 1", description="", subject="")
        class_2 = Class(id="class_2", name="Class 2", description="", subject="")
        db_session.add(class_1)
        db_session.add(class_2)
        db_session.commit()

        # Generate for class_1 - should only retrieve from class_1
        assessment_chunks = [
            RetrievedChunk(
                text="Class 1 assessment",
                score=0.9,
                metadata={
                    "class_id": "class_1",
                    "source_file": "class1_exam.pdf",
                    "reference_type": "assessment",
                },
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

        with patch("app.routes.generate.OCRService") as mock_ocr, patch(
            "app.routes.generate.RetrievalService", return_value=mock_retrieval_service
        ), patch(
            "app.routes.generate.GenerationService", return_value=mock_generation_service
        ):
            mock_ocr.return_value.extract_text.return_value = "OCR text"
            response = client.post(
                "/generate",
                data={"class_id": "class_1"},
                files={"image_file": ("test.png", BytesIO(b"fake image"), "image/png")},
            )

            assert response.status_code == 200

            # Verify retrieval was called with class_1 filter
            calls = mock_retrieval_service.retrieve_with_scores.call_args_list
            assert calls[0].kwargs["class_id"] == "class_1"
            assert calls[0].kwargs["reference_type"] == "assessment"

    def test_full_flow_upload_pdf_with_reference_type_verify_filename_preserved(
        self, client, sample_class
    ):
        """Full flow: Upload PDF with reference_type → Verify filename preserved."""
        original_filename = "my_exam_2024.pdf"

        with patch("app.api.reference_content._processor") as mock_processor, patch(
            "app.api.reference_content.JobService"
        ) as mock_job_service:
            mock_job_service.return_value.create_job.return_value = MagicMock(
                id="job_1", status="pending"
            )

            files = [(original_filename, BytesIO(b"pdf content"), "application/pdf")]
            data = {"class_id": "class_1", "reference_type": "assessment"}

            response = client.post(
                "/api/reference-content/upload",
                files=[("files", f) for f in files],
                data=data,
            )

            assert response.status_code == 202

            # Verify original filename is preserved in file_info_list
            call_args = mock_processor.process_job.call_args
            file_info_list = call_args[0][1]
            assert file_info_list[0][1] == original_filename

    def test_full_flow_upload_image_with_reference_type_verify_filename_preserved(
        self, client, sample_class
    ):
        """Full flow: Upload image with reference_type → Verify filename preserved."""
        original_filename = "lecture_slide_1.png"

        with patch("app.api.reference_content._processor") as mock_processor, patch(
            "app.api.reference_content.JobService"
        ) as mock_job_service:
            mock_job_service.return_value.create_job.return_value = MagicMock(
                id="job_1", status="pending"
            )

            files = [(original_filename, BytesIO(b"image content"), "image/png")]
            data = {"class_id": "class_1", "reference_type": "lecture"}

            response = client.post(
                "/api/reference-content/upload",
                files=[("files", f) for f in files],
                data=data,
            )

            assert response.status_code == 202

            # Verify original filename is preserved
            call_args = mock_processor.process_job.call_args
            file_info_list = call_args[0][1]
            assert file_info_list[0][1] == original_filename

