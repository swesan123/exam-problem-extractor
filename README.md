# Exam Problem Extractor

A lightweight AI-powered backend service that converts screenshots into clean, exam-style questions using OCR, RAG (Retrieval-Augmented Generation) over past exam data, and OpenAI generation. Capture any problem, extract text automatically, retrieve similar examples, and generate a fully formatted exam-ready question in seconds.

## Features

- **OCR Extraction**: Automatically extract text from uploaded screenshots using OpenAI Vision models
- **Vector Retrieval**: Retrieve similar exam content from past exams using semantic search (ChromaDB/FAISS)
- **Question Generation**: Generate exam-style questions using OpenAI GPT models with retrieved context
- **RESTful API**: Clean FastAPI-based endpoints for all operations
- **Modular Architecture**: Well-organized service layer for easy maintenance and testing

## Tech Stack

- **Python**: 3.10+
- **Web Framework**: FastAPI
- **AI/ML**:
  - OpenAI API (Vision OCR, text embeddings, GPT-4.1/GPT-4.1-mini for generation)
- **Vector Database**: ChromaDB or FAISS
- **Server**: uvicorn or gunicorn
- **Data Validation**: Pydantic models
- **File Handling**: pathlib

## Architecture

The service follows a modular architecture with clear separation of concerns:

```
┌─────────────┐
│   FastAPI   │  ← API Layer (routes/)
└──────┬──────┘
       │
┌──────▼──────┐
│  Services   │  ← Business Logic (services/)
└──────┬──────┘
       │
┌──────▼──────┐
│   OpenAI    │  ← External APIs
│  ChromaDB   │
└─────────────┘
```

### Component Overview

- **Routes** (`/routes`): API endpoint handlers with request/response validation
- **Services** (`/services`): Core business logic for OCR, embeddings, retrieval, and generation
- **Models** (`/models`): Pydantic schemas for request/response validation
- **Utils** (`/utils`): Helper functions for file handling, text cleaning, and chunking
- **Vector Store** (`/vector_store`): Persistent storage for exam embeddings

## API Endpoints

### POST `/ocr`
Extract text from an uploaded image using OpenAI Vision.

**Request**: Multipart form data with image file
**Response**: Extracted text content

### POST `/embed`
Generate embeddings for text chunks and store them in the vector database.

**Request**: Text chunks with metadata (exam source, page number, chunk ID)
**Response**: Confirmation of stored embeddings

### POST `/retrieve`
Retrieve similar exam content from the vector store.

**Request**: Query text, top_k parameter
**Response**: List of similar exam chunks with similarity scores

### POST `/generate`
Generate an exam-style question using OCR text and retrieved examples.

**Request**: OCR text, retrieved context
**Response**: Formatted exam question

All endpoints:
- Use Pydantic models for validation
- Return structured JSON responses
- Handle errors with proper HTTPException
- Include comprehensive error messages

## Project Structure

```
exam-problem-extractor/
├── app/
│   ├── main.py                 # FastAPI application entry point
│   ├── routes/
│   │   ├── ocr.py             # OCR endpoint
│   │   ├── embed.py           # Embedding endpoint
│   │   ├── retrieve.py        # Retrieval endpoint
│   │   └── generate.py        # Generation endpoint
│   ├── services/
│   │   ├── ocr_service.py     # OCR business logic
│   │   ├── embedding_service.py
│   │   ├── retrieval_service.py
│   │   └── generation_service.py
│   ├── models/
│   │   ├── ocr_models.py      # Pydantic schemas
│   │   ├── embedding_models.py
│   │   ├── retrieval_models.py
│   │   └── generation_models.py
│   └── utils/
│       ├── file_utils.py      # File handling utilities
│       ├── text_cleaning.py   # Text preprocessing
│       └── chunking.py        # Text chunking logic
├── vector_store/
│   └── chroma_index/          # ChromaDB index (or faiss_index/)
├── tests/
│   ├── test_ocr.py
│   ├── test_retrieval.py
│   └── test_generate.py
└── README.md
```

## Setup Instructions

### Prerequisites

- Python 3.10 or higher
- pip or poetry for dependency management
- OpenAI API key

### Installation

1. Clone the repository:
```bash
git clone git@github.com:swesan123/exam-problem-extractor.git
cd exam-problem-extractor
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the project root:
```bash
cp .env.example .env
```

5. Configure environment variables (see Environment Variables section below)

## Environment Variables

Create a `.env` file in the project root with the following variables:

```env
# Required
OPENAI_API_KEY=your_openai_api_key_here

# Optional - Vector Store Configuration
VECTOR_DB_PATH=./vector_store/chroma_index
VECTOR_DB_TYPE=chroma  # or 'faiss'

# Optional - Server Configuration
HOST=0.0.0.0
PORT=8000
```

**Important**: Never commit `.env` files or hardcode credentials in the codebase.

## Usage Examples

### Running the Server

```bash
# Development mode with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production mode with gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### API Usage

#### Extract Text from Image (OCR)

```bash
curl -X POST "http://localhost:8000/ocr" \
  -F "file=@screenshot.png"
```

#### Generate Embeddings

```bash
curl -X POST "http://localhost:8000/embed" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Sample exam question text...",
    "metadata": {
      "source": "exam_2023",
      "page": 1,
      "chunk_id": "chunk_001"
    }
  }'
```

#### Retrieve Similar Content

```bash
curl -X POST "http://localhost:8000/retrieve" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "quadratic equations",
    "top_k": 5
  }'
```

#### Generate Exam Question

```bash
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "ocr_text": "Extracted text from image...",
    "retrieved_context": ["Similar exam question 1", "Similar exam question 2"]
  }'
```

## Development

### Code Style

The project follows:
- **Black** for code formatting
- **isort** for import organization
- Type hints throughout
- Early returns to reduce nesting
- Small, focused functions with clear responsibilities

### Running Tests

```bash
pytest tests/
```

### Adding New Features

1. Create feature branch: `git checkout -b feature/your-feature-name`
2. Implement changes following the existing architecture
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit pull request

## Error Handling

All endpoints include comprehensive error handling:
- Input validation using Pydantic models
- File validation for image uploads
- Vector store state validation
- Meaningful error messages with HTTPException
- Logging with traceback for debugging

## Vector Database

The service supports both ChromaDB and FAISS for vector storage:
- **ChromaDB**: Persistent, metadata-rich storage (default)
- **FAISS**: Fast, in-memory similarity search

Ensure the same embedding model is used throughout for consistency. Metadata such as exam source, page number, and chunk ID are stored with each embedding.

## AI Generation

The question generation process:
1. Uses retrieved context to ground the generation (RAG)
2. Formats questions in clean, exam-ready style
3. Avoids hallucinated or fabricated content
4. Never outputs solutions unless explicitly requested

## License

[Add your license here]

## Contributing

[Add contributing guidelines here]

## Support

For issues and questions, please open an issue on GitHub.
