"""Embedding route endpoint."""

from fastapi import APIRouter, HTTPException, Request, status

from app.config import settings
from app.models.embedding_models import EmbeddingRequest, EmbeddingResponse
from app.services.embedding_service import EmbeddingService

router = APIRouter(prefix="/embed", tags=["embedding"])
# Limiter will be set by main.py after app initialization
limiter = None


@router.post("", response_model=EmbeddingResponse, status_code=status.HTTP_200_OK)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute" if settings.rate_limit_enabled else "1000/minute")
async def create_embedding(request: Request, embedding_request: EmbeddingRequest):
    """
    Generate and store embedding for text.

    Args:
        request: FastAPI Request object
        embedding_request: EmbeddingRequest with text and metadata

    Returns:
        EmbeddingResponse with embedding ID and status
    """
    try:
        # Initialize embedding service
        embedding_service = EmbeddingService()

        # Generate embedding
        embedding = embedding_service.generate_embedding(embedding_request.text)

        # Store embedding
        embedding_id = embedding_service.store_embedding(
            embedding_request.text, embedding, embedding_request.metadata.model_dump()
        )

        return EmbeddingResponse(
            embedding_id=embedding_id,
            status="stored",
            vector_dimension=len(embedding),
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Embedding generation or storage failed: {str(e)}",
        ) from e
