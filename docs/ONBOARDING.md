# Onboarding Guide for New Developers

Welcome to the **exam-problem-extractor** project! This guide will help you get set up and start contributing.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Environment Setup](#environment-setup)
4. [Project Structure](#project-structure)
5. [Key Modules](#key-modules)
6. [Running the Application](#running-the-application)
7. [Development Workflow](#development-workflow)
8. [Testing](#testing)
9. [First Tasks](#first-tasks)
10. [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Software

- **Python 3.10+** (3.11 or 3.12 recommended)
  ```bash
  python3 --version  # Should show 3.10 or higher
  ```

- **Git** (for version control)
  ```bash
  git --version
  ```

- **pip** (Python package manager)
  ```bash
  pip3 --version
  ```

### Optional but Recommended

- **Docker & Docker Compose** (for containerized development)
  ```bash
  docker --version
  docker-compose --version
  ```

- **VS Code** or **PyCharm** (with Python extensions)
- **Postman** or **curl** (for API testing)

## Quick Start

### 1. Clone the Repository

```bash
git clone git@github.com:swesan123/exam-problem-extractor.git
cd exam-problem-extractor
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your OpenAI API key
# Required: OPENAI_API_KEY=sk-your-key-here
```

### 5. Run the Application

```bash
# Development mode with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Environment Setup

### Step-by-Step Setup

#### 1. Python Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # macOS/Linux
# OR
venv\Scripts\activate     # Windows

# Verify activation (you should see (venv) in your prompt)
which python  # Should point to venv/bin/python
```

#### 2. Install Dependencies

```bash
# Upgrade pip first
pip install --upgrade pip

# Install all dependencies
pip install -r requirements.txt

# Verify installation
pip list
```

**Key Dependencies:**
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `openai` - OpenAI API client
- `chromadb` - Vector database
- `pydantic` - Data validation
- `pytest` - Testing framework

#### 3. Environment Variables

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# Required
OPENAI_API_KEY=sk-your-openai-api-key-here

# Optional - Vector Database
VECTOR_DB_PATH=./vector_store/chroma_index
VECTOR_DB_TYPE=chroma

# Optional - Server Configuration
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO

# Optional - Limits
MAX_FILE_SIZE_MB=10
MAX_RETRIEVE_K=100
REQUEST_TIMEOUT_SEC=60

# Optional - OpenAI Models
OCR_MODEL=gpt-4-vision-preview
EMBEDDING_MODEL=text-embedding-ada-002
GENERATION_MODEL=gpt-4
```

**Getting an OpenAI API Key:**
1. Go to https://platform.openai.com/
2. Sign up or log in
3. Navigate to API Keys section
4. Create a new secret key
5. Copy and paste into `.env` file

⚠️ **Important**: Never commit `.env` file to git! It's already in `.gitignore`.

#### 4. Vector Database Setup

The vector database (ChromaDB) will be automatically created on first run. The default location is `./vector_store/chroma_index`.

```bash
# The directory will be created automatically
# No manual setup required!
```

## Project Structure

```
exam-problem-extractor/
├── app/                      # Main application code
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Configuration management
│   ├── exceptions.py        # Custom exceptions
│   ├── middleware.py        # Request middleware
│   ├── models/              # Pydantic models
│   │   ├── ocr_models.py
│   │   ├── embedding_models.py
│   │   ├── retrieval_models.py
│   │   └── generation_models.py
│   ├── routes/              # API endpoints
│   │   ├── ocr.py          # POST /ocr
│   │   ├── embed.py        # POST /embed
│   │   ├── retrieve.py     # POST /retrieve
│   │   └── generate.py     # POST /generate
│   ├── services/            # Business logic
│   │   ├── ocr_service.py
│   │   ├── embedding_service.py
│   │   ├── retrieval_service.py
│   │   └── generation_service.py
│   └── utils/               # Utility functions
│       ├── file_utils.py
│       ├── text_cleaning.py
│       └── chunking.py
├── tests/                    # Test suite
│   ├── conftest.py
│   ├── test_utils.py
│   ├── test_ocr_service.py
│   ├── test_embedding_service.py
│   ├── test_retrieval_service.py
│   ├── test_generation_service.py
│   └── test_routes.py
├── docs/                     # Documentation
│   ├── ONBOARDING.md        # This file
│   ├── CODE_EXPLANATION.md
│   ├── CODE_REVIEW.md
│   └── SECURITY_AUDIT.md
├── vector_store/             # Vector database (auto-created)
├── .env                      # Environment variables (create from .env.example)
├── .env.example              # Example environment file
├── .gitignore
├── requirements.txt          # Python dependencies
├── Dockerfile                # Docker configuration
├── docker-compose.yml        # Docker Compose setup
├── README.md                 # Project overview
└── DESIGN.md                 # Technical design document
```

## Key Modules

### 1. Configuration (`app/config.py`)

Manages all application settings using `pydantic-settings`. Loads from environment variables.

**Key Settings:**
- `openai_api_key`: Required OpenAI API key
- `vector_db_path`: Path to ChromaDB storage
- `ocr_model`: OpenAI Vision model for OCR
- `generation_model`: GPT model for question generation

### 2. Services (`app/services/`)

**OCR Service** (`ocr_service.py`):
- Extracts text from images using OpenAI Vision
- Handles retry logic with exponential backoff
- Cleans extracted text

**Embedding Service** (`embedding_service.py`):
- Generates text embeddings using OpenAI
- Stores embeddings in ChromaDB
- Handles batch operations and chunking

**Retrieval Service** (`retrieval_service.py`):
- Performs semantic search over vector database
- Returns ranked results with similarity scores

**Generation Service** (`generation_service.py`):
- Generates exam-style questions using GPT-4
- Supports question-only or question+solution modes

### 3. Routes (`app/routes/`)

API endpoints that handle HTTP requests:

- `POST /ocr` - Extract text from image
- `POST /embed` - Generate and store embeddings
- `POST /retrieve` - Search for similar content
- `POST /generate` - Full pipeline (OCR → Retrieval → Generation)
- `GET /health` - Health check endpoint
- `GET /` - Root endpoint

### 4. Models (`app/models/`)

Pydantic models for request/response validation:
- Type-safe data structures
- Automatic API documentation
- Input validation

### 5. Utils (`app/utils/`)

Utility functions:
- **file_utils.py**: File upload handling, validation
- **text_cleaning.py**: OCR text cleaning and normalization
- **chunking.py**: Text chunking strategies

## Running the Application

### Development Mode (Recommended)

```bash
# Activate virtual environment
source venv/bin/activate

# Run with auto-reload (restarts on code changes)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Features:**
- Auto-reload on code changes
- Detailed error messages
- Interactive API docs at `/docs`

### Production Mode

```bash
# Using uvicorn directly
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# Using gunicorn (recommended for production)
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Docker (Alternative)

```bash
# Build and run with Docker Compose
docker-compose up --build

# Or build manually
docker build -t exam-problem-extractor .
docker run -p 8000:8000 --env-file .env exam-problem-extractor
```

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes

- Write code following existing patterns
- Add type hints
- Write docstrings
- Follow PEP 8 style guide

### 3. Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_ocr_service.py

# Run with verbose output
pytest -v
```

### 4. Check Code Quality

```bash
# Format code (if black is installed)
black app/ tests/

# Sort imports (if isort is installed)
isort app/ tests/

# Type checking (if mypy is installed)
mypy app/
```

### 5. Commit Changes

```bash
git add .
git commit -m "feat: Add new feature description"
```

**Commit Message Format:**
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation
- `test:` - Tests
- `refactor:` - Code refactoring
- `chore:` - Maintenance tasks

### 6. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub.

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_ocr_service.py

# Run specific test
pytest tests/test_ocr_service.py::test_extract_text_success

# Run with coverage report
pytest --cov=app --cov-report=term-missing
```

### Test Structure

- **Unit Tests**: Test individual functions/classes in isolation
- **Integration Tests**: Test API endpoints end-to-end
- **Fixtures**: Reusable test data (in `conftest.py`)

### Writing Tests

```python
# Example test structure
def test_feature_name():
    """Test description."""
    # Arrange
    service = SomeService()
    
    # Act
    result = service.do_something()
    
    # Assert
    assert result == expected_value
```

## First Tasks

### Good First Issues

1. **Add More Test Coverage**
   - Find untested code paths
   - Add edge case tests
   - Improve test fixtures

2. **Improve Error Messages**
   - Make error messages more user-friendly
   - Add error codes
   - Improve error documentation

3. **Add Logging**
   - Add structured logging to services
   - Improve log messages
   - Add request/response logging

4. **Documentation**
   - Improve docstrings
   - Add code examples
   - Update API documentation

5. **Code Quality**
   - Refactor complex functions
   - Improve type hints
   - Add missing validations

### Example: Adding a New Endpoint

1. **Create Pydantic Models** (`app/models/`)
   ```python
   class NewRequest(BaseModel):
       field: str
   ```

2. **Create Service** (`app/services/`)
   ```python
   class NewService:
       def process(self, data: str) -> str:
           # Implementation
   ```

3. **Create Route** (`app/routes/`)
   ```python
   @router.post("/new-endpoint")
   async def new_endpoint(request: NewRequest):
       service = NewService()
       result = service.process(request.field)
       return {"result": result}
   ```

4. **Register Route** (`app/main.py`)
   ```python
   app.include_router(new_router)
   ```

5. **Write Tests** (`tests/`)
   ```python
   def test_new_endpoint():
       response = client.post("/new-endpoint", json={"field": "value"})
       assert response.status_code == 200
   ```

## Troubleshooting

### Common Issues

#### 1. Import Errors

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

#### 2. OpenAI API Errors

```
Error: Invalid API key
```

**Solution:**
- Check `.env` file exists
- Verify `OPENAI_API_KEY` is set correctly
- Ensure API key is valid and has credits

#### 3. Port Already in Use

```
Error: Address already in use
```

**Solution:**
```bash
# Find process using port 8000
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill the process or use different port
uvicorn app.main:app --port 8001
```

#### 4. ChromaDB Errors

```
Error: Permission denied
```

**Solution:**
```bash
# Check vector_store directory permissions
chmod -R 755 vector_store/

# Or delete and recreate
rm -rf vector_store/
# Will be recreated on next run
```

#### 5. Module Not Found

```
ModuleNotFoundError: No module named 'app'
```

**Solution:**
```bash
# Make sure you're in project root
cd /path/to/exam-problem-extractor

# Install in development mode
pip install -e .
```

### Getting Help

1. **Check Documentation**
   - `README.md` - Project overview
   - `DESIGN.md` - Technical design
   - `docs/CODE_EXPLANATION.md` - Code walkthrough

2. **Check Issues**
   - GitHub Issues for known problems
   - Search existing issues before creating new ones

3. **Ask Questions**
   - Create a GitHub Discussion
   - Tag maintainers in issues

## Next Steps

1. ✅ Complete environment setup
2. ✅ Run the application successfully
3. ✅ Explore the API at http://localhost:8000/docs
4. ✅ Run the test suite
5. ✅ Read the codebase (start with `app/main.py`)
6. ✅ Pick a first task from the list above
7. ✅ Make your first contribution!

## Additional Resources

- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **OpenAI API Docs**: https://platform.openai.com/docs
- **ChromaDB Docs**: https://docs.trychroma.com/
- **Pydantic Docs**: https://docs.pydantic.dev/
- **Pytest Docs**: https://docs.pytest.org/

## Questions?

If you have questions or need help:
1. Check the documentation in `docs/`
2. Review existing code examples
3. Create a GitHub Issue or Discussion
4. Reach out to the maintainers

Welcome to the team! 🚀

