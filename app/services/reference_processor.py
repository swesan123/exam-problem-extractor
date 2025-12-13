"""Background processing service for reference content uploads."""

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from threading import Semaphore
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.db.models import ReferenceUploadJob
from app.services.embedding_service import EmbeddingService
from app.services.metrics_service import MetricsService
from app.services.ocr_service import OCRService
from app.utils.chunking import smart_chunk
from app.utils.file_utils import cleanup_temp_file, convert_pdf_to_images

logger = logging.getLogger(__name__)


class ReferenceProcessor:
    """
    Coordinates background processing of reference content uploads.
    Uses ThreadPoolExecutor for parallel file processing.
    """

    def __init__(self, max_workers: int = 4):
        """
        Initialize reference processor.

        Args:
            max_workers: Maximum number of worker threads for parallel processing
        """
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.ocr_semaphore = Semaphore(10)  # Limit concurrent OCR calls
        self.embedding_semaphore = Semaphore(5)  # Limit concurrent embedding calls

    def process_job(
        self, job_id: str, file_paths: List[Path], metadata: Dict, db: Session
    ) -> None:
        """
        Main processing coordinator.
        Distributes files across workers and updates progress.

        Args:
            job_id: Job ID
            file_paths: List of file paths to process
            metadata: Metadata dict with class_id, exam_source, exam_type
            db: Database session
        """
        try:
            # Load job from database
            job = (
                db.query(ReferenceUploadJob)
                .filter(ReferenceUploadJob.id == job_id)
                .first()
            )
            if not job:
                logger.error(f"Job {job_id} not found")
                return

            job.status = "processing"
            job.total_files = len(file_paths)
            job.file_statuses = {
                str(path.name): {"status": "pending", "progress": 0}
                for path in file_paths
            }
            db.commit()

            # Process files in parallel
            futures = []
            for file_path in file_paths:
                future = self.executor.submit(
                    self._process_single_file,
                    job_id,
                    file_path,
                    metadata,
                    db,
                )
                futures.append((file_path.name, future))

            # Wait for completion and update progress
            for filename, future in futures:
                try:
                    result = future.result()  # Blocks until complete
                    self._update_file_status(db, job_id, filename, "completed", 100)
                    self._increment_processed_files(db, job_id)
                except Exception as e:
                    logger.error(
                        f"Failed to process file {filename}: {e}", exc_info=True
                    )
                    self._update_file_status(db, job_id, filename, "failed", 0, str(e))
                    self._increment_failed_files(db, job_id)

            # Mark job as completed
            job = (
                db.query(ReferenceUploadJob)
                .filter(ReferenceUploadJob.id == job_id)
                .first()
            )
            if job:
                if job.processed_files > 0:
                    job.status = "completed"
                    job.progress = 100
                else:
                    job.status = "failed"
                    job.error_message = "All files failed to process"
                job.completed_at = datetime.utcnow()
                db.commit()

        except Exception as e:
            logger.error(f"Job {job_id} processing failed: {e}", exc_info=True)
            job = (
                db.query(ReferenceUploadJob)
                .filter(ReferenceUploadJob.id == job_id)
                .first()
            )
            if job:
                job.status = "failed"
                job.error_message = str(e)
                db.commit()

    def _process_single_file(
        self, job_id: str, file_path: Path, metadata: Dict, db: Session
    ) -> Dict:
        """
        Process a single file: OCR → Chunk → Embed → Store.
        Runs in parallel with other files.

        Args:
            job_id: Job ID
            file_path: Path to file to process
            metadata: Metadata dict with class_id, exam_source, exam_type
            db: Database session

        Returns:
            Dict with success status and chunk count
        """
        metrics_service = MetricsService(db)
        metrics_id = None

        try:
            # Initialize metrics tracking
            file_size_bytes = file_path.stat().st_size
            file_type = self._get_file_type(file_path)
            page_count = None
            if file_path.suffix.lower() == ".pdf":
                # For PDFs, try to count pages (optional dependency)
                try:
                    from PyPDF2 import PdfReader

                    reader = PdfReader(str(file_path))
                    page_count = len(reader.pages)
                except ImportError:
                    # PyPDF2 not installed, leave as None
                    pass
                except Exception:
                    # Error reading PDF, leave as None
                    pass

            metrics = metrics_service.create_file_metrics(
                job_id=job_id,
                filename=file_path.name,
                file_size_bytes=file_size_bytes,
                file_type=file_type,
                page_count=page_count,
            )
            metrics_id = metrics.id

            # Record upload time (assume upload completed when processing starts)
            upload_end_time = datetime.utcnow()
            metrics_service.update_upload_times(
                metrics_id, upload_end_time, upload_end_time
            )

            # Step 1: OCR extraction (with rate limiting)
            with self.ocr_semaphore:
                self._update_file_status(db, job_id, file_path.name, "processing", 10)
                ocr_start = datetime.utcnow()
                text = self._extract_text_ocr(file_path)
                ocr_end = datetime.utcnow()
                metrics_service.update_processing_step(
                    metrics_id, "ocr", ocr_start, ocr_end
                )

            # Step 2: Chunk text
            self._update_file_status(db, job_id, file_path.name, "processing", 30)
            chunking_start = datetime.utcnow()
            chunks = smart_chunk(text, max_size=1000)
            chunking_end = datetime.utcnow()
            metrics_service.update_processing_step(
                metrics_id, "chunking", chunking_start, chunking_end
            )

            # Step 3: Generate embeddings and store in ChromaDB (batch)
            with self.embedding_semaphore:
                self._update_file_status(db, job_id, file_path.name, "processing", 60)
                embedding_start = datetime.utcnow()
                self._store_embeddings_batch(chunks, file_path, metadata)
                embedding_end = datetime.utcnow()
                metrics_service.update_processing_step(
                    metrics_id, "embedding", embedding_start, embedding_end
                )

                # Storage happens as part of embedding batch_store
                storage_start = embedding_start
                storage_end = embedding_end
                metrics_service.update_processing_step(
                    metrics_id, "storage", storage_start, storage_end
                )

                self._update_file_status(db, job_id, file_path.name, "processing", 90)

            return {"success": True, "chunks": len(chunks)}

        except Exception as e:
            logger.error(f"Failed to process {file_path.name}: {e}", exc_info=True)
            raise

    def _get_file_type(self, file_path: Path) -> str:
        """
        Get MIME type for a file based on extension.

        Args:
            file_path: Path to file

        Returns:
            MIME type string
        """
        suffix = file_path.suffix.lower()
        type_map = {
            ".pdf": "application/pdf",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        return type_map.get(suffix, "application/octet-stream")

    def _extract_text_ocr(self, file_path: Path) -> str:
        """
        Extract text from file using OCR.

        Args:
            file_path: Path to file

        Returns:
            Extracted text
        """
        ocr_service = OCRService()

        # Handle PDF files
        if file_path.suffix.lower() == ".pdf":
            image_paths = convert_pdf_to_images(file_path)
            all_text_parts = []
            try:
                for page_num, image_path in enumerate(image_paths, start=1):
                    text = ocr_service.extract_text(image_path)
                    page_header = f"=== Page {page_num} ===\n"
                    all_text_parts.append(page_header + text)
                return "\n\n".join(all_text_parts)
            finally:
                # Clean up generated images
                for img_path in image_paths:
                    cleanup_temp_file(img_path)
        else:
            # Handle regular image files
            return ocr_service.extract_text(file_path)

    def _store_embeddings_batch(
        self, chunks: List[str], file_path: Path, metadata: Dict
    ) -> None:
        """
        Store embeddings in ChromaDB using optimized batch processing.

        Args:
            chunks: List of text chunks
            file_path: Path to source file
            metadata: Base metadata dict
        """
        embedding_service = EmbeddingService()

        # Prepare metadata for each chunk
        metadata_list = []
        for i, chunk in enumerate(chunks):
            chunk_metadata = metadata.copy()
            chunk_metadata["chunk_id"] = f"{file_path.stem}_chunk_{i}"
            chunk_metadata["source_file"] = file_path.name
            metadata_list.append(chunk_metadata)

        # Use batch_store which generates embeddings in optimized batches internally
        # OpenAI supports up to 2048 inputs per batch, but we'll use 200 for optimal performance
        embedding_service.batch_store(chunks, metadata_list)

    def _update_file_status(
        self,
        db: Session,
        job_id: str,
        filename: str,
        status: str,
        progress: int,
        error: Optional[str] = None,
    ) -> None:
        """Update status for a single file in the job."""
        job = (
            db.query(ReferenceUploadJob).filter(ReferenceUploadJob.id == job_id).first()
        )
        if job:
            if job.file_statuses is None:
                job.file_statuses = {}
            job.file_statuses[filename] = {
                "status": status,
                "progress": progress,
                "error": error,
            }
            # Update overall progress
            total_progress = sum(
                f.get("progress", 0) for f in job.file_statuses.values()
            )
            job.progress = (
                int(total_progress / len(job.file_statuses)) if job.file_statuses else 0
            )
            db.commit()

    def _increment_processed_files(self, db: Session, job_id: str) -> None:
        """Increment processed files count."""
        job = (
            db.query(ReferenceUploadJob).filter(ReferenceUploadJob.id == job_id).first()
        )
        if job:
            job.processed_files += 1
            db.commit()

    def _increment_failed_files(self, db: Session, job_id: str) -> None:
        """Increment failed files count."""
        job = (
            db.query(ReferenceUploadJob).filter(ReferenceUploadJob.id == job_id).first()
        )
        if job:
            job.failed_files += 1
            db.commit()
