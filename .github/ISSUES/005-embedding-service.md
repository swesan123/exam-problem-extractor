# Issue #5: Embedding Service Implementation

## Phase
Phase 2: Core Services

## Description
Implement the embedding service that generates text embeddings using OpenAI and stores them in the vector database (ChromaDB/FAISS). This service handles embedding generation, vector storage, and metadata management.

## Acceptance Criteria
- [ ] Create `app/services/embedding_service.py` with `EmbeddingService` class
- [ ] Implement `generate_embedding(text: str) -> List[float]`
- [ ] Implement `store_embedding(text: str, embedding: List[float], metadata: dict) -> str`
- [ ] Implement `batch_store(texts: List[str], metadata_list: List[dict]) -> List[str]`
- [ ] Integrate with OpenAI embeddings API
- [ ] Integrate with ChromaDB (default) or FAISS
- [ ] Use `chunking` utilities for large texts
- [ ] Handle vector DB initialization and connection
- [ ] Unit tests with mocked dependencies

## Technical Details

### Service Interface
```python
class EmbeddingService:
    def __init__(self, openai_client: OpenAI, vector_db: VectorDB):
        ...
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding vector for text."""
        
    def store_embedding(self, text: str, embedding: List[float], metadata: dict) -> str:
        """Store embedding in vector DB, return embedding ID."""
        
    def batch_store(self, texts: List[str], metadata_list: List[dict]) -> List[str]:
        """Store multiple embeddings efficiently."""
```

### OpenAI Integration
- Use `text-embedding-ada-002` model (or latest)
- Handle batch requests efficiently
- Respect API rate limits

### Vector DB Integration
- Support ChromaDB (default) and FAISS
- Store metadata alongside embeddings
- Handle collection/index creation
- Ensure same embedding model used throughout

### Chunking Integration
- Automatically chunk large texts before embedding
- Preserve metadata for each chunk
- Generate unique chunk IDs

## Implementation Notes
- Use dependency injection for OpenAI and vector DB clients
- Implement connection pooling for vector DB
- Handle vector DB initialization on first use
- Store embedding model version in metadata
- Consider batch processing for efficiency

## Testing Requirements
- Mock OpenAI embeddings API
- Test with in-memory vector DB (test fixture)
- Test batch operations
- Test chunking integration
- Test metadata storage and retrieval

## References
- Design Document: Section 4.2 (Embedding Service), Section 3.2 (Embedding Flow)
- Implementation Plan: Phase 2, Step 2

