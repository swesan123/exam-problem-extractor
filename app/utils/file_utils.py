"""File handling utilities."""
import tempfile
from pathlib import Path
from typing import List, Optional

import fitz  # PyMuPDF
from fastapi import HTTPException, UploadFile, status


ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg"}
ALLOWED_PDF_TYPES = {"application/pdf"}
MAX_FILE_SIZE_MB = 10


def validate_upload_file(file: UploadFile) -> bool:
    """
    Validate that the uploaded file is a supported type (image or PDF).

    Args:
        file: FastAPI UploadFile object

    Returns:
        True if valid, raises HTTPException if invalid

    Raises:
        HTTPException: If file type or size is invalid
    """
    if file.content_type not in ALLOWED_IMAGE_TYPES | ALLOWED_PDF_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid file type. Allowed types: PNG, JPG, JPEG, PDF. "
                f"Got: {file.content_type}"
            ),
        )

    # Note: File size validation is performed after saving to disk
    return True


def save_temp_file(file: UploadFile) -> Path:
    """
    Save uploaded file to temporary location.

    Args:
        file: FastAPI UploadFile object

    Returns:
        Path to the saved temporary file
    """
    # Create temporary file
    suffix = Path(file.filename).suffix if file.filename else ".tmp"
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    temp_path = Path(temp_file.name)

    try:
        # Write file content
        content = file.file.read()
        temp_path.write_bytes(content)

        # Validate file size
        size_mb = get_file_size_mb(temp_path)
        if size_mb > MAX_FILE_SIZE_MB:
            cleanup_temp_file(temp_path)
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"File size ({size_mb:.2f} MB) exceeds maximum allowed size ({MAX_FILE_SIZE_MB} MB)",
            )

        return temp_path
    except HTTPException:
        raise
    except Exception as e:
        cleanup_temp_file(temp_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving file: {str(e)}",
        )


def cleanup_temp_file(path: Path) -> None:
    """
    Delete a temporary file.

    Args:
        path: Path to the file to delete
    """
    try:
        if path.exists():
            path.unlink()
    except Exception:
        # Ignore errors during cleanup
        pass


def convert_pdf_to_images(pdf_path: Path) -> List[Path]:
    """
    Convert PDF pages to temporary image files.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        List of paths to generated image files (one per page)
    """
    image_paths: List[Path] = []
    doc = fitz.open(pdf_path)

    try:
        for page_index in range(len(doc)):
            page = doc.load_page(page_index)
            pix = page.get_pixmap()
            image_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            image_path = Path(image_temp.name)
            image_path.write_bytes(pix.tobytes("png"))
            image_paths.append(image_path)
    finally:
        doc.close()

    return image_paths


def get_file_size_mb(path: Path) -> float:
    """
    Get file size in megabytes.

    Args:
        path: Path to the file

    Returns:
        File size in megabytes
    """
    if not path.exists():
        return 0.0
    size_bytes = path.stat().st_size
    return size_bytes / (1024 * 1024)

