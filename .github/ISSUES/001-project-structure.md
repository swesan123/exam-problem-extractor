# Issue #1: Project Structure and Configuration Setup

## Phase
Phase 1: Foundation

## Description
Set up the complete project directory structure, base FastAPI application, environment configuration, and dependency management according to the design document.

## Acceptance Criteria
- [ ] Create complete directory structure:
  - `app/` with subdirectories: `routes/`, `services/`, `models/`, `utils/`
  - `vector_store/` directory
  - `tests/` directory
- [ ] Create `app/main.py` with base FastAPI app
- [ ] Add health check endpoint (`/health`)
- [ ] Create `requirements.txt` with all dependencies
- [ ] Create `.env.example` with all required environment variables
- [ ] Create `.gitignore` to exclude sensitive files
- [ ] Set up configuration management using `pydantic-settings`
- [ ] Add `__init__.py` files to make packages importable

## Technical Details

### Directory Structure
```
app/
├── __init__.py
├── main.py
├── routes/
│   └── __init__.py
├── services/
│   └── __init__.py
├── models/
│   └── __init__.py
└── utils/
    └── __init__.py
vector_store/
tests/
├── __init__.py
└── conftest.py
```

### Dependencies
- fastapi>=0.104.0
- uvicorn[standard]>=0.24.0
- python-multipart>=0.0.6
- openai>=1.3.0
- chromadb>=0.4.0
- pydantic>=2.0.0
- pydantic-settings>=2.0.0
- python-dotenv>=1.0.0

### Environment Variables
- `OPENAI_API_KEY` (required)
- `VECTOR_DB_PATH` (optional, default: `./vector_store/chroma_index`)
- `VECTOR_DB_TYPE` (optional, default: `chroma`)
- `HOST` (optional, default: `0.0.0.0`)
- `PORT` (optional, default: `8000`)

## Implementation Notes
- Use `pydantic-settings` for type-safe configuration
- Validate required environment variables on startup
- Fail fast if `OPENAI_API_KEY` is missing
- Health check should return 200 OK with basic status

## References
- Design Document: Section 2 (Architecture), Section 11 (Configuration Management)
- Implementation Plan: Phase 1, Step 1-3

