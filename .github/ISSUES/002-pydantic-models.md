# Issue #2: Pydantic Models for All Endpoints

## Phase
Phase 1: Foundation

## Description
Create all Pydantic models for request/response validation across all API endpoints. These models ensure type safety and automatic API documentation generation.

## Acceptance Criteria
- [ ] Create `app/models/ocr_models.py` with:
  - `OCRRequest` (for multipart file upload)
  - `OCRResponse` with text, confidence, processing_time_ms
- [ ] Create `app/models/embedding_models.py` with:
  - `EmbeddingMetadata` (source, page, chunk_id, timestamp)
  - `EmbeddingRequest` (text, metadata)
  - `EmbeddingResponse` (embedding_id, status, vector_dimension)
- [ ] Create `app/models/retrieval_models.py` with:
  - `RetrieveRequest` (query, top_k with validation)
  - `RetrievedChunk` (text, score, metadata, chunk_id)
  - `RetrieveResponse` (results list, query_embedding_dim)
- [ ] Create `app/models/generation_models.py` with:
  - `GenerateRequest` (ocr_text, image_file, retrieved_context, include_solution)
  - `GenerateResponse` (question, metadata, processing_steps)
- [ ] All models use proper type hints
- [ ] All models include field validations where appropriate
- [ ] All models have docstrings

## Technical Details

### Model Specifications

#### OCR Models
```python
class OCRResponse(BaseModel):
    text: str
    confidence: Optional[float] = None
    processing_time_ms: Optional[int] = None
```

#### Embedding Models
```python
class EmbeddingMetadata(BaseModel):
    source: str
    page: Optional[int] = None
    chunk_id: str
    timestamp: Optional[datetime] = None
```

#### Retrieval Models
```python
class RetrieveRequest(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=100)
```

#### Generation Models
```python
class GenerateRequest(BaseModel):
    ocr_text: Optional[str] = None
    image_file: Optional[UploadFile] = None
    retrieved_context: Optional[List[str]] = None
    include_solution: bool = False
```

## Validation Rules
- `top_k` must be between 1 and 100
- `query` and `text` fields must be non-empty strings
- `chunk_id` must be a valid identifier
- At least one of `ocr_text` or `image_file` required in `GenerateRequest`

## Implementation Notes
- Use Pydantic v2 syntax
- Add descriptive field descriptions for OpenAPI docs
- Use `Field()` for validation constraints
- Consider using `constr` for string length validation

## References
- Design Document: Section 4.3 (Model Modules)
- Implementation Plan: Phase 1, Step 4

