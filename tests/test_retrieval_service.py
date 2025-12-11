"""Unit tests for retrieval service."""
import pytest
from unittest.mock import MagicMock

from app.services.embedding_service import EmbeddingService
from app.services.retrieval_service import RetrievalService


@pytest.fixture
def mock_embedding_service():
    """Create a mock embedding service."""
    service = MagicMock(spec=EmbeddingService)
    service.generate_embedding.return_value = [0.1] * 1536
    service.client = MagicMock()  # Add client attribute
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


def test_retrieve_empty_query(mock_embedding_service):
    """Test error handling for empty query."""
    service = RetrievalService(mock_embedding_service)
    with pytest.raises(ValueError):
        service.retrieve("", top_k=5)

