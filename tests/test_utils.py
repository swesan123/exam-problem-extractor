"""Unit tests for utility functions."""

from pathlib import Path

import pytest

from app.utils import chunking, file_utils, text_cleaning


def test_clean_ocr_text():
    """Test OCR text cleaning."""
    dirty_text = "Hello   world\n\n\nTest"
    cleaned = text_cleaning.clean_ocr_text(dirty_text)
    assert "  " not in cleaned
    assert cleaned.count("\n\n") <= 1


def test_normalize_whitespace():
    """Test whitespace normalization."""
    text = "Hello    world"
    normalized = text_cleaning.normalize_whitespace(text)
    assert "  " not in normalized


def test_chunk_text():
    """Test text chunking."""
    text = "A" * 2000
    chunks = chunking.chunk_text(text, chunk_size=1000, overlap=200)
    assert len(chunks) > 1
    assert all(len(chunk) <= 1000 for chunk in chunks)


def test_chunk_by_sentences():
    """Test sentence-based chunking."""
    text = "First sentence. Second sentence. Third sentence."
    chunks = chunking.chunk_by_sentences(text, max_chunk_size=50)
    assert len(chunks) >= 1


def test_smart_chunk():
    """Test smart chunking."""
    text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
    chunks = chunking.smart_chunk(text, max_size=50)
    assert len(chunks) >= 1
