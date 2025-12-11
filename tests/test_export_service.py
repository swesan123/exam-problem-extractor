"""Tests for export service."""

import json
from io import BytesIO

import pytest

from app.db.models import Question
from app.services.export_service import ExportFormat, ExportService


@pytest.fixture
def sample_questions():
    """Create sample questions for testing."""
    from datetime import datetime

    questions = [
        Question(
            id="q1",
            class_id="class1",
            question_text="What is 2 + 2?",
            solution="4",
            metadata={"source": "test"},
            created_at=datetime.now(),
        ),
        Question(
            id="q2",
            class_id="class1",
            question_text="What is the capital of France?",
            solution="Paris",
            metadata={"source": "test"},
            created_at=datetime.now(),
        ),
    ]
    return questions


@pytest.fixture
def export_service():
    """Create export service instance."""
    return ExportService()


def test_export_to_txt(export_service, sample_questions):
    """Test TXT export."""
    result = export_service.export_to_txt(sample_questions, include_solutions=False)

    assert "EXAM QUESTIONS" in result
    assert "Question 1" in result
    assert "What is 2 + 2?" in result
    assert "Question 2" in result
    assert "What is the capital of France?" in result
    assert "4" not in result  # Solutions not included


def test_export_to_txt_with_solutions(export_service, sample_questions):
    """Test TXT export with solutions."""
    result = export_service.export_to_txt(sample_questions, include_solutions=True)

    assert "EXAM QUESTIONS" in result
    assert "Question 1" in result
    assert "What is 2 + 2?" in result
    assert "Solution:" in result
    assert "4" in result
    assert "Paris" in result


def test_export_to_json(export_service, sample_questions):
    """Test JSON export."""
    result = export_service.export_to_json(sample_questions, include_solutions=False)
    data = json.loads(result)

    assert "questions" in data
    assert "total" in data
    assert data["total"] == 2
    assert len(data["questions"]) == 2
    assert data["questions"][0]["question_text"] == "What is 2 + 2?"
    assert data["questions"][0]["solution"] is None  # Solutions not included


def test_export_to_json_with_solutions(export_service, sample_questions):
    """Test JSON export with solutions."""
    result = export_service.export_to_json(sample_questions, include_solutions=True)
    data = json.loads(result)

    assert data["questions"][0]["solution"] == "4"
    assert data["questions"][1]["solution"] == "Paris"


def test_export_to_pdf(export_service, sample_questions):
    """Test PDF export."""
    buffer = export_service.export_to_pdf(sample_questions, include_solutions=False)

    assert isinstance(buffer, BytesIO)
    assert buffer.tell() == 0  # Should be at start
    content = buffer.read()
    assert len(content) > 0
    assert content.startswith(b"%PDF")  # PDF magic number


def test_export_to_docx(export_service, sample_questions):
    """Test DOCX export."""
    buffer = export_service.export_to_docx(sample_questions, include_solutions=False)

    assert isinstance(buffer, BytesIO)
    assert buffer.tell() == 0  # Should be at start
    content = buffer.read()
    assert len(content) > 0
    # DOCX files start with PK (ZIP format)
    assert content.startswith(b"PK")


def test_export_questions_txt(export_service, sample_questions):
    """Test export_questions with TXT format."""
    content, content_type, file_ext = export_service.export_questions(
        sample_questions, ExportFormat.TXT, include_solutions=False
    )

    assert isinstance(content, bytes)
    assert content_type == "text/plain"
    assert file_ext == "txt"
    assert b"EXAM QUESTIONS" in content


def test_export_questions_json(export_service, sample_questions):
    """Test export_questions with JSON format."""
    content, content_type, file_ext = export_service.export_questions(
        sample_questions, ExportFormat.JSON, include_solutions=False
    )

    assert isinstance(content, bytes)
    assert content_type == "application/json"
    assert file_ext == "json"
    data = json.loads(content.decode("utf-8"))
    assert "questions" in data


def test_export_questions_pdf(export_service, sample_questions):
    """Test export_questions with PDF format."""
    content, content_type, file_ext = export_service.export_questions(
        sample_questions, ExportFormat.PDF, include_solutions=False
    )

    assert isinstance(content, bytes)
    assert content_type == "application/pdf"
    assert file_ext == "pdf"
    assert content.startswith(b"%PDF")


def test_export_questions_docx(export_service, sample_questions):
    """Test export_questions with DOCX format."""
    content, content_type, file_ext = export_service.export_questions(
        sample_questions, ExportFormat.DOCX, include_solutions=False
    )

    assert isinstance(content, bytes)
    assert "wordprocessingml" in content_type
    assert file_ext == "docx"
    assert content.startswith(b"PK")


def test_export_questions_invalid_format(export_service, sample_questions):
    """Test export_questions with invalid format."""
    with pytest.raises(ValueError, match="Unsupported export format"):
        export_service.export_questions(
            sample_questions, "invalid", include_solutions=False
        )


def test_export_empty_questions(export_service):
    """Test export with empty question list."""
    result = export_service.export_to_txt([], include_solutions=False)
    assert "EXAM QUESTIONS" in result
    assert "Question" not in result
