"""Unit tests for OCR service."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.ocr_service import OCRService


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client."""
    client = MagicMock()
    client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="Extracted text from image"))]
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


def test_detect_image_mime_type_png(tmp_path):
    """Test MIME type detection for PNG images."""
    service = OCRService()
    image_path = tmp_path / "test.png"
    image_path.write_bytes(b"fake png data")
    mime_type = service._detect_image_mime_type(image_path)
    assert mime_type == "image/png"


def test_detect_image_mime_type_jpeg(tmp_path):
    """Test MIME type detection for JPEG images."""
    service = OCRService()
    image_path = tmp_path / "test.jpg"
    image_path.write_bytes(b"fake jpeg data")
    mime_type = service._detect_image_mime_type(image_path)
    assert mime_type == "image/jpeg"


def test_detect_image_mime_type_gif(tmp_path):
    """Test MIME type detection for GIF images."""
    service = OCRService()
    image_path = tmp_path / "test.gif"
    image_path.write_bytes(b"fake gif data")
    mime_type = service._detect_image_mime_type(image_path)
    assert mime_type == "image/gif"


def test_detect_image_mime_type_webp(tmp_path):
    """Test MIME type detection for WebP images."""
    service = OCRService()
    image_path = tmp_path / "test.webp"
    image_path.write_bytes(b"fake webp data")
    mime_type = service._detect_image_mime_type(image_path)
    assert mime_type == "image/webp"


def test_detect_image_mime_type_defaults_to_jpeg(tmp_path):
    """Test that unknown formats default to JPEG."""
    service = OCRService()
    image_path = tmp_path / "test.unknown"
    image_path.write_bytes(b"fake data")
    mime_type = service._detect_image_mime_type(image_path)
    assert mime_type == "image/jpeg"


def test_extract_with_confidence_uses_correct_mime_type(mock_openai_client, tmp_path):
    """Test that extract_with_confidence uses correct MIME type in data URL."""
    service = OCRService(openai_client=mock_openai_client)
    image_path = tmp_path / "test.png"
    image_path.write_bytes(b"fake png data")

    service.extract_with_confidence(image_path)

    # Verify the API was called
    mock_openai_client.chat.completions.create.assert_called_once()
    call_args = mock_openai_client.chat.completions.create.call_args

    # Extract the messages from the call
    messages = call_args.kwargs["messages"]
    image_url = messages[0]["content"][1]["image_url"]["url"]

    # Verify it uses image/png, not image/jpeg
    assert image_url.startswith("data:image/png;base64,")
    assert not image_url.startswith("data:image/jpeg;base64,")
