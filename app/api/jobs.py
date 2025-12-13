"""Job management API endpoints for reference content uploads."""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import ReferenceUploadJob
from app.services.job_service import JobService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reference-content/jobs", tags=["jobs"])


@router.get("/{job_id}", status_code=status.HTTP_200_OK)
async def get_job_status(
    job_id: str,
    db: Session = Depends(get_db),
):
    """
    Get status of a reference upload job.

    Args:
        job_id: Job ID
        db: Database session

    Returns:
        Job status with progress information

    Raises:
        HTTPException: 404 if job not found, 500 on server error
    """
    try:
        job_service = JobService(db)
        job = job_service.get_job(job_id)

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job with ID '{job_id}' not found",
            )

        # Calculate ETA
        estimated_completion_time = job_service.calculate_eta(job_id)

        # Get metrics summary (optional, only if metrics exist)
        metrics_summary = None
        try:
            from app.services.metrics_service import MetricsService

            metrics_service = MetricsService(db)
            summary = metrics_service.get_job_metrics_summary(job_id)
            if summary["total_files"] > 0:
                metrics_summary = summary
        except Exception as e:
            logger.debug(f"Could not get metrics summary: {e}")

        return {
            "job_id": job.id,
            "status": job.status,
            "progress": job.progress,
            "total_files": job.total_files,
            "processed_files": job.processed_files,
            "failed_files": job.failed_files,
            "file_statuses": job.file_statuses or {},
            "error_message": job.error_message,
            "estimated_completion_time": estimated_completion_time,
            "metrics_summary": metrics_summary,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "updated_at": job.updated_at.isoformat() if job.updated_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job status {job_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job status: {str(e)}",
        ) from e


@router.get("/class/{class_id}", status_code=status.HTTP_200_OK)
async def list_class_jobs(
    class_id: str,
    db: Session = Depends(get_db),
):
    """
    List all jobs for a specific class.

    Args:
        class_id: Class ID
        db: Database session

    Returns:
        List of jobs for the class

    Raises:
        HTTPException: 500 on server error
    """
    try:
        job_service = JobService(db)
        jobs = job_service.list_class_jobs(class_id)

        return {
            "class_id": class_id,
            "jobs": [
                {
                    "job_id": job.id,
                    "status": job.status,
                    "progress": job.progress,
                    "total_files": job.total_files,
                    "processed_files": job.processed_files,
                    "failed_files": job.failed_files,
                    "created_at": (
                        job.created_at.isoformat() if job.created_at else None
                    ),
                    "completed_at": (
                        job.completed_at.isoformat() if job.completed_at else None
                    ),
                }
                for job in jobs
            ],
        }

    except Exception as e:
        logger.error(f"Failed to list jobs for class {class_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list jobs: {str(e)}",
        ) from e
