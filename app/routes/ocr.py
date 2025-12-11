"""OCR route endpoint."""
import logging
import time
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status

from app.models.ocr_models import OCRResponse
from app.services.ocr_service import OCRService
from app.utils.file_utils import (
    cleanup_temp_file,
    convert_pdf_to_images,
    save_temp_file,
    validate_upload_file,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ocr", tags=["ocr"])


@router.post("", response_model=OCRResponse, status_code=status.HTTP_200_OK)
async def extract_text(request: Request, file: UploadFile = File(...)):
    """
    Extract text from uploaded image or PDF using OCR.

    Args:
        request: FastAPI Request object
        file: Image file (PNG, JPG, JPEG) or PDF file (max 10MB)

    Returns:
        OCRResponse with extracted text and metadata
    """
    temp_path: Path | None = None
    try:
        logger.info(
            f"OCR request received: filename={file.filename}, "
            f"content_type={file.content_type}, size={file.size if hasattr(file, 'size') else 'unknown'}"
        )

        # Validate file
        validate_upload_file(file)

        # Save temporary file
        temp_path = save_temp_file(file)
        logger.debug(f"Saved temporary file: {temp_path}")

        # Initialize OCR service
        ocr_service = OCRService()

        start_time = time.time()

        # Handle PDF by converting each page to an image
        if file.content_type == "application/pdf":
            image_paths = convert_pdf_to_images(temp_path)
            all_text_parts = []
            confidence_values = []

            try:
                for page_num, image_path in enumerate(image_paths, start=1):
                    text, confidence = ocr_service.extract_with_confidence(image_path)
                    page_header = f"=== Page {page_num} ===\n"
                    all_text_parts.append(page_header + text)
                    if confidence is not None:
                        confidence_values.append(confidence)

                combined_text = "\n\n".join(all_text_parts)
                avg_confidence = (
                    sum(confidence_values) / len(confidence_values)
                    if confidence_values
                    else None
                )
            finally:
                # Clean up generated images
                for img_path in image_paths:
                    cleanup_temp_file(img_path)

            processing_time_ms = int((time.time() - start_time) * 1000)

            return OCRResponse(
                text=combined_text,
                confidence=avg_confidence,
                processing_time_ms=processing_time_ms,
            )

        # Default image flow
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
        logger.error(f"OCR processing failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR processing failed: {str(e)}",
        ) from e
    finally:
        # Clean up temporary file
        if temp_path:
            cleanup_temp_file(temp_path)

