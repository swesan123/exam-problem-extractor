"""Service for managing reference upload jobs."""

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.db.models import ReferenceUploadJob

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
        logger.info(f"Created job {job_id} for class {class_id} with {total_files} files")
        return job

    def get_job(self, job_id: str) -> Optional[ReferenceUploadJob]:
        """
        Get job by ID.

        Args:
            job_id: Job ID

        Returns:
            Job if found, None otherwise
        """
        return self.db.query(ReferenceUploadJob).filter(ReferenceUploadJob.id == job_id).first()

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

