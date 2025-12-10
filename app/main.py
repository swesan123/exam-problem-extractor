"""FastAPI application entry point."""
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.exceptions import (
    EmbeddingException,
    ExamProblemExtractorException,
    GenerationException,
    OCRException,
    RetrievalException,
    ValidationException,
)
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
    
    # Initialize database
    try:
        from app.db.database import init_db
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
    
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request ID middleware
app.add_middleware(RequestIDMiddleware)


# Exception handlers
@app.exception_handler(ExamProblemExtractorException)
async def custom_exception_handler(request: Request, exc: ExamProblemExtractorException):
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
    elif isinstance(exc, (OCRException, EmbeddingException, RetrievalException, GenerationException)):
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
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
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


# Logging middleware for requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.info(
        f"Request [{request_id}]: {request.method} {request.url.path}",
        extra={"request_id": request_id, "method": request.method, "path": request.url.path},
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
    Health check endpoint with service status.

    Returns:
        Health status with service checks
    """
    checks = {}
    overall_status = "healthy"

    # Check OpenAI API connectivity
    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key)
        # Simple check - just verify API key is set
        if settings.openai_api_key:
            checks["openai_api"] = "ok"
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
        "version": "0.1.0",
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

