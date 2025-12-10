"""Unit tests for generation service."""
import pytest
from unittest.mock import MagicMock

from app.services.generation_service import GenerationService
from app.exceptions import GenerationException


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
    assert result["metadata"]["retrieved_count"] == 1


def test_generate_with_metadata_empty_context(mock_openai_client):
    """Test generation with empty context list."""
    service = GenerationService(openai_client=mock_openai_client)
    result = service.generate_with_metadata("OCR text", [])
    assert "question" in result
    assert result["metadata"]["retrieved_count"] == 0


def test_generate_with_metadata_large_context(mock_openai_client):
    """Test generation with large context (should limit to 5)."""
    service = GenerationService(openai_client=mock_openai_client)
    large_context = [f"Context {i}" for i in range(10)]
    result = service.generate_with_metadata("OCR text", large_context)
    # Should still work, but only use first 5 contexts
    assert "question" in result


def test_generate_with_solution(mock_openai_client):
    """Test question generation with solution."""
    mock_openai_client.chat.completions.create.return_value = MagicMock(
        choices=[
            MagicMock(
                message=MagicMock(content="Question:\nWhat is 2+2?\n\nSolution:\n4")
            )
        ],
        usage=MagicMock(total_tokens=150)
    )
    service = GenerationService(openai_client=mock_openai_client)
    result = service.generate_with_solution("OCR text", ["Context 1"])
    assert "question" in result
    assert "solution" in result
    assert result["metadata"]["tokens_used"] == 150


def test_generate_with_solution_no_separator(mock_openai_client):
    """Test solution generation when response doesn't have separator."""
    mock_openai_client.chat.completions.create.return_value = MagicMock(
        choices=[
            MagicMock(
                message=MagicMock(content="Just a question without solution separator")
            )
        ],
        usage=MagicMock(total_tokens=100)
    )
    service = GenerationService(openai_client=mock_openai_client)
    result = service.generate_with_solution("OCR text", [])
    assert "question" in result
    assert result.get("solution") == ""  # Should be empty if no separator found


def test_generate_api_error(mock_openai_client):
    """Test error handling for API failures."""
    mock_openai_client.chat.completions.create.side_effect = Exception("API Error")
    service = GenerationService(openai_client=mock_openai_client)
    
    with pytest.raises(Exception) as exc_info:
        service.generate_question("OCR text", [])
    assert "Question generation failed" in str(exc_info.value)


def test_generate_empty_response(mock_openai_client):
    """Test handling of empty API response."""
    mock_openai_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content=None))]
    )
    service = GenerationService(openai_client=mock_openai_client)
    result = service.generate_question("OCR text", [])
    assert result == ""  # Should return empty string


def test_generate_service_initialization():
    """Test generation service initialization without client."""
    from unittest.mock import patch
    with patch("app.services.generation_service.OpenAI") as mock_openai:
        service = GenerationService()
        mock_openai.assert_called_once()
