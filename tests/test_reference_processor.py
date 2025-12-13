"""Unit tests for reference processor service."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.reference_processor import ReferenceProcessor


@pytest.fixture
def mock_ocr_service():
    """Create a mock OCR service."""
    service = MagicMock()
    service.extract_text.return_value = "Extracted text from file"
    return service


@pytest.fixture
def mock_embedding_service():
    """Create a mock embedding service."""
    service = MagicMock()
    service.batch_store.return_value = ["chunk_1", "chunk_2"]
    return service


@pytest.fixture
def sample_file_path(tmp_path):
    """Create a sample file for testing."""
    file_path = tmp_path / "test_file.pdf"
    file_path.write_bytes(b"fake pdf data")
    return file_path


@pytest.fixture
def sample_metadata():
    """Create sample metadata."""
    return {
        "class_id": "class_1",
        "exam_source": "test_source",
        "exam_type": "midterm",
        "reference_type": "assessment",
    }


class TestStoreEmbeddingsBatch:
    """Test _store_embeddings_batch method."""

    def test_stores_original_filename(self, mock_embedding_service, sample_file_path):
        """Test that original filename is stored (not temp filename)."""
        processor = ReferenceProcessor()
        chunks = ["chunk 1", "chunk 2"]
        original_filename = "original_file.pdf"
        metadata = {"class_id": "class_1", "reference_type": "assessment"}

        with patch(
            "app.services.reference_processor.EmbeddingService",
            return_value=mock_embedding_service,
        ):
            processor._store_embeddings_batch(
                chunks, sample_file_path, original_filename, metadata
            )

        # Verify batch_store was called
        assert mock_embedding_service.batch_store.called

        # Get the metadata_list passed to batch_store
        call_args = mock_embedding_service.batch_store.call_args
        metadata_list = call_args[0][1]  # Second positional argument

        # Verify original filename is stored in source_file
        assert metadata_list[0]["source_file"] == original_filename
        assert metadata_list[1]["source_file"] == original_filename

        # Verify temp filename is NOT used
        assert metadata_list[0]["source_file"] != sample_file_path.name

    def test_stores_reference_type(self, mock_embedding_service, sample_file_path):
        """Test that reference_type is stored in metadata."""
        processor = ReferenceProcessor()
        chunks = ["chunk 1"]
        original_filename = "test.pdf"
        metadata = {
            "class_id": "class_1",
            "reference_type": "lecture",
        }

        with patch(
            "app.services.reference_processor.EmbeddingService",
            return_value=mock_embedding_service,
        ):
            processor._store_embeddings_batch(
                chunks, sample_file_path, original_filename, metadata
            )

        call_args = mock_embedding_service.batch_store.call_args
        metadata_list = call_args[0][1]

        assert metadata_list[0]["reference_type"] == "lecture"

    def test_metadata_includes_source_file_and_reference_type(
        self, mock_embedding_service, sample_file_path
    ):
        """Test metadata includes both source_file and reference_type."""
        processor = ReferenceProcessor()
        chunks = ["chunk 1"]
        original_filename = "exam_2024.pdf"
        metadata = {
            "class_id": "class_1",
            "exam_source": "test_source",
            "reference_type": "assessment",
        }

        with patch(
            "app.services.reference_processor.EmbeddingService",
            return_value=mock_embedding_service,
        ):
            processor._store_embeddings_batch(
                chunks, sample_file_path, original_filename, metadata
            )

        call_args = mock_embedding_service.batch_store.call_args
        metadata_list = call_args[0][1]
        stored_metadata = metadata_list[0]

        assert "source_file" in stored_metadata
        assert stored_metadata["source_file"] == original_filename
        assert "reference_type" in stored_metadata
        assert stored_metadata["reference_type"] == "assessment"
        assert stored_metadata["class_id"] == "class_1"
        assert stored_metadata["exam_source"] == "test_source"

    def test_chunk_id_uses_original_filename_stem(
        self, mock_embedding_service, sample_file_path
    ):
        """Test chunk_id generation uses original filename stem."""
        processor = ReferenceProcessor()
        chunks = ["chunk 1", "chunk 2", "chunk 3"]
        original_filename = "my_exam_file.pdf"
        metadata = {"class_id": "class_1"}

        with patch(
            "app.services.reference_processor.EmbeddingService",
            return_value=mock_embedding_service,
        ):
            processor._store_embeddings_batch(
                chunks, sample_file_path, original_filename, metadata
            )

        call_args = mock_embedding_service.batch_store.call_args
        metadata_list = call_args[0][1]

        # Verify chunk_ids use original filename stem
        assert metadata_list[0]["chunk_id"] == "my_exam_file_chunk_0"
        assert metadata_list[1]["chunk_id"] == "my_exam_file_chunk_1"
        assert metadata_list[2]["chunk_id"] == "my_exam_file_chunk_2"

    def test_processing_with_missing_original_filename(
        self, mock_embedding_service, sample_file_path
    ):
        """Test processing with missing original filename (fallback to temp name)."""
        processor = ReferenceProcessor()
        chunks = ["chunk 1"]
        original_filename = ""  # Empty filename
        metadata = {"class_id": "class_1"}

        with patch(
            "app.services.reference_processor.EmbeddingService",
            return_value=mock_embedding_service,
        ):
            processor._store_embeddings_batch(
                chunks, sample_file_path, original_filename, metadata
            )

        call_args = mock_embedding_service.batch_store.call_args
        metadata_list = call_args[0][1]

        # Should use temp file name as fallback
        assert metadata_list[0]["source_file"] == ""
        # chunk_id should use empty stem, which becomes just "_chunk_0"
        assert metadata_list[0]["chunk_id"] == "_chunk_0"

    def test_preserves_all_metadata_fields(
        self, mock_embedding_service, sample_file_path, sample_metadata
    ):
        """Test that all metadata fields are preserved."""
        processor = ReferenceProcessor()
        chunks = ["chunk 1"]
        original_filename = "test.pdf"

        with patch(
            "app.services.reference_processor.EmbeddingService",
            return_value=mock_embedding_service,
        ):
            processor._store_embeddings_batch(
                chunks, sample_file_path, original_filename, sample_metadata
            )

        call_args = mock_embedding_service.batch_store.call_args
        metadata_list = call_args[0][1]
        stored_metadata = metadata_list[0]

        # Verify all original metadata fields are present
        assert stored_metadata["class_id"] == sample_metadata["class_id"]
        assert stored_metadata["exam_source"] == sample_metadata["exam_source"]
        assert stored_metadata["exam_type"] == sample_metadata["exam_type"]
        assert stored_metadata["reference_type"] == sample_metadata["reference_type"]
        assert stored_metadata["source_file"] == original_filename


class TestProcessSingleFile:
    """Test _process_single_file method."""

    def test_receives_and_uses_original_filename(
        self, mock_ocr_service, mock_embedding_service, sample_file_path
    ):
        """Test that _process_single_file receives and uses original filename."""
        processor = ReferenceProcessor()
        original_filename = "original_document.pdf"
        metadata = {"class_id": "class_1", "reference_type": "lecture"}

        mock_db = MagicMock()
        # Mock the database query methods that might be called
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Create a non-PDF file path for testing
        from pathlib import Path
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            test_image_path = Path(tmp.name)
            test_image_path.write_bytes(b"fake image data")
        
        try:
            with patch(
                "app.services.reference_processor.OCRService", return_value=mock_ocr_service
            ), patch(
                "app.services.reference_processor.EmbeddingService",
                return_value=mock_embedding_service,
            ), patch(
                "app.services.reference_processor.smart_chunk", return_value=["chunk 1"]
            ), patch.object(
                processor, "_update_file_status"
            ), patch.object(
                processor, "_increment_processed_files"
            ):
                result = processor._process_single_file(
                    "job_1", test_image_path, original_filename, metadata, mock_db
                )
        finally:
            # Clean up
            if test_image_path.exists():
                test_image_path.unlink()

        assert result["success"] is True

        # Verify batch_store was called with original filename
        call_args = mock_embedding_service.batch_store.call_args
        metadata_list = call_args[0][1]
        assert metadata_list[0]["source_file"] == original_filename

