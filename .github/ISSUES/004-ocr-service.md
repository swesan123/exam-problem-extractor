# Issue #4: OCR Service Implementation

## Phase
Phase 2: Core Services

## Description
Implement the OCR service that extracts text from images using OpenAI Vision API. This service handles image processing, API calls, and text post-processing.

## Acceptance Criteria
- [ ] Create `app/services/ocr_service.py` with `OCRService` class
- [ ] Implement `extract_text(image_path: Path) -> str`
- [ ] Implement `extract_with_confidence(image_path: Path) -> tuple[str, float]`
- [ ] Integrate with OpenAI Vision API
- [ ] Use `text_cleaning` utilities for post-processing
- [ ] Handle API errors gracefully with retry logic
- [ ] Add proper logging for debugging
- [ ] Unit tests with mocked OpenAI API

## Technical Details

### Service Interface
```python
class OCRService:
    def __init__(self, openai_client: OpenAI, text_cleaner: TextCleaningUtils):
        ...
    
    def extract_text(self, image_path: Path) -> str:
        """Extract text from image, return cleaned text."""
        
    def extract_with_confidence(self, image_path: Path) -> tuple[str, float]:
        """Extract text with confidence score if available."""
```

### OpenAI Integration
- Use `gpt-4-vision-preview` model (or latest vision model)
- Send image as base64 encoded or file path
- Configure appropriate max_tokens for response
- Handle rate limiting and retries

### Error Handling
- Handle invalid image format errors
- Handle OpenAI API errors (rate limits, timeouts)
- Handle network errors with retry logic
- Return meaningful error messages

### Dependencies
- OpenAI client (injected via constructor)
- `utils/text_cleaning.py` for post-processing
- `utils/file_utils.py` for file validation

## Implementation Notes
- Use dependency injection for OpenAI client
- Implement exponential backoff for retries
- Log processing time for monitoring
- Consider caching results for same image (optional)
- Handle large images (may need resizing)

## Testing Requirements
- Mock OpenAI API responses
- Test with various image formats
- Test error handling (API failures, invalid images)
- Test text cleaning integration
- Test confidence score extraction

## References
- Design Document: Section 4.2 (OCR Service), Section 3.1 (Data Flow)
- Implementation Plan: Phase 2, Step 1

