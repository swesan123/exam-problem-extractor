"""Retrieval route endpoint."""

import logging

from fastapi import APIRouter, HTTPException, Request, status

from app.config import settings
from app.models.retrieval_models import RetrieveRequest, RetrieveResponse
from app.services.embedding_service import EmbeddingService
from app.services.retrieval_service import RetrievalService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/retrieve", tags=["retrieval"])


@router.post("", response_model=RetrieveResponse, status_code=status.HTTP_200_OK)
async def retrieve_similar(request: Request, retrieve_request: RetrieveRequest):
    """
    Retrieve similar exam content from vector database.

    Args:
        request: FastAPI Request object
        retrieve_request: RetrieveRequest with query and top_k

    Returns:
        RetrieveResponse with ranked results
    """
    try:
        # Initialize services
        embedding_service = EmbeddingService()
        retrieval_service = RetrievalService(embedding_service)

        # Retrieve similar content
        results = retrieval_service.retrieve_with_scores(
            retrieve_request.query, retrieve_request.top_k
        )

        # Get embedding dimension (from embedding model)
        # OpenAI text-embedding-ada-002 has 1536 dimensions
        query_embedding_dim = 1536

        return RetrieveResponse(
            results=results,
            query_embedding_dim=query_embedding_dim,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        from app.config import settings
        from app.utils.error_utils import get_safe_error_detail

        logger.error(f"Retrieval failed: {str(e)}", exc_info=True)
        is_production = settings.environment.lower() == "production"
        # Sanitize the full error message, not just the exception
        full_error_msg = f"Retrieval failed: {str(e)}"
        from app.utils.error_utils import sanitize_error_message
        safe_detail = sanitize_error_message(full_error_msg, is_production)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=safe_detail,
        ) from e
