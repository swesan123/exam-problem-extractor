"""File handling utilities."""
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import UploadFile, HTTPException, status


ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg"}
MAX_FILE_SIZE_MB = 10


def validate_image_file(file: UploadFile) -> bool:
    """
    Validate that the uploaded file is a valid image.

    Args:
        file: FastAPI UploadFile object

    Returns:
        True if valid, raises HTTPException if invalid

    Raises:
        HTTPException: If file type or size is invalid
    """
    # Check MIME type
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed types: PNG, JPG, JPEG. Got: {file.content_type}",
        )

    # Note: File size validation should be done at the FastAPI level
    # or by reading the file content and checking size
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
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
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

