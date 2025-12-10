# Code Explanation

## Overview

The **exam-problem-extractor** is a FastAPI-based backend service that converts screenshots into exam-style questions using OCR, vector retrieval, and AI generation. This document explains how the codebase works.

## Architecture

### High-Level Flow

```
User Uploads Image
    ↓
OCR Service (OpenAI Vision) → Extract Text
    ↓
Text Cleaning → Remove Artifacts
    ↓
Retrieval Service → Find Similar Exam Questions (Vector Search)
    ↓
Generation Service (GPT-4) → Create Formatted Question
    ↓
Return Response
```

### Component Layers

1. **API Layer** (`app/routes/`) - HTTP endpoints
2. **Service Layer** (`app/services/`) - Business logic
3. **Data Layer** (`app/models/`) - Pydantic schemas
4. **Utility Layer** (`app/utils/`) - Helper functions

## Core Components

### 1. Configuration (`app/config.py`)

**Purpose**: Centralized configuration management using `pydantic-settings`.

**How it works**:
- Loads environment variables from `.env` file
- Validates required fields (e.g., `OPENAI_API_KEY`)
- Provides type-safe access to settings
- Creates default paths for vector database

**Key Settings**:
- `openai_api_key`: Required API key for OpenAI services
- `vector_db_path`: Where ChromaDB stores embeddings
- `ocr_model`: Which OpenAI Vision model to use
- `generation_model`: Which GPT model for question generation

### 2. OCR Service (`app/services/ocr_service.py`)

**Purpose**: Extract text from images using OpenAI Vision API.

**How it works**:
1. Accepts image file path
2. Reads and base64-encodes the image
3. Sends to OpenAI Vision API with prompt
4. Receives extracted text
5. Cleans text using `text_cleaning` utilities
6. Returns cleaned text

**Key Methods**:
- `extract_text()`: Simple text extraction
- `extract_with_confidence()`: Text extraction with retry logic

**Retry Logic**:
- Exponential backoff: waits 2^attempt seconds between retries
- Default: 3 attempts
- Handles transient API failures

**Example Flow**:
```python
service = OCRService()
text = service.extract_text(image_path)
# Returns: "Find the derivative of f(x) = x^2 + 3x"
```

### 3. Embedding Service (`app/services/embedding_service.py`)

**Purpose**: Generate and store text embeddings in ChromaDB vector database.

**How it works**:
1. Takes text input
2. Sends to OpenAI Embeddings API
3. Receives embedding vector (1536 dimensions for ada-002)
4. Stores in ChromaDB with metadata
5. Returns embedding ID

**Key Methods**:
- `generate_embedding()`: Create embedding for single text
- `store_embedding()`: Save embedding to vector DB
- `batch_store()`: Process multiple texts efficiently
- `store_text_with_chunking()`: Automatically chunk large texts

**Chunking Strategy**:
- Large texts are split into chunks (max 1000 chars)
- Each chunk gets its own embedding
- Preserves sentence boundaries when possible
- Overlaps chunks to maintain context

**Example Flow**:
```python
service = EmbeddingService()
embedding = service.generate_embedding("Sample exam question")
chunk_id = service.store_embedding("Sample exam question", embedding, metadata)
```

### 4. Retrieval Service (`app/services/retrieval_service.py`)

**Purpose**: Find similar exam questions using semantic search.

**How it works**:
1. Takes query text
2. Generates embedding for query
3. Searches ChromaDB for similar embeddings
4. Converts distances to similarity scores
5. Returns ranked results

**Key Methods**:
- `retrieve()`: Get similar chunks
- `retrieve_with_scores()`: Get chunks with similarity scores

**Score Calculation**:
- ChromaDB returns cosine distances (lower = more similar)
- Converts to similarity: `score = 1 - distance`
- Normalizes to 0-1 range
- Sorts by score (descending)

**Example Flow**:
```python
retrieval_service = RetrievalService(embedding_service)
results = retrieval_service.retrieve("derivative problem", top_k=5)
# Returns: List of RetrievedChunk objects with similar exam questions
```

### 5. Generation Service (`app/services/generation_service.py`)

**Purpose**: Generate formatted exam questions using GPT-4.

**How it works**:
1. Takes OCR text and retrieved context
2. Builds system and user prompts
3. Sends to GPT-4 API
4. Parses response
5. Returns formatted question

**Key Methods**:
- `generate_question()`: Simple question generation
- `generate_with_metadata()`: Question with metadata (tokens, model, etc.)
- `generate_with_solution()`: Question with solution included

**Prompt Engineering**:
- System prompt: Defines role and guidelines
- User prompt: Includes OCR text + retrieved examples
- Temperature: 0.7 (balanced creativity/consistency)
- Max tokens: 2048 (question) or 4096 (with solution)

**Example Flow**:
```python
service = GenerationService()
question = service.generate_question(
    ocr_text="Find derivative of x^2",
    retrieved_context=["Similar problem 1", "Similar problem 2"]
)
# Returns: "Find the derivative of the function f(x) = x^2..."
```

### 6. API Routes (`app/routes/`)

#### `/ocr` Endpoint
- **Input**: Image file (PNG, JPG, JPEG)
- **Process**: OCR extraction
- **Output**: Extracted text, confidence, processing time

#### `/embed` Endpoint
- **Input**: Text + metadata
- **Process**: Generate embedding, store in vector DB
- **Output**: Embedding ID, status, vector dimension

#### `/retrieve` Endpoint
- **Input**: Query text + top_k
- **Process**: Semantic search
- **Output**: List of similar chunks with scores

#### `/generate` Endpoint
- **Input**: Image OR text + optional context
- **Process**: OCR → Retrieval → Generation
- **Output**: Formatted question + metadata

## Utility Functions

### Text Cleaning (`app/utils/text_cleaning.py`)

**Purpose**: Clean OCR output to remove artifacts.

**Functions**:
- `clean_ocr_text()`: Main cleaning function
- `remove_artifacts()`: Remove control characters, excessive punctuation
- `normalize_whitespace()`: Normalize spaces and newlines
- `extract_math_expressions()`: Extract mathematical formulas

**Example**:
```python
dirty = "Hello   world\n\n\nTest"
clean = clean_ocr_text(dirty)
# Returns: "Hello world\n\nTest"
```

### Chunking (`app/utils/chunking.py`)

**Purpose**: Split large texts into manageable chunks.

**Functions**:
- `chunk_text()`: Character-based chunking with overlap
- `chunk_by_sentences()`: Preserve sentence boundaries
- `smart_chunk()`: Intelligent chunking (paragraphs → sentences → characters)

**Example**:
```python
text = "Long text..." * 100
chunks = smart_chunk(text, max_size=1000)
# Returns: List of chunks, each ≤ 1000 chars
```

### File Utils (`app/utils/file_utils.py`)

**Purpose**: Handle file uploads and validation.

**Functions**:
- `validate_image_file()`: Check MIME type
- `save_temp_file()`: Save uploaded file temporarily
- `cleanup_temp_file()`: Delete temporary file
- `get_file_size_mb()`: Get file size

**Security**:
- Validates MIME type (not just extension)
- Enforces 10MB size limit
- Cleans up files after processing

## Data Flow Examples

### Example 1: Full Pipeline (Image → Question)

```
1. User uploads image to /generate
   ↓
2. Route validates file (type, size)
   ↓
3. OCR Service extracts text
   "Find the derivative of f(x) = x^2"
   ↓
4. Text Cleaning removes artifacts
   ↓
5. Retrieval Service finds similar problems
   ["Derivative of x^3", "Integration problem", ...]
   ↓
6. Generation Service creates question
   "Question: Find the derivative of the function f(x) = x^2..."
   ↓
7. Response returned to user
```

### Example 2: Embedding Pipeline

```
1. Admin uploads exam questions to /embed
   ↓
2. Text is chunked (if large)
   ↓
3. Each chunk gets embedded (OpenAI)
   [0.123, -0.456, ..., 0.789] (1536 dimensions)
   ↓
4. Embeddings stored in ChromaDB
   - ID: "chunk_001"
   - Text: "Original question text"
   - Metadata: {source: "exam_2023", page: 1}
   ↓
5. Vector database ready for retrieval
```

## Error Handling

### Exception Hierarchy

```
ExamProblemExtractorException (base)
├── ValidationException (400)
├── OCRException (500)
├── EmbeddingException (500)
├── RetrievalException (500)
└── GenerationException (500)
```

### Error Flow

1. **Service Layer**: Catches exceptions, wraps in custom exceptions
2. **Route Layer**: Catches exceptions, converts to HTTPException
3. **Middleware**: Logs errors with request ID
4. **Exception Handler**: Returns structured JSON error response

### Example Error Response

```json
{
  "error": {
    "code": "OCRException",
    "message": "OCR extraction failed after 3 attempts",
    "details": {},
    "request_id": "abc-123-def"
  }
}
```

## Testing Strategy

### Unit Tests
- **Services**: Mock external APIs (OpenAI, ChromaDB)
- **Utils**: Test pure functions with various inputs
- **Models**: Test Pydantic validation

### Integration Tests
- **Routes**: Use FastAPI TestClient
- **End-to-end**: Test full pipeline with mocked dependencies
- **Error paths**: Test validation, error handling

### Test Structure

```
tests/
├── conftest.py          # Shared fixtures
├── test_utils.py        # Utility function tests
├── test_ocr_service.py  # OCR service tests
├── test_embedding_service.py
├── test_retrieval_service.py
├── test_generation_service.py
└── test_routes.py       # API endpoint tests
```

## Key Design Decisions

### 1. Why FastAPI?
- Async support for I/O-bound operations
- Automatic API documentation
- Type validation with Pydantic
- Modern Python features

### 2. Why ChromaDB?
- Easy to use Python API
- Persistent storage
- Good performance for small-medium datasets
- Supports metadata filtering

### 3. Why OpenAI?
- High-quality OCR (Vision API)
- Excellent embeddings (ada-002)
- Powerful generation (GPT-4)
- Single vendor simplifies integration

### 4. Why Separate Services?
- Single Responsibility Principle
- Easy to test (mock dependencies)
- Easy to swap implementations
- Clear separation of concerns

## Performance Considerations

### Bottlenecks
1. **OpenAI API calls**: Network latency (mitigated with retries)
2. **Vector search**: ChromaDB queries (acceptable for current scale)
3. **File I/O**: Temporary file operations (minimal impact)

### Optimizations
- Batch embedding operations
- Async/await for concurrent operations
- Caching (future: cache frequent queries)
- Connection pooling (OpenAI client)

## Security Considerations

### Current Protections
- ✅ Input validation (Pydantic)
- ✅ File type validation
- ✅ File size limits
- ✅ Temporary file cleanup
- ✅ No code injection risks

### Missing (Production Needs)
- ❌ Authentication/Authorization
- ❌ Rate limiting
- ❌ HTTPS enforcement
- ❌ CORS restrictions

## Future Enhancements

1. **Authentication**: API keys or OAuth2
2. **Rate Limiting**: Per-user/IP limits
3. **Caching**: Redis for frequent queries
4. **Batch Processing**: Process multiple images
5. **Webhooks**: Async processing with callbacks
6. **Multi-language**: Support multiple languages

## Conclusion

The codebase follows clean architecture principles with clear separation of concerns. Each component has a single responsibility, making it easy to understand, test, and maintain. The flow from image upload to question generation is straightforward, with each step building on the previous one.

