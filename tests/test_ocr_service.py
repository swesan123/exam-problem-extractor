"""Unit tests for OCR service."""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.services.ocr_service import OCRService


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client."""
    client = MagicMock()
    client.chat.completions.create.return_value = MagicMock(
        choices=[
            MagicMock(
                message=MagicMock(content="Extracted text from image")
            )
        ]
    )
    return client


@pytest.fixture
def sample_image_path(tmp_path):
    """Create a sample image file for testing."""
    image_path = tmp_path / "test.png"
    image_path.write_bytes(b"fake image data")
    return image_path


def test_extract_text_success(mock_openai_client, sample_image_path):
    """Test successful text extraction."""
    service = OCRService(openai_client=mock_openai_client)
    result = service.extract_text(sample_image_path)
    assert result == "Extracted text from image"
    mock_openai_client.chat.completions.create.assert_called_once()


def test_extract_with_confidence(mock_openai_client, sample_image_path):
    """Test text extraction with confidence."""
    service = OCRService(openai_client=mock_openai_client)
    text, confidence = service.extract_with_confidence(sample_image_path)
    assert text == "Extracted text from image"
    assert confidence is None  # OpenAI Vision doesn't provide confidence


def test_extract_text_file_not_found(mock_openai_client):
    """Test error handling for missing file."""
    service = OCRService(openai_client=mock_openai_client)
    with pytest.raises(FileNotFoundError):
        service.extract_text(Path("nonexistent.png"))

