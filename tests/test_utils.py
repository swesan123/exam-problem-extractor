"""Unit tests for utility functions."""

import io
import tempfile
from pathlib import Path

import pytest
from fastapi import HTTPException, UploadFile

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


class TestFileUtils:
    """Tests for file utility functions."""

    def test_validate_upload_file_image(self):
        """Test validation of image files."""
        file = UploadFile(
            filename="test.png",
            file=io.BytesIO(b"fake image content"),
            headers={"content-type": "image/png"},
        )
        result = file_utils.validate_upload_file(file)
        assert result is True

    def test_validate_upload_file_pdf(self):
        """Test validation of PDF files."""
        file = UploadFile(
            filename="test.pdf",
            file=io.BytesIO(b"%PDF-1.4 fake pdf content"),
            headers={"content-type": "application/pdf"},
        )
        result = file_utils.validate_upload_file(file)
        assert result is True

    def test_validate_upload_file_invalid(self):
        """Test validation rejects invalid file types."""
        file = UploadFile(
            filename="test.txt",
            file=io.BytesIO(b"text content"),
            headers={"content-type": "text/plain"},
        )
        with pytest.raises(HTTPException) as exc_info:
            file_utils.validate_upload_file(file)
        assert exc_info.value.status_code == 400

    def test_convert_pdf_to_images(self):
        """Test PDF to images conversion."""
        # Create a minimal valid PDF
        pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>
endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
trailer
<< /Size 4 /Root 1 0 R >>
startxref
174
%%EOF"""

        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_content)
            pdf_path = Path(tmp.name)

        try:
            # Convert PDF to images
            image_paths = file_utils.convert_pdf_to_images(pdf_path)

            # Should create at least one image
            assert len(image_paths) >= 1
            # All paths should exist
            for img_path in image_paths:
                assert img_path.exists()
                # Clean up
                file_utils.cleanup_temp_file(img_path)
        finally:
            # Clean up PDF
            if pdf_path.exists():
                pdf_path.unlink()
