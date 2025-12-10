# Issue #6: Retrieval Service Implementation

## Phase
Phase 2: Core Services

## Description
Implement the retrieval service that performs semantic search over the vector database. This service generates query embeddings and retrieves similar exam content with similarity scores.

## Acceptance Criteria
- [ ] Create `app/services/retrieval_service.py` with `RetrievalService` class
- [ ] Implement `retrieve(query: str, top_k: int) -> List[RetrievedChunk]`
- [ ] Implement `retrieve_with_scores(query: str, top_k: int) -> List[RetrievedChunk]`
- [ ] Generate query embeddings using OpenAI
- [ ] Perform similarity search in vector DB
- [ ] Return results sorted by similarity score
- [ ] Include metadata with each result
- [ ] Handle empty vector DB gracefully
- [ ] Unit tests with mocked dependencies

## Technical Details

### Service Interface
```python
class RetrievalService:
    def __init__(self, openai_client: OpenAI, vector_db: VectorDB, embedding_service: EmbeddingService):
        ...
    
    def retrieve(self, query: str, top_k: int) -> List[RetrievedChunk]:
        """Retrieve top_k similar chunks, return without scores."""
        
    def retrieve_with_scores(self, query: str, top_k: int) -> List[RetrievedChunk]:
        """Retrieve top_k similar chunks with similarity scores."""
```

### Query Processing
- Generate embedding for query text
- Use same embedding model as stored embeddings
- Handle empty or very short queries

### Vector Search
- Perform similarity search (cosine similarity)
- Return top_k results sorted by score
- Include full metadata for each result
- Handle cases where vector DB is empty

### Result Format
- Each result includes: text, score, metadata, chunk_id
- Scores normalized (0.0 to 1.0)
- Results sorted descending by score

## Implementation Notes
- Reuse embedding service for query embedding generation
- Validate top_k parameter (1-100)
- Handle edge cases (no results, empty query)
- Consider filtering by metadata (optional enhancement)
- Log retrieval performance metrics

## Testing Requirements
- Mock OpenAI embeddings API
- Test with test vector DB containing sample data
- Test with various query types
- Test edge cases (empty DB, no matches)
- Test score calculation and sorting

## References
- Design Document: Section 4.2 (Retrieval Service), Section 3.1 (Data Flow)
- Implementation Plan: Phase 2, Step 3

