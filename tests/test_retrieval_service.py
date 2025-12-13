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
    service.client = MagicMock()  # Add client attribute for RetrievalService
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


class TestRetrievalFiltering:
    """Test retrieval service filtering by class_id and reference_type."""

    def test_retrieve_with_scores_class_id_filter_only(self, mock_embedding_service):
        """Test retrieve_with_scores with class_id filter only."""
        service = RetrievalService(mock_embedding_service)
        results = service.retrieve_with_scores("test query", top_k=2, class_id="class_1")

        assert len(results) == 2
        # Verify query was called with where clause
        call_args = mock_embedding_service.collection.query.call_args
        assert "where" in call_args.kwargs
        assert call_args.kwargs["where"] == {"class_id": "class_1"}

    def test_retrieve_with_scores_reference_type_filter_only(
        self, mock_embedding_service
    ):
        """Test retrieve_with_scores with reference_type filter only."""
        service = RetrievalService(mock_embedding_service)
        results = service.retrieve_with_scores(
            "test query", top_k=2, reference_type="assessment"
        )

        assert len(results) == 2
        # Verify query was called with where clause
        call_args = mock_embedding_service.collection.query.call_args
        assert "where" in call_args.kwargs
        assert call_args.kwargs["where"] == {"reference_type": "assessment"}

    def test_retrieve_with_scores_both_filters(self, mock_embedding_service):
        """Test retrieve_with_scores with both class_id and reference_type filters."""
        service = RetrievalService(mock_embedding_service)
        results = service.retrieve_with_scores(
            "test query",
            top_k=2,
            class_id="class_1",
            reference_type="lecture",
        )

        assert len(results) == 2
        # Verify query was called with combined where clause
        call_args = mock_embedding_service.collection.query.call_args
        assert "where" in call_args.kwargs
        assert call_args.kwargs["where"] == {
            "class_id": "class_1",
            "reference_type": "lecture",
        }

    def test_retrieve_with_scores_without_filters(self, mock_embedding_service):
        """Test retrieve_with_scores without filters (backward compatibility)."""
        service = RetrievalService(mock_embedding_service)
        results = service.retrieve_with_scores("test query", top_k=2)

        assert len(results) == 2
        # Verify query was called without where clause
        call_args = mock_embedding_service.collection.query.call_args
        assert "where" not in call_args.kwargs or call_args.kwargs["where"] is None

    def test_filtering_returns_only_matching_class_id(self, mock_embedding_service):
        """Test filtering returns only matching class_id."""
        # Mock collection to return filtered results
        mock_embedding_service.collection.query.return_value = {
            "ids": [["chunk_1"]],
            "documents": [["Text 1"]],
            "metadatas": [[{"class_id": "class_1", "source": "test"}]],
            "distances": [[0.1]],
        }

        service = RetrievalService(mock_embedding_service)
        results = service.retrieve_with_scores("test query", top_k=5, class_id="class_1")

        assert len(results) == 1
        assert results[0].metadata["class_id"] == "class_1"

    def test_filtering_returns_only_matching_reference_type(
        self, mock_embedding_service
    ):
        """Test filtering returns only matching reference_type."""
        # Mock collection to return filtered results
        mock_embedding_service.collection.query.return_value = {
            "ids": [["chunk_1", "chunk_2"]],
            "documents": [["Text 1", "Text 2"]],
            "metadatas": [
                [
                    {"reference_type": "assessment", "source": "test"},
                    {"reference_type": "assessment", "source": "test"},
                ]
            ],
            "distances": [[0.1, 0.2]],
        }

        service = RetrievalService(mock_embedding_service)
        results = service.retrieve_with_scores(
            "test query", top_k=5, reference_type="assessment"
        )

        assert len(results) == 2
        assert all(r.metadata["reference_type"] == "assessment" for r in results)

    def test_filtering_with_nonexistent_class_id_returns_empty(
        self, mock_embedding_service
    ):
        """Test filtering with non-existent class_id returns empty results."""
        # Mock collection to return empty results
        mock_embedding_service.collection.query.return_value = {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }

        service = RetrievalService(mock_embedding_service)
        results = service.retrieve_with_scores(
            "test query", top_k=5, class_id="nonexistent_class"
        )

        assert len(results) == 0

    def test_filtering_with_nonexistent_reference_type_returns_empty(
        self, mock_embedding_service
    ):
        """Test filtering with non-existent reference_type returns empty results."""
        # Mock collection to return empty results
        mock_embedding_service.collection.query.return_value = {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }

        service = RetrievalService(mock_embedding_service)
        results = service.retrieve_with_scores(
            "test query", top_k=5, reference_type="nonexistent_type"
        )

        assert len(results) == 0

    def test_retrieve_method_passes_filters_correctly(self, mock_embedding_service):
        """Test retrieve() method passes filters correctly."""
        service = RetrievalService(mock_embedding_service)
        results = service.retrieve(
            "test query", top_k=2, class_id="class_1", reference_type="assessment"
        )

        assert len(results) == 2
        # Verify query was called with where clause
        call_args = mock_embedding_service.collection.query.call_args
        assert "where" in call_args.kwargs
        assert call_args.kwargs["where"] == {
            "class_id": "class_1",
            "reference_type": "assessment",
        }

    def test_chromadb_where_clause_single_filter(self, mock_embedding_service):
        """Test ChromaDB where clause construction for single filter."""
        service = RetrievalService(mock_embedding_service)
        service.retrieve_with_scores("test query", top_k=2, class_id="class_1")

        call_args = mock_embedding_service.collection.query.call_args
        where_clause = call_args.kwargs.get("where")
        assert where_clause == {"class_id": "class_1"}

    def test_chromadb_where_clause_multiple_filters(self, mock_embedding_service):
        """Test ChromaDB where clause construction for multiple filters."""
        service = RetrievalService(mock_embedding_service)
        service.retrieve_with_scores(
            "test query",
            top_k=2,
            class_id="class_1",
            reference_type="lecture",
        )

        call_args = mock_embedding_service.collection.query.call_args
        where_clause = call_args.kwargs.get("where")
        assert where_clause == {"class_id": "class_1", "reference_type": "lecture"}

    def test_empty_results_when_filters_match_nothing(self, mock_embedding_service):
        """Test empty results when filters match nothing."""
        # Mock collection to return empty results
        mock_embedding_service.collection.query.return_value = {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }

        service = RetrievalService(mock_embedding_service)
        results = service.retrieve_with_scores(
            "test query",
            top_k=5,
            class_id="class_1",
            reference_type="assessment",
        )

        assert len(results) == 0

