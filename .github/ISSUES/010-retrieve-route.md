# Issue #10: Retrieve Route Endpoint Implementation

## Phase
Phase 3: API Layer

## Description
Implement the `/retrieve` API endpoint that accepts a query string and returns similar exam content from the vector database. This endpoint performs semantic search over stored embeddings.

## Acceptance Criteria
- [ ] Create `app/routes/retrieve.py` with FastAPI router
- [ ] Implement `POST /retrieve` endpoint
- [ ] Accept JSON with query and top_k
- [ ] Validate request using `RetrieveRequest` model
- [ ] Use retrieval service to find similar content
- [ ] Return `RetrieveResponse` with ranked results
- [ ] Handle errors with proper HTTPException
- [ ] Integration tests

## Technical Details

### Endpoint Specification
```python
@router.post("/retrieve", response_model=RetrieveResponse)
async def retrieve_similar(request: RetrieveRequest):
    """Retrieve similar exam content."""
```

### Request Format
```json
{
  "query": "quadratic equations",
  "top_k": 5
}
```

### Response Format
```json
{
  "results": [
    {
      "text": "Similar exam question...",
      "score": 0.87,
      "metadata": {...},
      "chunk_id": "chunk_001"
    }
  ],
  "query_embedding_dim": 1536
}
```

### Error Handling
- 400: Validation error (invalid query or top_k)
- 500: Retrieval failed
- Handle empty vector DB gracefully

## Implementation Notes
- Validate top_k is between 1 and 100
- Delegate to retrieval service
- Handle empty results (return empty list, not error)
- Log query performance
- Consider caching frequent queries (future)

## Testing Requirements
- Test with valid queries
- Test with various top_k values
- Test with empty vector DB
- Test with no matching results
- Test error handling

## References
- Design Document: Section 5.1 (API Design - POST /retrieve)
- Implementation Plan: Phase 3, Step 3

