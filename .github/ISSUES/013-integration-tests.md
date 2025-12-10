# Issue #13: Integration Tests for Routes

## Phase
Phase 4: Testing & Polish

## Description
Create integration tests for all API endpoints. Tests should verify end-to-end functionality including request validation, service integration, and response formatting.

## Acceptance Criteria
- [ ] Create `tests/test_routes.py` or separate test files per route
- [ ] Test `POST /ocr` endpoint:
  - Valid image upload
  - Invalid file types
  - File size limits
  - Response format
- [ ] Test `POST /embed` endpoint:
  - Valid embedding creation
  - Invalid metadata
  - Response format
- [ ] Test `POST /retrieve` endpoint:
  - Valid queries
  - Various top_k values
  - Empty results handling
- [ ] Test `POST /generate` endpoint:
  - Image upload workflow
  - Direct text workflow
  - Complete end-to-end flow
- [ ] Test error responses (400, 500, etc.)
- [ ] Use test client (FastAPI TestClient)
- [ ] Use test vector DB (in-memory or test instance)

## Technical Details

### Testing Setup
- Use FastAPI's `TestClient` for API testing
- Use test database/vector store (separate from production)
- Use test fixtures for sample data
- Clean up after each test

### Test Structure
```python
def test_ocr_endpoint_success(client, sample_image):
    response = client.post("/ocr", files={"file": sample_image})
    assert response.status_code == 200
    assert "text" in response.json()
```

### Test Data
- Sample images in `tests/fixtures/`
- Sample exam text in `tests/fixtures/`
- Pre-populated test vector DB

## Implementation Notes
- Use pytest fixtures for test client setup
- Use test database that's isolated from production
- Test both success and error paths
- Verify response schemas match Pydantic models
- Test authentication/authorization if added (future)

## Coverage Goals
- Routes: 80%+ coverage
- Focus on request/response handling
- Test error paths thoroughly

## References
- Design Document: Section 9 (Testing Strategy)
- Implementation Plan: Phase 4, Step 2

