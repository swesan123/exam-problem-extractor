"""Retrieval route endpoint."""
from fastapi import APIRouter, HTTPException, status

from app.models.retrieval_models import RetrieveRequest, RetrieveResponse
from app.services.embedding_service import EmbeddingService
from app.services.retrieval_service import RetrievalService

router = APIRouter(prefix="/retrieve", tags=["retrieval"])


@router.post("", response_model=RetrieveResponse, status_code=status.HTTP_200_OK)
async def retrieve_similar(request: RetrieveRequest):
    """
    Retrieve similar exam content from vector database.

    Args:
        request: RetrieveRequest with query and top_k

    Returns:
        RetrieveResponse with ranked results
    """
    try:
        # Initialize services
        embedding_service = EmbeddingService()
        retrieval_service = RetrievalService(embedding_service)

        # Retrieve similar content
        results = retrieval_service.retrieve_with_scores(request.query, request.top_k)

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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Retrieval failed: {str(e)}",
        ) from e

