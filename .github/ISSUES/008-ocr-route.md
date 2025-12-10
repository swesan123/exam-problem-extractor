# Issue #8: OCR Route Endpoint Implementation

## Phase
Phase 3: API Layer

## Description
Implement the `/ocr` API endpoint that accepts image uploads and returns extracted text. This endpoint handles file validation, delegates to OCR service, and formats responses.

## Acceptance Criteria
- [ ] Create `app/routes/ocr.py` with FastAPI router
- [ ] Implement `POST /ocr` endpoint
- [ ] Accept multipart/form-data with image file
- [ ] Validate file type (PNG, JPG, JPEG) and size (<10MB)
- [ ] Use OCR service to extract text
- [ ] Return `OCRResponse` with text and metadata
- [ ] Handle errors with proper HTTPException
- [ ] Clean up temporary files
- [ ] Integration tests

## Technical Details

### Endpoint Specification
```python
@router.post("/ocr", response_model=OCRResponse)
async def extract_text(file: UploadFile = File(...)):
    """Extract text from uploaded image."""
```

### Request Handling
- Accept `multipart/form-data`
- Validate file using `file_utils.validate_image_file()`
- Save temporary file using `file_utils.save_temp_file()`
- Pass to OCR service

### Response Format
```json
{
  "text": "Extracted text content...",
  "confidence": 0.95,
  "processing_time_ms": 1234
}
```

### Error Handling
- 400: Invalid file type or size
- 413: File too large
- 500: OCR processing failed
- Include meaningful error messages

## Implementation Notes
- Use FastAPI's `File()` and `UploadFile` for file handling
- Use `file_utils` for validation and temp file management
- Ensure temp files are cleaned up (use try/finally)
- Add request logging
- Consider async file operations

## Testing Requirements
- Test with valid image files (PNG, JPG, JPEG)
- Test with invalid file types
- Test with oversized files
- Test error handling
- Test response format

## References
- Design Document: Section 5.1 (API Design - POST /ocr)
- Implementation Plan: Phase 3, Step 1

