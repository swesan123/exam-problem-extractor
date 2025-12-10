"""Unit tests for generation service."""
import pytest
from unittest.mock import MagicMock

from app.services.generation_service import GenerationService


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client."""
    client = MagicMock()
    client.chat.completions.create.return_value = MagicMock(
        choices=[
            MagicMock(
                message=MagicMock(content="Generated exam question")
            )
        ],
        usage=MagicMock(total_tokens=100)
    )
    return client


def test_generate_question(mock_openai_client):
    """Test question generation."""
    service = GenerationService(openai_client=mock_openai_client)
    result = service.generate_question("OCR text", ["Context 1", "Context 2"])
    assert result == "Generated exam question"
    mock_openai_client.chat.completions.create.assert_called_once()


def test_generate_with_metadata(mock_openai_client):
    """Test question generation with metadata."""
    service = GenerationService(openai_client=mock_openai_client)
    result = service.generate_with_metadata("OCR text", ["Context 1"])
    assert "question" in result
    assert "metadata" in result
    assert result["metadata"]["tokens_used"] == 100

