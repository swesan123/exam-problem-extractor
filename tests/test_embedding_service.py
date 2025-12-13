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


def test_store_embedding_filters_none_values(mock_openai_client, mock_chromadb):
    """Test that None values in metadata are filtered out before storing."""
    mock_client, mock_collection = mock_chromadb
    service = EmbeddingService(
        openai_client=mock_openai_client, vector_db_client=mock_client
    )
    embedding = [0.1] * 1536

    # Metadata with None values (common when optional fields are not provided)
    metadata = {
        "source": "test",
        "chunk_id": "chunk_1",
        "exam_source": None,  # Optional field not provided
        "exam_type": None,  # Optional field not provided
        "class_id": "class_1",
        "timestamp": "2024-01-01",
    }

    chunk_id = service.store_embedding("test text", embedding, metadata)

    assert chunk_id == "chunk_1"
    mock_collection.add.assert_called_once()

    # Verify that the call was made with cleaned metadata (no None values)
    call_args = mock_collection.add.call_args
    stored_metadata = call_args.kwargs["metadatas"][0]

    # None values should be filtered out
    assert "exam_source" not in stored_metadata
    assert "exam_type" not in stored_metadata

    # Valid values should be preserved
    assert stored_metadata["source"] == "test"
    assert stored_metadata["chunk_id"] == "chunk_1"
    assert stored_metadata["class_id"] == "class_1"
    assert stored_metadata["timestamp"] == "2024-01-01"


def test_store_embedding_all_none_metadata(mock_openai_client, mock_chromadb):
    """Test storing with metadata where all optional fields are None."""
    mock_client, mock_collection = mock_chromadb
    service = EmbeddingService(
        openai_client=mock_openai_client, vector_db_client=mock_client
    )
    embedding = [0.1] * 1536

    # Only required fields, all optional fields are None
    metadata = {
        "chunk_id": "chunk_2",
        "class_id": "class_1",
        "exam_source": None,
        "exam_type": None,
    }

    chunk_id = service.store_embedding("test text", embedding, metadata)

    assert chunk_id == "chunk_2"
    mock_collection.add.assert_called_once()

    # Verify cleaned metadata only contains non-None values
    call_args = mock_collection.add.call_args
    stored_metadata = call_args.kwargs["metadatas"][0]

    assert "exam_source" not in stored_metadata
    assert "exam_type" not in stored_metadata
    assert stored_metadata["chunk_id"] == "chunk_2"
    assert stored_metadata["class_id"] == "class_1"


def test_batch_store_filters_none_values(mock_openai_client, mock_chromadb):
    """Test that None values in batch metadata are filtered out."""
    mock_client, mock_collection = mock_chromadb
    service = EmbeddingService(
        openai_client=mock_openai_client, vector_db_client=mock_client
    )

    texts = ["text 1", "text 2"]
    metadata_list = [
        {
            "chunk_id": "chunk_1",
            "class_id": "class_1",
            "exam_source": None,  # None value
            "exam_type": "midterm",
        },
        {
            "chunk_id": "chunk_2",
            "class_id": "class_1",
            "exam_source": "test_source",
            "exam_type": None,  # None value
        },
    ]

    chunk_ids = service.batch_store(texts, metadata_list)

    assert len(chunk_ids) == 2
    assert chunk_ids == ["chunk_1", "chunk_2"]
    mock_collection.add.assert_called_once()

    # Verify that None values were filtered out from all metadata
    call_args = mock_collection.add.call_args
    stored_metadata_list = call_args.kwargs["metadatas"]

    # First metadata: exam_source should be filtered out
    assert "exam_source" not in stored_metadata_list[0]
    assert stored_metadata_list[0]["exam_type"] == "midterm"
    assert stored_metadata_list[0]["chunk_id"] == "chunk_1"

    # Second metadata: exam_type should be filtered out
    assert "exam_type" not in stored_metadata_list[1]
    assert stored_metadata_list[1]["exam_source"] == "test_source"
    assert stored_metadata_list[1]["chunk_id"] == "chunk_2"


def test_batch_store_preserves_reference_type_and_source_file(
    mock_openai_client, mock_chromadb
):
    """Test that batch_store preserves reference_type and source_file metadata."""
    mock_client, mock_collection = mock_chromadb
    service = EmbeddingService(
        openai_client=mock_openai_client, vector_db_client=mock_client
    )

    texts = ["text 1", "text 2"]
    metadata_list = [
        {
            "chunk_id": "chunk_1",
            "class_id": "class_1",
            "reference_type": "assessment",
            "source_file": "exam_2024.pdf",
        },
        {
            "chunk_id": "chunk_2",
            "class_id": "class_1",
            "reference_type": "lecture",
            "source_file": "lecture_notes.pdf",
        },
    ]

    chunk_ids = service.batch_store(texts, metadata_list)

    assert len(chunk_ids) == 2
    mock_collection.add.assert_called_once()

    # Verify that reference_type and source_file are preserved
    call_args = mock_collection.add.call_args
    stored_metadata_list = call_args.kwargs["metadatas"]

    assert stored_metadata_list[0]["reference_type"] == "assessment"
    assert stored_metadata_list[0]["source_file"] == "exam_2024.pdf"
    assert stored_metadata_list[1]["reference_type"] == "lecture"
    assert stored_metadata_list[1]["source_file"] == "lecture_notes.pdf"


def test_batch_store_filters_none_but_preserves_reference_type(
    mock_openai_client, mock_chromadb
):
    """Test that None values are filtered but reference_type is preserved."""
    mock_client, mock_collection = mock_chromadb
    service = EmbeddingService(
        openai_client=mock_openai_client, vector_db_client=mock_client
    )

    texts = ["text 1"]
    metadata_list = [
        {
            "chunk_id": "chunk_1",
            "class_id": "class_1",
            "reference_type": "assessment",
            "source_file": "test.pdf",
            "exam_source": None,  # Should be filtered
            "exam_type": None,  # Should be filtered
        },
    ]

    chunk_ids = service.batch_store(texts, metadata_list)

    assert len(chunk_ids) == 1
    mock_collection.add.assert_called_once()

    call_args = mock_collection.add.call_args
    stored_metadata_list = call_args.kwargs["metadatas"]

    # None values should be filtered out
    assert "exam_source" not in stored_metadata_list[0]
    assert "exam_type" not in stored_metadata_list[0]

    # reference_type and source_file should be preserved
    assert stored_metadata_list[0]["reference_type"] == "assessment"
    assert stored_metadata_list[0]["source_file"] == "test.pdf"


def test_list_embeddings_by_class_returns_reference_type_and_source_file(
    mock_openai_client, mock_chromadb
):
    """Test that list_embeddings_by_class returns items with reference_type and source_file."""
    mock_client, mock_collection = mock_chromadb
    service = EmbeddingService(
        openai_client=mock_openai_client, vector_db_client=mock_client
    )

    # Mock collection.get to return data with reference_type and source_file
    mock_collection.get.return_value = {
        "ids": ["chunk_1", "chunk_2"],
        "documents": ["Text 1", "Text 2"],
        "metadatas": [
            {
                "source": "test",
                "class_id": "class_1",
                "reference_type": "assessment",
                "source_file": "exam_1.pdf",
            },
            {
                "source": "test",
                "class_id": "class_1",
                "reference_type": "lecture",
                "source_file": "lecture_1.pdf",
            },
        ],
    }

    results = service.list_embeddings_by_class("class_1")

    assert len(results) == 2
    assert results[0]["metadata"]["reference_type"] == "assessment"
    assert results[0]["metadata"]["source_file"] == "exam_1.pdf"
    assert results[1]["metadata"]["reference_type"] == "lecture"
    assert results[1]["metadata"]["source_file"] == "lecture_1.pdf"
