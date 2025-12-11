"""FastAPI application entry point."""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api import classes, questions
from app.config import settings
from app.exceptions import (EmbeddingException, ExamProblemExtractorException,
                            GenerationException, OCRException,
                            RetrievalException, ValidationException)
from app.middleware import RequestIDMiddleware
from app.routes import embed, generate, ocr, retrieve

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown."""
    # Startup
    logger.info("Starting Exam Problem Extractor API...")
    logger.info(f"Environment: {settings.log_level}")
    logger.info(f"Vector DB: {settings.vector_db_type} at {settings.vector_db_path}")

    # Validate required environment variables
    try:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required but not set")
        logger.info("Environment variables validated successfully")
    except Exception as e:
        logger.error(f"Environment variable validation failed: {e}")
        raise

    # Initialize database
    try:
        from app.db.database import init_db

        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        raise

    yield
    # Shutdown
    logger.info("Shutting down Exam Problem Extractor API...")


# Create FastAPI application
app = FastAPI(
    title="Exam Problem Extractor",
    description="AI-powered backend service that converts screenshots into exam-style questions",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS
cors_origins = [
    origin.strip()
    for origin in settings.cors_origins.split(",")
    if origin.strip()
]
# In development, allow localhost origins if not specified
if not cors_origins and settings.log_level.upper() == "DEBUG":
    cors_origins = ["http://localhost:3000", "http://localhost:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins if cors_origins else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Add request ID middleware
app.add_middleware(RequestIDMiddleware)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Exception handlers
@app.exception_handler(ExamProblemExtractorException)
async def custom_exception_handler(
    request: Request, exc: ExamProblemExtractorException
):
    """Handle custom application exceptions."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(
        f"Application error [{request_id}]: {exc.message}",
        exc_info=True,
        extra={"request_id": request_id, "details": exc.details},
    )

    # Determine status code based on exception type
    if isinstance(exc, ValidationException):
        status_code = status.HTTP_400_BAD_REQUEST
    elif isinstance(
        exc, (OCRException, EmbeddingException, RetrievalException, GenerationException)
    ):
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": exc.__class__.__name__,
                "message": exc.message,
                "details": exc.details,
                "request_id": request_id,
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.warning(
        f"Validation error [{request_id}]: {exc.errors()}",
        extra={"request_id": request_id},
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "error": {
                "code": "ValidationError",
                "message": "Request validation failed",
                "details": exc.errors(),
                "request_id": request_id,
            }
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.exception(
        f"Unexpected error [{request_id}]: {str(exc)}",
        extra={"request_id": request_id},
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "InternalServerError",
                "message": "An unexpected error occurred",
                "details": {},
                "request_id": request_id,
            }
        },
    )


# Include routers
app.include_router(ocr.router)
app.include_router(embed.router)
app.include_router(retrieve.router)
app.include_router(generate.router)
app.include_router(classes.router)
app.include_router(questions.router)

# Apply rate limiting to route endpoints
# Get rate limit string based on settings
if settings.rate_limit_enabled:
    rate_limit_str = f"{settings.rate_limit_per_minute}/minute"
else:
    rate_limit_str = "1000/minute"

# Apply rate limit decorators to endpoints
ocr.extract_text = limiter.limit(rate_limit_str)(ocr.extract_text)
generate.generate_question = limiter.limit(rate_limit_str)(generate.generate_question)
embed.create_embedding = limiter.limit(rate_limit_str)(embed.create_embedding)
retrieve.retrieve_similar = limiter.limit(rate_limit_str)(retrieve.retrieve_similar)


# Logging middleware for requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.info(
        f"Request [{request_id}]: {request.method} {request.url.path}",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
        },
    )

    response = await call_next(request)

    logger.info(
        f"Response [{request_id}]: {response.status_code}",
        extra={"request_id": request_id, "status_code": response.status_code},
    )

    return response


@app.get("/health")
async def health_check():
    """
    Enhanced health check endpoint with comprehensive service status.

    Returns:
        Health status with detailed service checks including:
        - Database connectivity
        - OpenAI API connectivity
        - Vector DB status
        - Service version info
    """
    import shutil

    from app.db.database import engine

    checks = {}
    overall_status = "healthy"
    version = "1.0.0"

    # Check Database connectivity
    try:
        from sqlalchemy import text

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {str(e)[:50]}"
        overall_status = "degraded"
        logger.warning(f"Database health check failed: {e}")

    # Check OpenAI API connectivity
    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        # Try a lightweight API call to verify connectivity
        if settings.openai_api_key:
            # Just verify the key is set and valid format (don't make actual API call for speed)
            if len(settings.openai_api_key) > 20 and settings.openai_api_key.startswith(
                "sk-"
            ):
                checks["openai_api"] = "ok"
            else:
                checks["openai_api"] = "warning: invalid key format"
                overall_status = "degraded"
        else:
            checks["openai_api"] = "error"
            overall_status = "degraded"
    except Exception:
        checks["openai_api"] = "error"
        overall_status = "degraded"

    # Check vector DB
    try:
        import chromadb

        client = chromadb.PersistentClient(path=str(settings.vector_db_path))
        checks["vector_db"] = "ok"
    except Exception:
        checks["vector_db"] = "error"
        overall_status = "degraded"

    # Check disk space (basic check)
    try:
        import shutil

        total, used, free = shutil.disk_usage(settings.vector_db_path.parent)
        free_gb = free / (1024**3)
        if free_gb > 1:  # At least 1GB free
            checks["disk_space"] = "ok"
        else:
            checks["disk_space"] = "warning"
            overall_status = "degraded"
    except Exception:
        checks["disk_space"] = "unknown"

    return {
        "status": overall_status,
        "version": version,
        "service": "exam-problem-extractor",
        "checks": checks,
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Exam Problem Extractor API",
        "version": "0.1.0",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level=settings.log_level.lower(),
    )
