"""Embedding route endpoint."""
from fastapi import APIRouter, HTTPException, status

from app.models.embedding_models import EmbeddingRequest, EmbeddingResponse
from app.services.embedding_service import EmbeddingService

router = APIRouter(prefix="/embed", tags=["embedding"])


@router.post("", response_model=EmbeddingResponse, status_code=status.HTTP_200_OK)
async def create_embedding(request: EmbeddingRequest):
    """
    Generate and store embedding for text.

    Args:
        request: EmbeddingRequest with text and metadata

    Returns:
        EmbeddingResponse with embedding ID and status
    """
    try:
        # Initialize embedding service
        embedding_service = EmbeddingService()

        # Generate embedding
        embedding = embedding_service.generate_embedding(request.text)

        # Store embedding
        embedding_id = embedding_service.store_embedding(
            request.text, embedding, request.metadata.model_dump()
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

