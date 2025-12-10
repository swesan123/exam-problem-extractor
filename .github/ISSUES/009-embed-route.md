# Issue #9: Embed Route Endpoint Implementation

## Phase
Phase 3: API Layer

## Description
Implement the `/embed` API endpoint that accepts text and metadata, generates embeddings, and stores them in the vector database. This endpoint is used to build the knowledge base of exam content.

## Acceptance Criteria
- [ ] Create `app/routes/embed.py` with FastAPI router
- [ ] Implement `POST /embed` endpoint
- [ ] Accept JSON with text and metadata
- [ ] Validate request using `EmbeddingRequest` model
- [ ] Use embedding service to generate and store embeddings
- [ ] Return `EmbeddingResponse` with embedding ID
- [ ] Handle errors with proper HTTPException
- [ ] Integration tests

## Technical Details

### Endpoint Specification
```python
@router.post("/embed", response_model=EmbeddingResponse)
async def create_embedding(request: EmbeddingRequest):
    """Generate and store embedding for text."""
```

### Request Format
```json
{
  "text": "Question text to embed...",
  "metadata": {
    "source": "exam_2023",
    "page": 1,
    "chunk_id": "chunk_001"
  }
}
```

### Response Format
```json
{
  "embedding_id": "emb_abc123",
  "status": "stored",
  "vector_dimension": 1536
}
```

### Error Handling
- 400: Validation error (invalid request)
- 500: Embedding generation or storage failed
- Include detailed error messages

## Implementation Notes
- Use Pydantic model for request validation
- Delegate all business logic to embedding service
- Handle vector DB connection errors
- Log embedding creation for auditing
- Consider batch endpoint for multiple embeddings (future)

## Testing Requirements
- Test with valid requests
- Test with invalid metadata
- Test with empty text
- Test error handling
- Test response format

## References
- Design Document: Section 5.1 (API Design - POST /embed), Section 3.2 (Embedding Flow)
- Implementation Plan: Phase 3, Step 2

