"""OCR route endpoint."""

import time
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status

from app.config import settings
from app.models.ocr_models import OCRResponse
from app.services.ocr_service import OCRService
from app.utils.file_utils import (cleanup_temp_file, save_temp_file,
                                  validate_image_file)

router = APIRouter(prefix="/ocr", tags=["ocr"])
limiter = Limiter(key_func=get_remote_address)


@router.post("", response_model=OCRResponse, status_code=status.HTTP_200_OK)
async def extract_text(request: Request, file: UploadFile = File(...)):
    # Rate limiting is handled by the limiter attached to the router
    if limiter and settings.rate_limit_enabled:
        limiter.limit(f"{settings.rate_limit_per_minute}/minute")(extract_text)
    """
    Extract text from uploaded image using OCR.

    Args:
        file: Image file (PNG, JPG, JPEG, max 10MB)

    Returns:
        OCRResponse with extracted text and metadata
    """
    temp_path: Path | None = None
    try:
        # Validate file
        validate_image_file(file)

        # Save temporary file
        temp_path = save_temp_file(file)

        # Initialize OCR service
        ocr_service = OCRService()

        # Extract text
        start_time = time.time()
        text, confidence = ocr_service.extract_with_confidence(temp_path)
        processing_time_ms = int((time.time() - start_time) * 1000)

        return OCRResponse(
            text=text,
            confidence=confidence,
            processing_time_ms=processing_time_ms,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR processing failed: {str(e)}",
        ) from e
    finally:
        # Clean up temporary file
        if temp_path:
            cleanup_temp_file(temp_path)
