"""SQLAlchemy database models for classes and questions."""

from datetime import datetime
from typing import Dict, Optional

from sqlalchemy import (
    JSON,
    BigInteger,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class Class(Base):
    """Class model for organizing exam questions."""

    __tablename__ = "classes"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    subject = Column(String, nullable=True, index=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationship to questions
    questions = relationship(
        "Question", back_populates="class_obj", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Class(id={self.id}, name={self.name})>"


class Question(Base):
    """Question model for storing exam questions."""

    __tablename__ = "questions"

    id = Column(String, primary_key=True, index=True)
    class_id = Column(
        String, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_text = Column(Text, nullable=False)
    solution = Column(Text, nullable=True)
    question_metadata = Column(
        "metadata", JSON, nullable=True, default=dict
    )  # Using "metadata" as column name but question_metadata as attribute
    source_image = Column(String, nullable=True)  # Path to original image if available
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationship to class
    class_obj = relationship("Class", back_populates="questions")

    def __repr__(self):
        return f"<Question(id={self.id}, class_id={self.class_id})>"


class ReferenceUploadJob(Base):
    """Model for tracking reference content upload jobs."""

    __tablename__ = "reference_upload_jobs"

    id = Column(String, primary_key=True, index=True)
    class_id = Column(
        String, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    exam_source = Column(String, nullable=True)
    exam_type = Column(String, nullable=True)

    # Status tracking
    status = Column(String, nullable=False, default="pending", index=True)  # pending, processing, completed, failed
    progress = Column(Integer, nullable=False, default=0)  # 0-100

    # File tracking
    total_files = Column(Integer, nullable=False, default=0)
    processed_files = Column(Integer, nullable=False, default=0)
    failed_files = Column(Integer, nullable=False, default=0)

    # Per-file status (JSON)
    file_statuses = Column(JSON, nullable=True, default=dict)
    # Format: {
    #   "filename1.pdf": {"status": "processing", "progress": 50, "error": null},
    #   "filename2.pdf": {"status": "completed", "progress": 100, "error": null}
    # }

    # Error handling
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<ReferenceUploadJob(id={self.id}, status={self.status}, progress={self.progress}%)>"


class UploadMetrics(Base):
    """Model for tracking per-file upload and processing metrics."""

    __tablename__ = "upload_metrics"

    id = Column(String, primary_key=True, index=True)
    job_id = Column(
        String,
        ForeignKey("reference_upload_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # File information
    filename = Column(String, nullable=False)
    file_size_bytes = Column(BigInteger, nullable=False)
    file_type = Column(String, nullable=False)  # e.g., 'application/pdf', 'image/png'
    page_count = Column(Integer, nullable=True)  # For PDFs

    # Upload timestamps
    upload_start_time = Column(DateTime(timezone=True), nullable=True)
    upload_end_time = Column(DateTime(timezone=True), nullable=True)

    # OCR timestamps
    ocr_start_time = Column(DateTime(timezone=True), nullable=True)
    ocr_end_time = Column(DateTime(timezone=True), nullable=True)
    ocr_duration_ms = Column(Integer, nullable=True)

    # Chunking timestamps
    chunking_start_time = Column(DateTime(timezone=True), nullable=True)
    chunking_end_time = Column(DateTime(timezone=True), nullable=True)
    chunking_duration_ms = Column(Integer, nullable=True)

    # Embedding timestamps
    embedding_start_time = Column(DateTime(timezone=True), nullable=True)
    embedding_end_time = Column(DateTime(timezone=True), nullable=True)
    embedding_duration_ms = Column(Integer, nullable=True)

    # Storage timestamps
    storage_start_time = Column(DateTime(timezone=True), nullable=True)
    storage_end_time = Column(DateTime(timezone=True), nullable=True)
    storage_duration_ms = Column(Integer, nullable=True)

    # Calculated metrics
    total_duration_ms = Column(Integer, nullable=True)
    network_throughput_bps = Column(Float, nullable=True)  # bytes per second

    # Timestamp
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationship to job
    job = relationship("ReferenceUploadJob", backref="metrics")

    def __repr__(self):
        return f"<UploadMetrics(id={self.id}, filename={self.filename}, job_id={self.job_id})>"
