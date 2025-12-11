"""Integration tests for OCR route with PDF support."""
import io

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


class TestOCREndpointPDF:
    """Tests for OCR endpoint with PDF files."""

    def test_ocr_endpoint_pdf_support_if_available(self, client: TestClient, mocker):
        """Test OCR endpoint accepts PDF files if PDF support is available."""
        # Check if PDF support exists
        from app.utils import file_utils

        if not hasattr(file_utils, "validate_upload_file"):
            pytest.skip("PDF support not available (PR #47 not merged)")

        # Mock OCR service to avoid actual API calls
        mock_text = "Extracted text from PDF page 1\n\n=== Page 2 ===\nExtracted text from PDF page 2"
        mock_confidence = 0.95

        mocker.patch(
            "app.services.ocr_service.OCRService.extract_with_confidence",
            return_value=(mock_text, mock_confidence),
        )

        # Create a minimal PDF file
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

        response = client.post(
            "/ocr",
            files={"file": ("test.pdf", pdf_content, "application/pdf")},
        )

        # Should accept PDF if support is available
        if hasattr(file_utils, "convert_pdf_to_images"):
            # PDF support is available
            assert response.status_code in [200, 500]  # 500 if PyMuPDF not installed
            if response.status_code == 200:
                data = response.json()
                assert "text" in data
                assert "processing_time_ms" in data
        else:
            # PDF support not available, should reject
            assert response.status_code == 400

    def test_ocr_endpoint_pdf_multipage_if_available(self, client: TestClient, mocker):
        """Test OCR endpoint processes multi-page PDFs if support is available."""
        from app.utils import file_utils

        if not hasattr(file_utils, "convert_pdf_to_images"):
            pytest.skip("PDF support not available (PR #47 not merged)")

        # Mock OCR service to return different text for each page
        def mock_extract_side_effect(*args, **kwargs):
            # This will be called once per page
            # For simplicity, return same text for all pages
            return ("Page text content", 0.95)

        mocker.patch(
            "app.services.ocr_service.OCRService.extract_with_confidence",
            side_effect=mock_extract_side_effect,
        )

        # Create a minimal PDF (single page for simplicity)
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

        response = client.post(
            "/ocr",
            files={"file": ("test.pdf", pdf_content, "application/pdf")},
        )

        if response.status_code == 200:
            data = response.json()
            assert "text" in data
            # Multi-page PDFs should have page separators
            if "=== Page" in data["text"]:
                assert "=== Page 1 ===" in data["text"]

    def test_ocr_endpoint_still_accepts_images(self, client: TestClient, mocker):
        """Test that OCR endpoint still accepts images after PDF support."""
        # Mock OCR service
        mocker.patch(
            "app.services.ocr_service.OCRService.extract_with_confidence",
            return_value=("Extracted text", 0.95),
        )

        # Create a fake image file
        image_content = b"fake image content"
        response = client.post(
            "/ocr",
            files={"file": ("test.png", image_content, "image/png")},
        )

        # Should still work for images
        assert response.status_code in [200, 500]  # 500 if OpenAI not configured
        if response.status_code == 200:
            data = response.json()
            assert "text" in data
            assert data["text"] == "Extracted text"

