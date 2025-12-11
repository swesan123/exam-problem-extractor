"""Embedding route endpoint."""

import logging

from fastapi import APIRouter, HTTPException, Request, status

from app.config import settings
from app.models.embedding_models import EmbeddingRequest, EmbeddingResponse
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/embed", tags=["embedding"])


@router.post("", response_model=EmbeddingResponse, status_code=status.HTTP_200_OK)
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
        from app.config import settings
        from app.utils.error_utils import get_safe_error_detail

        logger.error(f"Embedding generation or storage failed: {str(e)}", exc_info=True)
        is_production = settings.environment.lower() == "production"
        # Sanitize the full error message, not just the exception
        full_error_msg = f"Embedding generation or storage failed: {str(e)}"
        from app.utils.error_utils import sanitize_error_message
        safe_detail = sanitize_error_message(full_error_msg, is_production)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=safe_detail,
        ) from e
