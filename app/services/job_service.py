"""Service for managing reference upload jobs."""

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.db.models import ReferenceUploadJob
from app.services.metrics_service import MetricsService

logger = logging.getLogger(__name__)


class JobService:
    """Service for managing reference upload jobs."""

    def __init__(self, db: Session):
        """
        Initialize job service.

        Args:
            db: Database session
        """
        self.db = db

    def create_job(
        self,
        class_id: str,
        total_files: int,
        exam_source: Optional[str] = None,
        exam_type: Optional[str] = None,
    ) -> ReferenceUploadJob:
        """
        Create a new reference upload job.

        Args:
            class_id: Class ID
            total_files: Total number of files to process
            exam_source: Optional exam source
            exam_type: Optional exam type

        Returns:
            Created job
        """
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        job = ReferenceUploadJob(
            id=job_id,
            class_id=class_id,
            exam_source=exam_source,
            exam_type=exam_type,
            status="pending",
            progress=0,
            total_files=total_files,
            processed_files=0,
            failed_files=0,
            file_statuses={},
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        logger.info(
            f"Created job {job_id} for class {class_id} with {total_files} files"
        )
        return job

    def get_job(self, job_id: str) -> Optional[ReferenceUploadJob]:
        """
        Get job by ID.

        Args:
            job_id: Job ID

        Returns:
            Job if found, None otherwise
        """
        return (
            self.db.query(ReferenceUploadJob)
            .filter(ReferenceUploadJob.id == job_id)
            .first()
        )

    def list_class_jobs(self, class_id: str) -> List[ReferenceUploadJob]:
        """
        List all jobs for a class.

        Args:
            class_id: Class ID

        Returns:
            List of jobs
        """
        return (
            self.db.query(ReferenceUploadJob)
            .filter(ReferenceUploadJob.class_id == class_id)
            .order_by(ReferenceUploadJob.created_at.desc())
            .all()
        )

    def get_job_metrics(self, job_id: str) -> List:
        """
        Get all metrics records for a job.

        Args:
            job_id: Job ID

        Returns:
            List of metrics records
        """
        metrics_service = MetricsService(self.db)
        return metrics_service.get_job_metrics(job_id)

    def calculate_eta(self, job_id: str) -> Optional[float]:
        """
        Calculate estimated time to completion based on historical averages.

        Args:
            job_id: Job ID

        Returns:
            Estimated seconds remaining, or None if cannot calculate
        """
        job = self.get_job(job_id)
        if not job or job.status not in ["pending", "processing"]:
            return None

        metrics_service = MetricsService(self.db)
        summary = metrics_service.get_job_metrics_summary(job_id)

        if summary["total_files"] == 0 or summary["avg_total_duration_ms"] == 0:
            return None

        # Calculate average time per file
        avg_time_per_file_ms = summary["avg_total_duration_ms"]
        remaining_files = job.total_files - job.processed_files

        if remaining_files <= 0:
            return 0.0

        # Estimate: remaining files * average time per file
        estimated_ms = remaining_files * avg_time_per_file_ms
        return estimated_ms / 1000.0  # Convert to seconds
