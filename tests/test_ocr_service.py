"""Unit tests for OCR service."""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
import time

from app.services.ocr_service import OCRService
from app.exceptions import OCRException


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


def test_extract_text_api_failure(mock_openai_client, sample_image_path):
    """Test error handling for API failures."""
    mock_openai_client.chat.completions.create.side_effect = Exception("API Error")
    service = OCRService(openai_client=mock_openai_client)
    
    with pytest.raises(Exception) as exc_info:
        service.extract_text(sample_image_path)
    assert "OCR extraction failed" in str(exc_info.value)


def test_extract_text_retry_logic(mock_openai_client, sample_image_path, monkeypatch):
    """Test retry logic with exponential backoff."""
    call_count = 0
    
    def failing_then_success(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise Exception("Temporary error")
        return MagicMock(
            choices=[MagicMock(message=MagicMock(content="Success after retry"))]
        )
    
    mock_openai_client.chat.completions.create.side_effect = failing_then_success
    
    # Mock sleep to speed up test
    sleep_calls = []
    def mock_sleep(seconds):
        sleep_calls.append(seconds)
    
    monkeypatch.setattr(time, "sleep", mock_sleep)
    
    service = OCRService(openai_client=mock_openai_client)
    result = service.extract_text(sample_image_path)
    
    assert result == "Success after retry"
    assert call_count == 2
    assert len(sleep_calls) == 1  # Should have slept once before retry


def test_extract_text_max_retries_exceeded(mock_openai_client, sample_image_path):
    """Test that max retries are respected."""
    mock_openai_client.chat.completions.create.side_effect = Exception("Persistent error")
    service = OCRService(openai_client=mock_openai_client)
    
    with pytest.raises(Exception) as exc_info:
        service.extract_with_confidence(sample_image_path, max_retries=2)
    assert "failed after 2 attempts" in str(exc_info.value)


def test_ocr_service_initialization():
    """Test OCR service initialization without client."""
    with patch("app.services.ocr_service.OpenAI") as mock_openai:
        service = OCRService()
        mock_openai.assert_called_once()


def test_extract_text_empty_response(mock_openai_client, sample_image_path):
    """Test handling of empty API response."""
    mock_openai_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content=None))]
    )
    service = OCRService(openai_client=mock_openai_client)
    result = service.extract_text(sample_image_path)
    assert result == ""  # Should return empty string, not None
