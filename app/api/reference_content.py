"""Reference content management API endpoints."""

import logging
from pathlib import Path
from threading import Thread
from typing import List, Optional

from fastapi import (APIRouter, Depends, File, Form, HTTPException, UploadFile,
                     status)
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.class_service import ClassService
from app.services.embedding_service import EmbeddingService
from app.services.job_service import JobService
from app.services.reference_processor import ReferenceProcessor
from app.utils.file_utils import save_temp_file, validate_upload_file

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reference-content", tags=["reference-content"])

# Global processor instance
_processor = ReferenceProcessor(max_workers=4)


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

    Raises:
        HTTPException: 404 if class not found, 500 on server error
    """
    try:
        # Validate that the class exists
        class_service = ClassService(db)
        class_obj = class_service.get_class(class_id)
        if not class_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Class with ID '{class_id}' not found",
            )

        embedding_service = EmbeddingService()
        reference_content = embedding_service.list_embeddings_by_class(class_id)

        return {
            "class_id": class_id,
            "items": reference_content,
            "count": len(reference_content),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to list reference content for class {class_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list reference content: {str(e)}",
        ) from e


@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_reference_content(
    class_id: str = Form(...),
    files: List[UploadFile] = File(...),
    exam_source: Optional[str] = Form(None),
    exam_type: Optional[str] = Form(None),
    reference_type: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """
    Upload reference content files for background processing.

    Args:
        class_id: Class ID to associate reference content with
        files: List of files to upload
        exam_source: Optional exam source
        exam_type: Optional exam type
        reference_type: Optional reference type (e.g., assessment, lecture, homework, notes, textbook)
        db: Database session

    Returns:
        Job ID and initial status

    Raises:
        HTTPException: 400 if validation fails, 404 if class not found, 500 on server error
    """
    try:
        # Validate class exists
        class_service = ClassService(db)
        class_obj = class_service.get_class(class_id)
        if not class_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Class with ID '{class_id}' not found",
            )

        # Validate files
        if not files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one file must be provided",
            )

        for file in files:
            validate_upload_file(file)

        # Create job
        job_service = JobService(db)
        job = job_service.create_job(
            class_id=class_id,
            total_files=len(files),
            exam_source=exam_source,
            exam_type=exam_type,
        )

        # Save files temporarily and preserve original filenames
        file_info_list = []  # List of tuples: (temp_path, original_filename)
        try:
            for file in files:
                temp_path = save_temp_file(file)
                original_filename = file.filename or temp_path.name
                file_info_list.append((temp_path, original_filename))
        except Exception as e:
            logger.error(f"Failed to save files: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save files: {str(e)}",
            ) from e

        # Prepare metadata
        metadata = {
            "class_id": class_id,
            "exam_source": exam_source,
            "exam_type": exam_type,
            "reference_type": reference_type,
        }

        # Start background processing in a separate thread
        # Note: We need to create a new database session for the background thread
        from app.db.database import SessionLocal

        def process_in_background():
            background_db = SessionLocal()
            try:
                _processor.process_job(
                    job.id, file_info_list, metadata, background_db
                )
            except Exception as e:
                logger.error(
                    f"Background processing failed for job {job.id}: {e}", exc_info=True
                )
            finally:
                background_db.close()

        thread = Thread(target=process_in_background, daemon=True)
        thread.start()

        return {
            "job_id": job.id,
            "status": job.status,
            "total_files": job.total_files,
            "message": "Upload started. Processing in background.",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload reference content: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload reference content: {str(e)}",
        ) from e


@router.delete("/{chunk_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reference_content(
    chunk_id: str,
    db: Session = Depends(get_db),  # Keep for consistency with other endpoints
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
        logger.error(
            f"Failed to delete reference content {chunk_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete reference content: {str(e)}",
        ) from e
