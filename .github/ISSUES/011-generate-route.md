# Issue #11: Generate Route Endpoint Implementation

## Phase
Phase 3: API Layer

## Description
Implement the `/generate` API endpoint that orchestrates the complete workflow: OCR extraction, retrieval, and question generation. This is the main endpoint that combines all services.

## Acceptance Criteria
- [ ] Create `app/routes/generate.py` with FastAPI router
- [ ] Implement `POST /generate` endpoint
- [ ] Accept either image file OR ocr_text in JSON
- [ ] Support optional retrieved_context parameter
- [ ] Orchestrate: OCR → Retrieval → Generation
- [ ] Return `GenerateResponse` with formatted question
- [ ] Handle errors with proper HTTPException
- [ ] Clean up temporary files
- [ ] Integration tests

## Technical Details

### Endpoint Specification
```python
@router.post("/generate", response_model=GenerateResponse)
async def generate_question(
    ocr_text: Optional[str] = None,
    image_file: Optional[UploadFile] = None,
    retrieved_context: Optional[List[str]] = None,
    include_solution: bool = False
):
    """Generate exam question from image or text."""
```

### Request Options
**Option 1 - Image Upload:**
- multipart/form-data with image file
- Automatically performs OCR and retrieval

**Option 2 - Direct Text:**
- JSON with ocr_text and optional retrieved_context
- Skips OCR step

### Response Format
```json
{
  "question": "Formatted exam question...",
  "metadata": {
    "model": "gpt-4",
    "tokens_used": 1234,
    "retrieved_count": 5
  },
  "processing_steps": ["ocr", "retrieval", "generation"]
}
```

### Workflow
1. If image provided: Extract text via OCR service
2. If retrieved_context not provided: Retrieve similar content
3. Generate question using generation service
4. Return formatted response

## Implementation Notes
- Validate that at least one of ocr_text or image_file is provided
- Handle both request formats gracefully
- Track processing steps for response metadata
- Ensure temp file cleanup
- Log full workflow for debugging

## Testing Requirements
- Test with image upload
- Test with direct text input
- Test with pre-provided context
- Test error handling at each step
- Test complete workflow end-to-end

## References
- Design Document: Section 5.1 (API Design - POST /generate), Section 3.1 (Complete Request Flow)
- Implementation Plan: Phase 3, Step 4

