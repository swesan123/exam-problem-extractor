"""OCR service for extracting text from images using OpenAI Vision API."""
import base64
import logging
import time
from pathlib import Path
from typing import Optional, Tuple

from openai import OpenAI

from app.config import settings
from app.utils.text_cleaning import clean_ocr_text

logger = logging.getLogger(__name__)


class OCRService:
    """Service for OCR text extraction from images."""

    def __init__(self, openai_client: Optional[OpenAI] = None):
        """
        Initialize OCR service.

        Args:
            openai_client: OpenAI client instance (creates new one if not provided)
        """
        self.client = openai_client or OpenAI(api_key=settings.openai_api_key)
        self.model = settings.ocr_model

    def extract_text(self, image_path: Path) -> str:
        """
        Extract text from image and return cleaned text.

        Args:
            image_path: Path to the image file

        Returns:
            Extracted and cleaned text

        Raises:
            Exception: If OCR extraction fails
        """
        text, _ = self.extract_with_confidence(image_path)
        return text

    def extract_with_confidence(
        self, image_path: Path, max_retries: int = 3
    ) -> Tuple[str, Optional[float]]:
        """
        Extract text from image with confidence score if available.

        Args:
            image_path: Path to the image file
            max_retries: Maximum number of retry attempts

        Returns:
            Tuple of (extracted_text, confidence_score)

        Raises:
            Exception: If OCR extraction fails after retries
        """
        if not image_path.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")

        start_time = time.time()

        # Read and encode image
        image_data = image_path.read_bytes()
        base64_image = base64.b64encode(image_data).decode("utf-8")

        # Prepare API request
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Extract all text from this image. Preserve formatting and structure.",
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                        },
                    },
                ],
            }
        ]

        # Retry logic with exponential backoff
        last_error = None
        for attempt in range(max_retries):
            try:
                logger.info(f"OCR attempt {attempt + 1}/{max_retries} using model: {self.model}")
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=4096,
                )

                # Extract text from response
                extracted_text = response.choices[0].message.content or ""

                # Clean the extracted text
                cleaned_text = clean_ocr_text(extracted_text)

                # Calculate processing time
                processing_time = (time.time() - start_time) * 1000

                logger.info(f"OCR extraction successful. Text length: {len(cleaned_text)} chars, Time: {processing_time:.2f}ms")

                # Note: OpenAI Vision API doesn't provide confidence scores
                # Return None for confidence
                return cleaned_text, None

            except Exception as e:
                last_error = e
                error_details = str(e)
                
                # Log detailed error information
                logger.error(
                    f"OCR extraction attempt {attempt + 1}/{max_retries} failed",
                    exc_info=True,
                    extra={
                        "model": self.model,
                        "attempt": attempt + 1,
                        "error_type": type(e).__name__,
                        "error_message": error_details,
                    }
                )
                
                # Try to extract more details from OpenAI errors
                if hasattr(e, 'response') and hasattr(e.response, 'json'):
                    try:
                        error_json = e.response.json()
                        logger.error(f"OpenAI API error details: {error_json}")
                        error_details = f"{error_details} - API Response: {error_json}"
                    except Exception:
                        pass
                
                if attempt < max_retries - 1:
                    # Exponential backoff: wait 2^attempt seconds
                    wait_time = 2 ** attempt
                    logger.warning(f"Retrying OCR in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    final_error = Exception(f"OCR extraction failed after {max_retries} attempts: {error_details}")
                    logger.error(f"OCR extraction failed after all retries. Final error: {error_details}", exc_info=True)
                    raise final_error from last_error

        # Should not reach here, but handle just in case
        raise Exception(f"OCR extraction failed: {str(last_error)}") from last_error

