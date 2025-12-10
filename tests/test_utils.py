"""Unit tests for utility functions."""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, mock_open
from io import BytesIO

from fastapi import UploadFile, HTTPException

from app.utils import chunking, file_utils, text_cleaning


# Text Cleaning Tests
def test_clean_ocr_text():
    """Test OCR text cleaning."""
    dirty_text = "Hello   world\n\n\nTest"
    cleaned = text_cleaning.clean_ocr_text(dirty_text)
    assert "  " not in cleaned
    assert cleaned.count("\n\n") <= 1


def test_clean_ocr_text_empty():
    """Test OCR text cleaning with empty string."""
    assert text_cleaning.clean_ocr_text("") == ""
    assert text_cleaning.clean_ocr_text(None) == ""


def test_remove_artifacts():
    """Test artifact removal."""
    text = "Hello\x00world\x01test"
    cleaned = text_cleaning.remove_artifacts(text)
    assert "\x00" not in cleaned
    assert "\x01" not in cleaned


def test_remove_artifacts_punctuation():
    """Test removal of excessive punctuation."""
    text = "Hello....world---test"
    cleaned = text_cleaning.remove_artifacts(text)
    assert "...." not in cleaned
    assert "---" in cleaned  # Should be normalized to ---


def test_normalize_whitespace():
    """Test whitespace normalization."""
    text = "Hello    world"
    normalized = text_cleaning.normalize_whitespace(text)
    assert "  " not in normalized
    assert normalized == "Hello world"


def test_normalize_whitespace_newlines():
    """Test newline normalization."""
    text = "Line 1\n\n\n\nLine 2"
    normalized = text_cleaning.normalize_whitespace(text)
    assert normalized.count("\n\n") <= 1


def test_normalize_whitespace_empty():
    """Test whitespace normalization with empty string."""
    assert text_cleaning.normalize_whitespace("") == ""


def test_extract_math_expressions():
    """Test mathematical expression extraction."""
    text = "The equation x^2 + y^2 = r^2 is a circle."
    expressions = text_cleaning.extract_math_expressions(text)
    assert "x^2" in expressions
    assert "y^2" in expressions
    assert "r^2" in expressions


def test_extract_math_expressions_empty():
    """Test math expression extraction with empty text."""
    assert text_cleaning.extract_math_expressions("") == []


# Chunking Tests
def test_chunk_text():
    """Test text chunking."""
    text = "A" * 2000
    chunks = chunking.chunk_text(text, chunk_size=1000, overlap=200)
    assert len(chunks) > 1
    assert all(len(chunk) <= 1000 for chunk in chunks)


def test_chunk_text_small():
    """Test chunking with text smaller than chunk size."""
    text = "Short text"
    chunks = chunking.chunk_text(text, chunk_size=1000, overlap=200)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunk_text_empty():
    """Test chunking with empty text."""
    assert chunking.chunk_text("", chunk_size=1000, overlap=200) == []


def test_chunk_by_sentences():
    """Test sentence-based chunking."""
    text = "First sentence. Second sentence. Third sentence."
    chunks = chunking.chunk_by_sentences(text, max_chunk_size=50)
    assert len(chunks) >= 1
    assert all("sentence" in chunk for chunk in chunks)


def test_chunk_by_sentences_empty():
    """Test sentence chunking with empty text."""
    assert chunking.chunk_by_sentences("", max_chunk_size=1000) == []


def test_smart_chunk():
    """Test smart chunking."""
    text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
    chunks = chunking.smart_chunk(text, max_size=50)
    assert len(chunks) >= 1


def test_smart_chunk_single_paragraph():
    """Test smart chunking with single paragraph."""
    text = "Single paragraph text."
    chunks = chunking.smart_chunk(text, max_size=1000)
    assert len(chunks) == 1


def test_smart_chunk_empty():
    """Test smart chunking with empty text."""
    assert chunking.smart_chunk("", max_size=1000) == []


# File Utils Tests
def test_validate_image_file_valid():
    """Test validation of valid image file."""
    file = MagicMock(spec=UploadFile)
    file.content_type = "image/png"
    assert file_utils.validate_image_file(file) is True


def test_validate_image_file_invalid_type():
    """Test validation with invalid file type."""
    file = MagicMock(spec=UploadFile)
    file.content_type = "text/plain"
    with pytest.raises(HTTPException) as exc_info:
        file_utils.validate_image_file(file)
    assert exc_info.value.status_code == 400


@pytest.mark.parametrize("content_type", ["image/png", "image/jpeg", "image/jpg"])
def test_validate_image_file_allowed_types(content_type):
    """Test validation with all allowed image types."""
    file = MagicMock(spec=UploadFile)
    file.content_type = content_type
    assert file_utils.validate_image_file(file) is True


def test_get_file_size_mb(tmp_path):
    """Test getting file size in MB."""
    test_file = tmp_path / "test.txt"
    # Write 1MB of data
    test_file.write_bytes(b"0" * (1024 * 1024))
    size_mb = file_utils.get_file_size_mb(test_file)
    assert abs(size_mb - 1.0) < 0.01


def test_get_file_size_mb_nonexistent():
    """Test getting size of nonexistent file."""
    assert file_utils.get_file_size_mb(Path("nonexistent.txt")) == 0.0


def test_cleanup_temp_file(tmp_path):
    """Test temporary file cleanup."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")
    assert test_file.exists()
    file_utils.cleanup_temp_file(test_file)
    assert not test_file.exists()


def test_cleanup_temp_file_nonexistent():
    """Test cleanup of nonexistent file (should not raise error)."""
    file_utils.cleanup_temp_file(Path("nonexistent.txt"))


def test_save_temp_file_valid(tmp_path, monkeypatch):
    """Test saving valid temporary file."""
    # Mock tempfile to use our tmp_path
    import app.utils.file_utils as file_utils_module
    original_named_tempfile = file_utils_module.tempfile.NamedTemporaryFile
    
    def mock_named_tempfile(*args, **kwargs):
        kwargs['dir'] = str(tmp_path)
        return original_named_tempfile(*args, **kwargs)
    
    monkeypatch.setattr(file_utils_module.tempfile, "NamedTemporaryFile", mock_named_tempfile)
    
    file = MagicMock(spec=UploadFile)
    file.filename = "test.png"
    file.content_type = "image/png"
    file.file = BytesIO(b"small image data")
    
    temp_path = file_utils.save_temp_file(file)
    assert temp_path.exists()
    assert temp_path.read_bytes() == b"small image data"
    
    # Cleanup
    file_utils.cleanup_temp_file(temp_path)


def test_save_temp_file_too_large(tmp_path, monkeypatch):
    """Test saving file that exceeds size limit."""
    import app.utils.file_utils as file_utils_module
    original_named_tempfile = file_utils_module.tempfile.NamedTemporaryFile
    
    def mock_named_tempfile(*args, **kwargs):
        kwargs['dir'] = str(tmp_path)
        return original_named_tempfile(*args, **kwargs)
    
    monkeypatch.setattr(file_utils_module.tempfile, "NamedTemporaryFile", mock_named_tempfile)
    
    # Create file larger than 10MB
    large_data = b"0" * (11 * 1024 * 1024)
    file = MagicMock(spec=UploadFile)
    file.filename = "large.png"
    file.content_type = "image/png"
    file.file = BytesIO(large_data)
    
    with pytest.raises(HTTPException) as exc_info:
        file_utils.save_temp_file(file)
    assert exc_info.value.status_code == 413
