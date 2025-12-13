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
        self,
        job_id: str,
        file_info_list: List[tuple[Path, str]],
        metadata: Dict,
        db: Session,
    ) -> None:
        """
        Main processing coordinator.
        Distributes files across workers and updates progress.

        Args:
            job_id: Job ID
            file_info_list: List of tuples (temp_path, original_filename) to process
            metadata: Metadata dict with class_id, exam_source, exam_type, reference_type
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
            job.total_files = len(file_info_list)
            job.file_statuses = {
                original_filename: {"status": "pending", "progress": 0}
                for _, original_filename in file_info_list
            }
            db.commit()

            # Process files in parallel
            futures = []
            for file_path, original_filename in file_info_list:
                future = self.executor.submit(
                    self._process_single_file,
                    job_id,
                    file_path,
                    original_filename,
                    metadata,
                    db,
                )
                futures.append((original_filename, future))

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
        self,
        job_id: str,
        file_path: Path,
        original_filename: str,
        metadata: Dict,
        db: Session,
    ) -> Dict:
        """
        Process a single file: OCR → Chunk → Embed → Store.
        Runs in parallel with other files.

        Args:
            job_id: Job ID
            file_path: Path to temp file to process
            original_filename: Original filename from upload
            metadata: Metadata dict with class_id, exam_source, exam_type, reference_type
            db: Database session

        Returns:
            Dict with success status and chunk count
        """
        try:
            # Step 1: OCR extraction (with rate limiting)
            with self.ocr_semaphore:
                self._update_file_status(
                    db, job_id, original_filename, "processing", 10
                )
                text = self._extract_text_ocr(file_path)

            # Step 2: Chunk text
            self._update_file_status(db, job_id, original_filename, "processing", 30)
            chunks = smart_chunk(text, max_size=1000)

            # Step 3: Generate embeddings and store in ChromaDB (batch)
            with self.embedding_semaphore:
                self._update_file_status(
                    db, job_id, original_filename, "processing", 60
                )
                self._store_embeddings_batch(
                    chunks, file_path, original_filename, metadata
                )
                self._update_file_status(
                    db, job_id, original_filename, "processing", 90
                )

            return {"success": True, "chunks": len(chunks)}

        except Exception as e:
            logger.error(
                f"Failed to process {original_filename}: {e}", exc_info=True
            )
            raise

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
        self,
        chunks: List[str],
        file_path: Path,
        original_filename: str,
        metadata: Dict,
    ) -> None:
        """
        Store embeddings in ChromaDB using optimized batch processing.

        Args:
            chunks: List of text chunks
            file_path: Path to temp source file
            original_filename: Original filename from upload
            metadata: Base metadata dict (includes reference_type)
        """
        embedding_service = EmbeddingService()

        # Prepare metadata for each chunk
        metadata_list = []
        for i, chunk in enumerate(chunks):
            chunk_metadata = metadata.copy()
            # Use original filename stem for chunk_id, but original filename for source_file
            chunk_metadata["chunk_id"] = f"{Path(original_filename).stem}_chunk_{i}"
            chunk_metadata["source_file"] = original_filename
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
