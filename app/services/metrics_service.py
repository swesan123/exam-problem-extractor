"""Service for tracking and managing upload performance metrics."""

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.db.models import UploadMetrics

logger = logging.getLogger(__name__)


class MetricsService:
    """Service for managing upload and processing metrics."""

    def __init__(self, db: Session):
        """
        Initialize metrics service.

        Args:
            db: Database session
        """
        self.db = db

    def create_file_metrics(
        self,
        job_id: str,
        filename: str,
        file_size_bytes: int,
        file_type: str,
        page_count: Optional[int] = None,
    ) -> UploadMetrics:
        """
        Create a new metrics record for a file.

        Args:
            job_id: Job ID
            filename: Name of the file
            file_size_bytes: Size of file in bytes
            file_type: MIME type of file (e.g., 'application/pdf', 'image/png')
            page_count: Number of pages (for PDFs)

        Returns:
            Created metrics record
        """
        metrics_id = f"metrics_{uuid.uuid4().hex[:12]}"
        metrics = UploadMetrics(
            id=metrics_id,
            job_id=job_id,
            filename=filename,
            file_size_bytes=file_size_bytes,
            file_type=file_type,
            page_count=page_count,
        )
        self.db.add(metrics)
        self.db.commit()
        self.db.refresh(metrics)
        logger.debug(f"Created metrics {metrics_id} for file {filename} in job {job_id}")
        return metrics

    def update_upload_times(
        self, metrics_id: str, start_time: datetime, end_time: datetime
    ) -> None:
        """
        Update upload start and end times.

        Args:
            metrics_id: Metrics record ID
            start_time: Upload start time
            end_time: Upload end time
        """
        metrics = (
            self.db.query(UploadMetrics).filter(UploadMetrics.id == metrics_id).first()
        )
        if metrics:
            metrics.upload_start_time = start_time
            metrics.upload_end_time = end_time
            # Calculate network throughput
            if start_time and end_time:
                duration_seconds = (end_time - start_time).total_seconds()
                if duration_seconds > 0:
                    metrics.network_throughput_bps = (
                        metrics.file_size_bytes / duration_seconds
                    )
            self.db.commit()

    def update_processing_step(
        self,
        metrics_id: str,
        step_name: str,
        start_time: datetime,
        end_time: datetime,
    ) -> None:
        """
        Update timestamps for a processing step (OCR, chunking, embedding, storage).

        Args:
            metrics_id: Metrics record ID
            step_name: Name of the step ('ocr', 'chunking', 'embedding', 'storage')
            start_time: Step start time
            end_time: Step end time
        """
        metrics = (
            self.db.query(UploadMetrics).filter(UploadMetrics.id == metrics_id).first()
        )
        if not metrics:
            logger.warning(f"Metrics {metrics_id} not found")
            return

        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        if step_name == "ocr":
            metrics.ocr_start_time = start_time
            metrics.ocr_end_time = end_time
            metrics.ocr_duration_ms = duration_ms
        elif step_name == "chunking":
            metrics.chunking_start_time = start_time
            metrics.chunking_end_time = end_time
            metrics.chunking_duration_ms = duration_ms
        elif step_name == "embedding":
            metrics.embedding_start_time = start_time
            metrics.embedding_end_time = end_time
            metrics.embedding_duration_ms = duration_ms
        elif step_name == "storage":
            metrics.storage_start_time = start_time
            metrics.storage_end_time = end_time
            metrics.storage_duration_ms = duration_ms
        else:
            logger.warning(f"Unknown step name: {step_name}")

        # Update total duration
        self._calculate_total_duration(metrics)
        self.db.commit()

    def _calculate_total_duration(self, metrics: UploadMetrics) -> None:
        """
        Calculate total processing duration from all steps.

        Args:
            metrics: Metrics record to update
        """
        total_ms = 0
        if metrics.ocr_duration_ms:
            total_ms += metrics.ocr_duration_ms
        if metrics.chunking_duration_ms:
            total_ms += metrics.chunking_duration_ms
        if metrics.embedding_duration_ms:
            total_ms += metrics.embedding_duration_ms
        if metrics.storage_duration_ms:
            total_ms += metrics.storage_duration_ms

        metrics.total_duration_ms = total_ms if total_ms > 0 else None

    def calculate_throughput(
        self, file_size_bytes: int, duration_seconds: float
    ) -> float:
        """
        Calculate network throughput in bytes per second.

        Args:
            file_size_bytes: File size in bytes
            duration_seconds: Duration in seconds

        Returns:
            Throughput in bytes per second
        """
        if duration_seconds <= 0:
            return 0.0
        return file_size_bytes / duration_seconds

    def get_job_metrics_summary(self, job_id: str) -> Dict:
        """
        Get summary metrics for a job.

        Args:
            job_id: Job ID

        Returns:
            Dictionary with summary statistics
        """
        metrics_list = (
            self.db.query(UploadMetrics)
            .filter(UploadMetrics.job_id == job_id)
            .all()
        )

        if not metrics_list:
            return {
                "total_files": 0,
                "total_size_bytes": 0,
                "avg_upload_throughput_bps": 0.0,
                "avg_ocr_duration_ms": 0.0,
                "avg_chunking_duration_ms": 0.0,
                "avg_embedding_duration_ms": 0.0,
                "avg_storage_duration_ms": 0.0,
                "avg_total_duration_ms": 0.0,
            }

        total_size = sum(m.file_size_bytes for m in metrics_list)
        throughputs = [
            m.network_throughput_bps
            for m in metrics_list
            if m.network_throughput_bps is not None
        ]
        ocr_durations = [
            m.ocr_duration_ms for m in metrics_list if m.ocr_duration_ms is not None
        ]
        chunking_durations = [
            m.chunking_duration_ms
            for m in metrics_list
            if m.chunking_duration_ms is not None
        ]
        embedding_durations = [
            m.embedding_duration_ms
            for m in metrics_list
            if m.embedding_duration_ms is not None
        ]
        storage_durations = [
            m.storage_duration_ms
            for m in metrics_list
            if m.storage_duration_ms is not None
        ]
        total_durations = [
            m.total_duration_ms for m in metrics_list if m.total_duration_ms is not None
        ]

        def avg(values: List[float]) -> float:
            return sum(values) / len(values) if values else 0.0

        return {
            "total_files": len(metrics_list),
            "total_size_bytes": total_size,
            "avg_upload_throughput_bps": avg(throughputs),
            "avg_ocr_duration_ms": avg(ocr_durations),
            "avg_chunking_duration_ms": avg(chunking_durations),
            "avg_embedding_duration_ms": avg(embedding_durations),
            "avg_storage_duration_ms": avg(storage_durations),
            "avg_total_duration_ms": avg(total_durations),
        }

    def get_job_metrics(self, job_id: str) -> List[UploadMetrics]:
        """
        Get all metrics records for a job.

        Args:
            job_id: Job ID

        Returns:
            List of metrics records
        """
        return (
            self.db.query(UploadMetrics)
            .filter(UploadMetrics.job_id == job_id)
            .all()
        )

