"""Reference content management API endpoints."""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reference-content", tags=["reference-content"])


@router.get("/classes/{class_id}", status_code=status.HTTP_200_OK)
async def list_class_reference_content(
    class_id: str,
    db: Session = Depends(get_db),
):
    """
    List all reference content for a specific class.

    Args:
        class_id: Class ID
        db: Database session

    Returns:
        List of reference content items with metadata
    """
    try:
        embedding_service = EmbeddingService()
        reference_content = embedding_service.list_embeddings_by_class(class_id)

        return {
            "class_id": class_id,
            "items": reference_content,
            "count": len(reference_content),
        }

    except Exception as e:
        logger.error(f"Failed to list reference content for class {class_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list reference content: {str(e)}",
        ) from e


@router.delete("/{chunk_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reference_content(
    chunk_id: str,
    db: Session = Depends(get_db),
):
    """
    Delete a reference content item by chunk_id.

    Args:
        chunk_id: Chunk ID to delete
        db: Database session

    Returns:
        No content on success
    """
    try:
        embedding_service = EmbeddingService()
        deleted = embedding_service.delete_embedding(chunk_id)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Reference content with chunk_id '{chunk_id}' not found",
            )

        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete reference content {chunk_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete reference content: {str(e)}",
        ) from e

