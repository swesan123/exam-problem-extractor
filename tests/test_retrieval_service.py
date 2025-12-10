"""Unit tests for retrieval service."""
import pytest
from unittest.mock import MagicMock

from app.services.embedding_service import EmbeddingService
from app.services.retrieval_service import RetrievalService
from app.exceptions import RetrievalException


@pytest.fixture
def mock_embedding_service():
    """Create a mock embedding service."""
    service = MagicMock(spec=EmbeddingService)
    service.generate_embedding.return_value = [0.1] * 1536
    service.collection = MagicMock()
    service.collection.query.return_value = {
        "ids": [["chunk_1", "chunk_2"]],
        "documents": [["Text 1", "Text 2"]],
        "metadatas": [[{"source": "test"}, {"source": "test"}]],
        "distances": [[0.1, 0.2]],
    }
    return service


def test_retrieve_with_scores(mock_embedding_service):
    """Test retrieval with scores."""
    service = RetrievalService(mock_embedding_service)
    results = service.retrieve_with_scores("test query", top_k=2)
    assert len(results) == 2
    assert all(result.score >= 0.0 and result.score <= 1.0 for result in results)
    assert results[0].score >= results[1].score  # Sorted by score


def test_retrieve(mock_embedding_service):
    """Test retrieve method (without explicit scores)."""
    service = RetrievalService(mock_embedding_service)
    results = service.retrieve("test query", top_k=2)
    assert len(results) == 2
    assert all(hasattr(result, "score") for result in results)


def test_retrieve_empty_query(mock_embedding_service):
    """Test error handling for empty query."""
    service = RetrievalService(mock_embedding_service)
    with pytest.raises(ValueError):
        service.retrieve("", top_k=5)


def test_retrieve_whitespace_only_query(mock_embedding_service):
    """Test error handling for whitespace-only query."""
    service = RetrievalService(mock_embedding_service)
    with pytest.raises(ValueError):
        service.retrieve("   ", top_k=5)


def test_retrieve_invalid_top_k(mock_embedding_service):
    """Test error handling for invalid top_k values."""
    service = RetrievalService(mock_embedding_service)
    
    with pytest.raises(ValueError):
        service.retrieve("query", top_k=0)
    
    with pytest.raises(ValueError):
        service.retrieve("query", top_k=101)


def test_retrieve_empty_results(mock_embedding_service):
    """Test retrieval when vector DB returns no results."""
    mock_embedding_service.collection.query.return_value = {
        "ids": [[]],
        "documents": [[]],
        "metadatas": [[]],
        "distances": [[]],
    }
    service = RetrievalService(mock_embedding_service)
    results = service.retrieve_with_scores("query", top_k=5)
    assert len(results) == 0


def test_retrieve_score_calculation(mock_embedding_service):
    """Test that scores are calculated correctly from distances."""
    # Distance of 0.1 should give score of 0.9 (1.0 - 0.1)
    mock_embedding_service.collection.query.return_value = {
        "ids": [["chunk_1"]],
        "documents": [["Text 1"]],
        "metadatas": [[{"source": "test"}]],
        "distances": [[0.1]],
    }
    service = RetrievalService(mock_embedding_service)
    results = service.retrieve_with_scores("query", top_k=1)
    assert len(results) == 1
    assert abs(results[0].score - 0.9) < 0.01


def test_retrieve_score_normalization(mock_embedding_service):
    """Test that scores are normalized to 0-1 range."""
    # Test with very high distance
    mock_embedding_service.collection.query.return_value = {
        "ids": [["chunk_1"]],
        "documents": [["Text 1"]],
        "metadatas": [[{"source": "test"}]],
        "distances": [[2.0]],  # Distance > 1.0
    }
    service = RetrievalService(mock_embedding_service)
    results = service.retrieve_with_scores("query", top_k=1)
    assert 0.0 <= results[0].score <= 1.0


def test_retrieve_api_error(mock_embedding_service):
    """Test error handling for API failures."""
    mock_embedding_service.generate_embedding.side_effect = Exception("API Error")
    service = RetrievalService(mock_embedding_service)
    
    with pytest.raises(Exception) as exc_info:
        service.retrieve("query", top_k=5)
    assert "Retrieval failed" in str(exc_info.value)
