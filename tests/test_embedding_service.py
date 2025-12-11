"""Unit tests for embedding service."""

from unittest.mock import MagicMock, patch

import pytest

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
    service = EmbeddingService(
        openai_client=mock_openai_client, vector_db_client=mock_client
    )
    embedding = service.generate_embedding("test text")
    assert len(embedding) == 1536
    assert all(isinstance(x, float) for x in embedding)


def test_store_embedding(mock_openai_client, mock_chromadb):
    """Test embedding storage."""
    mock_client, mock_collection = mock_chromadb
    service = EmbeddingService(
        openai_client=mock_openai_client, vector_db_client=mock_client
    )
    embedding = [0.1] * 1536
    metadata = {"source": "test", "chunk_id": "chunk_1"}
    chunk_id = service.store_embedding("test text", embedding, metadata)
    assert chunk_id == "chunk_1"
    mock_collection.add.assert_called_once()


def test_list_embeddings_by_class(mock_openai_client, mock_chromadb):
    """Test listing embeddings by class ID."""
    mock_client, mock_collection = mock_chromadb
    service = EmbeddingService(
        openai_client=mock_openai_client, vector_db_client=mock_client
    )

    # Mock collection.get to return data with class_id filter
    mock_collection.get.return_value = {
        "ids": ["chunk_1", "chunk_2", "chunk_3"],
        "documents": ["Text 1", "Text 2", "Text 3"],
        "metadatas": [
            {"source": "test", "class_id": "class_1"},
            {"source": "test", "class_id": "class_1"},
            {"source": "test", "class_id": "class_2"},
        ],
    }

    results = service.list_embeddings_by_class("class_1")

    assert len(results) == 2
    assert results[0]["chunk_id"] == "chunk_1"
    assert results[0]["metadata"]["class_id"] == "class_1"
    assert results[1]["chunk_id"] == "chunk_2"


def test_list_embeddings_by_class_empty(mock_openai_client, mock_chromadb):
    """Test listing embeddings when class has none."""
    mock_client, mock_collection = mock_chromadb
    service = EmbeddingService(
        openai_client=mock_openai_client, vector_db_client=mock_client
    )

    mock_collection.get.return_value = {
        "ids": [],
        "documents": [],
        "metadatas": [],
    }

    results = service.list_embeddings_by_class("class_1")

    assert len(results) == 0


def test_delete_embedding_success(mock_openai_client, mock_chromadb):
    """Test successfully deleting an embedding."""
    mock_client, mock_collection = mock_chromadb
    service = EmbeddingService(
        openai_client=mock_openai_client, vector_db_client=mock_client
    )

    mock_collection.get.return_value = {"ids": ["chunk_1"]}
    result = service.delete_embedding("chunk_1")

    assert result is True
    mock_collection.delete.assert_called_once_with(ids=["chunk_1"])


def test_delete_embedding_not_found(mock_openai_client, mock_chromadb):
    """Test deleting non-existent embedding."""
    mock_client, mock_collection = mock_chromadb
    service = EmbeddingService(
        openai_client=mock_openai_client, vector_db_client=mock_client
    )

    mock_collection.get.return_value = {"ids": []}
    result = service.delete_embedding("chunk_999")

    assert result is False
    mock_collection.delete.assert_not_called()
