"""Unit tests for embedding service."""
import pytest
from unittest.mock import MagicMock, patch

from app.services.embedding_service import EmbeddingService
from app.exceptions import EmbeddingException


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
        mock_collection.get.return_value = {"ids": []}
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


def test_generate_embedding_empty_text(mock_openai_client, mock_chromadb):
    """Test embedding generation with empty text."""
    mock_client, mock_collection = mock_chromadb
    service = EmbeddingService(openai_client=mock_openai_client, vector_db_client=mock_client)
    with pytest.raises(ValueError):
        service.generate_embedding("")


def test_generate_embedding_api_error(mock_openai_client, mock_chromadb):
    """Test error handling for API failures."""
    mock_client, mock_collection = mock_chromadb
    mock_openai_client.embeddings.create.side_effect = Exception("API Error")
    service = EmbeddingService(openai_client=mock_openai_client, vector_db_client=mock_client)
    
    with pytest.raises(Exception) as exc_info:
        service.generate_embedding("test text")
    assert "Failed to generate embedding" in str(exc_info.value)


def test_store_embedding(mock_openai_client, mock_chromadb):
    """Test embedding storage."""
    mock_client, mock_collection = mock_chromadb
    service = EmbeddingService(openai_client=mock_openai_client, vector_db_client=mock_client)
    embedding = [0.1] * 1536
    metadata = {"source": "test", "chunk_id": "chunk_1"}
    chunk_id = service.store_embedding("test text", embedding, metadata)
    assert chunk_id == "chunk_1"
    mock_collection.add.assert_called_once()


def test_store_embedding_auto_chunk_id(mock_openai_client, mock_chromadb):
    """Test embedding storage with auto-generated chunk_id."""
    mock_client, mock_collection = mock_chromadb
    mock_collection.get.return_value = {"ids": ["existing_1", "existing_2"]}
    service = EmbeddingService(openai_client=mock_openai_client, vector_db_client=mock_client)
    embedding = [0.1] * 1536
    metadata = {"source": "test"}  # No chunk_id
    chunk_id = service.store_embedding("test text", embedding, metadata)
    assert chunk_id is not None
    mock_collection.add.assert_called_once()


def test_batch_store(mock_openai_client, mock_chromadb):
    """Test batch embedding storage."""
    mock_client, mock_collection = mock_chromadb
    mock_openai_client.embeddings.create.return_value = MagicMock(
        data=[
            MagicMock(embedding=[0.1] * 1536),
            MagicMock(embedding=[0.2] * 1536),
        ]
    )
    service = EmbeddingService(openai_client=mock_openai_client, vector_db_client=mock_client)
    
    texts = ["text 1", "text 2"]
    metadata_list = [
        {"source": "test", "chunk_id": "chunk_1"},
        {"source": "test", "chunk_id": "chunk_2"},
    ]
    
    chunk_ids = service.batch_store(texts, metadata_list)
    assert len(chunk_ids) == 2
    assert chunk_ids == ["chunk_1", "chunk_2"]
    mock_collection.add.assert_called_once()


def test_batch_store_mismatched_lengths(mock_openai_client, mock_chromadb):
    """Test batch store with mismatched text and metadata lengths."""
    mock_client, mock_collection = mock_chromadb
    service = EmbeddingService(openai_client=mock_openai_client, vector_db_client=mock_client)
    
    with pytest.raises(ValueError):
        service.batch_store(["text 1"], [{"chunk_id": "1"}, {"chunk_id": "2"}])


def test_store_text_with_chunking_single_chunk(mock_openai_client, mock_chromadb):
    """Test storing text with automatic chunking (single chunk)."""
    mock_client, mock_collection = mock_chromadb
    service = EmbeddingService(openai_client=mock_openai_client, vector_db_client=mock_client)
    
    text = "Short text that doesn't need chunking"
    metadata = {"source": "test", "chunk_id": "chunk_1"}
    
    chunk_ids = service.store_text_with_chunking(text, metadata, max_chunk_size=1000)
    assert len(chunk_ids) == 1
    mock_collection.add.assert_called_once()


def test_store_text_with_chunking_multiple_chunks(mock_openai_client, mock_chromadb):
    """Test storing text with automatic chunking (multiple chunks)."""
    mock_client, mock_collection = mock_chromadb
    mock_openai_client.embeddings.create.return_value = MagicMock(
        data=[
            MagicMock(embedding=[0.1] * 1536),
            MagicMock(embedding=[0.2] * 1536),
        ]
    )
    service = EmbeddingService(openai_client=mock_openai_client, vector_db_client=mock_client)
    
    # Create text that will be chunked
    text = "A" * 2000  # Large text
    metadata = {"source": "test", "chunk_id": "base_chunk"}
    
    chunk_ids = service.store_text_with_chunking(text, metadata, max_chunk_size=1000)
    assert len(chunk_ids) > 1
    # Verify chunk IDs are generated
    assert all("base_chunk" in chunk_id or "chunk" in chunk_id for chunk_id in chunk_ids)
