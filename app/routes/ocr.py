"""OCR route endpoint."""
import logging
import time
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.models.ocr_models import OCRResponse
from app.services.ocr_service import OCRService
from app.utils.file_utils import cleanup_temp_file, save_temp_file, validate_image_file

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ocr", tags=["ocr"])


@router.post("", response_model=OCRResponse, status_code=status.HTTP_200_OK)
async def extract_text(file: UploadFile = File(...)):
    """
    Extract text from uploaded image using OCR.

    Args:
        file: Image file (PNG, JPG, JPEG, max 10MB)

    Returns:
        OCRResponse with extracted text and metadata
    """
    temp_path: Path | None = None
    try:
        logger.info(f"OCR request received. File: {file.filename}, Content-Type: {file.content_type}")
        
        # Validate file
        validate_image_file(file)

        # Save temporary file
        temp_path = save_temp_file(file)
        logger.info(f"Temporary file saved: {temp_path}")

        # Initialize OCR service
        ocr_service = OCRService()

        # Extract text
        start_time = time.time()
        text, confidence = ocr_service.extract_with_confidence(temp_path)
        processing_time_ms = int((time.time() - start_time) * 1000)

        logger.info(f"OCR extraction completed successfully. Processing time: {processing_time_ms}ms")

        return OCRResponse(
            text=text,
            confidence=confidence,
            processing_time_ms=processing_time_ms,
        )

    except HTTPException as e:
        logger.warning(f"OCR request validation error: {e.detail}")
        raise
    except Exception as e:
        error_message = str(e)
        logger.error(
            f"OCR processing failed: {error_message}",
            exc_info=True,
            extra={
                "error_type": type(e).__name__,
                "error_message": error_message,
                "file_name": file.filename if file else None,
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR processing failed: {error_message}",
        ) from e
    finally:
        # Clean up temporary file
        if temp_path:
            cleanup_temp_file(temp_path)
            logger.debug(f"Cleaned up temporary file: {temp_path}")

