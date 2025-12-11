"""Integration tests for API routes."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.database import Base, engine, SessionLocal
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
        id="test_class_1",
        name="Test Class",
        description="Test Description"
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
    response = client.post("/ocr", files={"file": ("test.txt", b"not an image", "text/plain")})
    assert response.status_code == 400


def test_embed_endpoint_validation(client: TestClient):
    """Test embed endpoint validation."""
    response = client.post("/embed", json={"text": "", "metadata": {"source": "test", "chunk_id": "1"}})
    # Should fail validation
    assert response.status_code in [400, 422]


def test_retrieve_endpoint_validation(client: TestClient):
    """Test retrieve endpoint validation."""
    response = client.post("/retrieve", json={"query": "", "top_k": 5})
    # Should fail validation
    assert response.status_code in [400, 422]


def test_generate_endpoint_with_class_id(client: TestClient, sample_class: Class, mocker):
    """Test generate endpoint with class_id saves question to class."""
    # Mock OpenAI services
    mocker.patch("app.services.ocr_service.OCRService.extract_text", return_value="Test OCR text")
    # Mock EmbeddingService to avoid ChromaDB singleton issues
    mock_embedding_service = mocker.MagicMock()
    mocker.patch("app.routes.generate.EmbeddingService", return_value=mock_embedding_service)
    # Mock RetrievalService
    mock_retrieval_service = mocker.MagicMock()
    mock_retrieval_service.retrieve.return_value = []
    mocker.patch("app.routes.generate.RetrievalService", return_value=mock_retrieval_service)
    mocker.patch(
        "app.services.generation_service.GenerationService.generate_with_metadata",
        return_value={
            "question": "Generated question text",
            "metadata": {"model": "gpt-4", "tokens_used": 100}
        }
    )
    
    response = client.post(
        "/generate",
        data={
            "ocr_text": "Test OCR text",
            "class_id": sample_class.id,
            "include_solution": False
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["question"] == "Generated question text"
    assert data["question_id"] is not None
    assert data["class_id"] == sample_class.id
    
    # Verify question was saved to database
    from app.db.database import SessionLocal
    db = SessionLocal()
    try:
        saved_question = db.query(Question).filter(Question.id == data["question_id"]).first()
        assert saved_question is not None
        assert saved_question.class_id == sample_class.id
        assert saved_question.question_text == "Generated question text"
    finally:
        db.close()


def test_generate_endpoint_without_class_id(client: TestClient, mocker):
    """Test generate endpoint without class_id (backward compatible)."""
    # Mock OpenAI services
    mocker.patch("app.services.ocr_service.OCRService.extract_text", return_value="Test OCR text")
    # Mock EmbeddingService to avoid ChromaDB singleton issues
    mock_embedding_service = mocker.MagicMock()
    mocker.patch("app.routes.generate.EmbeddingService", return_value=mock_embedding_service)
    # Mock RetrievalService
    mock_retrieval_service = mocker.MagicMock()
    mock_retrieval_service.retrieve.return_value = []
    mocker.patch("app.routes.generate.RetrievalService", return_value=mock_retrieval_service)
    mocker.patch(
        "app.services.generation_service.GenerationService.generate_with_metadata",
        return_value={
            "question": "Generated question text",
            "metadata": {"model": "gpt-4", "tokens_used": 100}
        }
    )
    
    response = client.post(
        "/generate",
        data={
            "ocr_text": "Test OCR text",
            "include_solution": False
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["question"] == "Generated question text"
    assert data["question_id"] is None
    assert data["class_id"] is None


def test_generate_endpoint_invalid_class_id(client: TestClient, mocker):
    """Test generate endpoint with invalid class_id doesn't fail."""
    # Mock OpenAI services
    mocker.patch("app.services.ocr_service.OCRService.extract_text", return_value="Test OCR text")
    # Mock EmbeddingService to avoid ChromaDB singleton issues
    mock_embedding_service = mocker.MagicMock()
    mocker.patch("app.routes.generate.EmbeddingService", return_value=mock_embedding_service)
    # Mock RetrievalService
    mock_retrieval_service = mocker.MagicMock()
    mock_retrieval_service.retrieve.return_value = []
    mocker.patch("app.routes.generate.RetrievalService", return_value=mock_retrieval_service)
    mocker.patch(
        "app.services.generation_service.GenerationService.generate_with_metadata",
        return_value={
            "question": "Generated question text",
            "metadata": {"model": "gpt-4", "tokens_used": 100}
        }
    )
    
    response = client.post(
        "/generate",
        data={
            "ocr_text": "Test OCR text",
            "class_id": "nonexistent_class",
            "include_solution": False
        }
    )
    
    # Should still succeed, just not save to class
    assert response.status_code == 200
    data = response.json()
    assert data["question"] == "Generated question text"
    assert data["question_id"] is None  # Not saved due to invalid class

