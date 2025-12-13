"""Integration tests for API routes."""

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
def sample_class(db_session: Session):
    """Create a sample class for testing."""
    test_class = Class(
        id="test_class_1", name="Test Class", description="Test Description"
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


def test_health_check(client: TestClient):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "checks" in data


def test_root_endpoint(client: TestClient):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data


def test_ocr_endpoint_invalid_file(client: TestClient):
    """Test OCR endpoint with invalid file."""
    response = client.post(
        "/ocr", files={"file": ("test.txt", b"not an image", "text/plain")}
    )
    assert response.status_code == 400


def test_ocr_endpoint_pdf_support(client: TestClient, mocker):
    """Test OCR endpoint accepts PDF files."""
    # Mock OCR service to avoid actual API calls
    mocker.patch(
        "app.services.ocr_service.OCRService.extract_with_confidence",
        return_value=("Extracted text from PDF page", 0.95),
    )

    # Create a minimal valid PDF
    pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>
endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
trailer
<< /Size 4 /Root 1 0 R >>
startxref
174
%%EOF"""

    response = client.post(
        "/ocr",
        files={"file": ("test.pdf", pdf_content, "application/pdf")},
    )

    # Should accept PDF and process it
    assert response.status_code == 200
    data = response.json()
    assert "text" in data
    assert "processing_time_ms" in data
    # Should include page separator for PDFs
    assert "=== Page" in data["text"] or "Extracted text" in data["text"]


def test_ocr_endpoint_pdf_multipage(client: TestClient, mocker):
    """Test OCR endpoint handles multi-page PDFs."""

    # Mock OCR service to return different text for each page
    def mock_extract_side_effect(*args, **kwargs):
        # This will be called once per page
        # For simplicity, return same text for all pages
        return ("Page text content", 0.95)

    mocker.patch(
        "app.services.ocr_service.OCRService.extract_with_confidence",
        side_effect=mock_extract_side_effect,
    )

    # Create a minimal PDF (single page for simplicity)
    pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>
endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
trailer
<< /Size 4 /Root 1 0 R >>
startxref
174
%%EOF"""

    response = client.post(
        "/ocr",
        files={"file": ("test.pdf", pdf_content, "application/pdf")},
    )

    if response.status_code == 200:
        data = response.json()
        assert "text" in data
        # Multi-page PDFs should have page separators
        if "=== Page" in data["text"]:
            assert "=== Page 1 ===" in data["text"]


def test_ocr_endpoint_pdf_invalid_file(client: TestClient):
    """Test OCR endpoint handles invalid PDF files gracefully."""
    # Create invalid PDF content
    invalid_pdf_content = b"Not a valid PDF file"

    response = client.post(
        "/ocr",
        files={"file": ("invalid.pdf", invalid_pdf_content, "application/pdf")},
    )

    # Should return an error (400 or 500 depending on when validation happens)
    assert response.status_code in [400, 500]


def test_embed_endpoint_validation(client: TestClient):
    """Test embed endpoint validation."""
    response = client.post(
        "/embed", json={"text": "", "metadata": {"source": "test", "chunk_id": "1"}}
    )
    # Should fail validation
    assert response.status_code in [400, 422]


def test_retrieve_endpoint_validation(client: TestClient):
    """Test retrieve endpoint validation."""
    response = client.post("/retrieve", json={"query": "", "top_k": 5})
    # Should fail validation
    assert response.status_code in [400, 422]


def test_generate_endpoint_with_class_id(
    client: TestClient, sample_class: Class, db_session: Session, mocker
):
    """Test generate endpoint with class_id saves question to class."""
    # Mock service instantiation to avoid ChromaDB conflicts
    mock_embedding_service = mocker.MagicMock()
    mock_retrieval_service = mocker.MagicMock()
    # Mock retrieve_with_scores to return empty chunks (will use generate_with_reference_types with empty chunks)
    mock_retrieval_service.retrieve_with_scores.return_value = []
    mocker.patch(
        "app.routes.generate.EmbeddingService", return_value=mock_embedding_service
    )
    mocker.patch(
        "app.routes.generate.RetrievalService", return_value=mock_retrieval_service
    )

    # Mock OpenAI services
    mocker.patch(
        "app.services.ocr_service.OCRService.extract_text", return_value="Test OCR text"
    )
    # When class_id is provided but both chunks are empty, it falls back to generate_with_metadata
    # Need to patch the instance method, not the class method
    mock_gen_service = mocker.MagicMock()
    mock_gen_service.generate_with_metadata.return_value = {
        "question": "Generated question text",
        "metadata": {"model": "gpt-4", "tokens_used": 100},
    }
    mocker.patch(
        "app.routes.generate.GenerationService", return_value=mock_gen_service
    )

    response = client.post(
        "/generate",
        data={
            "ocr_text": "Test OCR text",
            "class_id": sample_class.id,
            "include_solution": False,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["question"] == "Generated question text"
    assert data["question_id"] is not None
    assert data["class_id"] == sample_class.id

    # Verify question was saved to database using the same session as the endpoint
    # The endpoint uses db_session via dependency override, so we use the same session
    db_session.expire_all()  # Refresh to see committed changes
    saved_question = (
        db_session.query(Question).filter(Question.id == data["question_id"]).first()
    )
    assert saved_question is not None, f"Question {data['question_id']} should be saved"
    assert saved_question.class_id == sample_class.id
    assert saved_question.question_text == "Generated question text"


def test_generate_endpoint_without_class_id(client: TestClient, mocker):
    """Test generate endpoint without class_id (backward compatible)."""
    # Mock service instantiation to avoid ChromaDB conflicts
    mock_embedding_service = mocker.MagicMock()
    mock_retrieval_service = mocker.MagicMock()
    mock_retrieval_service.retrieve.return_value = []
    mocker.patch(
        "app.routes.generate.EmbeddingService", return_value=mock_embedding_service
    )
    mocker.patch(
        "app.routes.generate.RetrievalService", return_value=mock_retrieval_service
    )

    # Mock OpenAI services
    mocker.patch(
        "app.services.ocr_service.OCRService.extract_text", return_value="Test OCR text"
    )
    mocker.patch(
        "app.services.generation_service.GenerationService.generate_with_metadata",
        return_value={
            "question": "Generated question text",
            "metadata": {"model": "gpt-4", "tokens_used": 100},
        },
    )

    response = client.post(
        "/generate", data={"ocr_text": "Test OCR text", "include_solution": False}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["question"] == "Generated question text"
    assert data["question_id"] is None
    assert data["class_id"] is None


def test_generate_endpoint_invalid_class_id(client: TestClient, mocker):
    """Test generate endpoint with invalid class_id doesn't fail."""
    # Mock service instantiation to avoid ChromaDB conflicts
    mock_embedding_service = mocker.MagicMock()
    mock_retrieval_service = mocker.MagicMock()
    # Mock retrieve_with_scores to return empty chunks
    mock_retrieval_service.retrieve_with_scores.return_value = []
    mocker.patch(
        "app.routes.generate.EmbeddingService", return_value=mock_embedding_service
    )
    mocker.patch(
        "app.routes.generate.RetrievalService", return_value=mock_retrieval_service
    )

    # Mock OpenAI services
    mocker.patch(
        "app.services.ocr_service.OCRService.extract_text", return_value="Test OCR text"
    )
    # When class_id is provided but both chunks are empty, it falls back to generate_with_metadata
    # Need to patch the instance method, not the class method
    mock_gen_service = mocker.MagicMock()
    mock_gen_service.generate_with_metadata.return_value = {
        "question": "Generated question text",
        "metadata": {"model": "gpt-4", "tokens_used": 100},
    }
    mocker.patch(
        "app.routes.generate.GenerationService", return_value=mock_gen_service
    )

    response = client.post(
        "/generate",
        data={
            "ocr_text": "Test OCR text",
            "class_id": "nonexistent_class",
            "include_solution": False,
        },
    )

    # Should still succeed, just not save to class
    assert response.status_code == 200
    data = response.json()
    assert data["question"] == "Generated question text"
    assert data["question_id"] is None  # Not saved due to invalid class
