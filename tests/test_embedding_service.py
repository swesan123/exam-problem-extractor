"""Unit tests for embedding service."""
import pytest
from unittest.mock import MagicMock, patch

from app.services.embedding_service import EmbeddingService


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client."""
    client = MagicMock()
    client.embeddings.create.return_value = MagicMock(
        data=[MagicMock(embedding=[0.1] * 1536)]
    )
    return client


@pytest.fixture
def mock_chromadb():
    """Create a mock ChromaDB client."""
    with patch("app.services.embedding_service.chromadb") as mock:
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock.PersistentClient.return_value = mock_client
        yield mock_client, mock_collection


def test_generate_embedding(mock_openai_client, mock_chromadb):
    """Test embedding generation."""
    mock_client, mock_collection = mock_chromadb
    service = EmbeddingService(openai_client=mock_openai_client, vector_db_client=mock_client)
    embedding = service.generate_embedding("test text")
    assert len(embedding) == 1536
    assert all(isinstance(x, float) for x in embedding)


def test_store_embedding(mock_openai_client, mock_chromadb):
    """Test embedding storage."""
    mock_client, mock_collection = mock_chromadb
    service = EmbeddingService(openai_client=mock_openai_client, vector_db_client=mock_client)
    embedding = [0.1] * 1536
    metadata = {"source": "test", "chunk_id": "chunk_1"}
    chunk_id = service.store_embedding("test text", embedding, metadata)
    assert chunk_id == "chunk_1"
    mock_collection.add.assert_called_once()

