"""SQLAlchemy database models for classes and questions."""

from datetime import datetime
from typing import Dict, Optional

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
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
    exam_format = Column(Text, nullable=True)
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


class MockExam(Base):
    """Mock exam model for organizing exam questions into complete exams."""

    __tablename__ = "mock_exams"

    id = Column(String, primary_key=True, index=True)
    class_id = Column(
        String, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title = Column(String, nullable=True)  # Exam title/header
    instructions = Column(Text, nullable=True)  # Exam instructions
    exam_format = Column(Text, nullable=True)  # Format template used
    weighting_rules = Column(JSON, nullable=True, default=dict)  # Weighting configuration
    exam_metadata = Column(JSON, nullable=True, default=dict)  # Additional metadata
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
        "Question", back_populates="mock_exam", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<MockExam(id={self.id}, class_id={self.class_id})>"


class Question(Base):
    """Question model for storing exam questions."""

    __tablename__ = "questions"

    id = Column(String, primary_key=True, index=True)
    class_id = Column(
        String, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    mock_exam_id = Column(
        String, ForeignKey("mock_exams.id", ondelete="CASCADE"), nullable=True, index=True
    )  # Link to mock exam if part of one
    question_text = Column(Text, nullable=False)
    solution = Column(Text, nullable=True)
    question_metadata = Column(
        "metadata", JSON, nullable=True, default=dict
    )  # Using "metadata" as column name but question_metadata as attribute
    source_image = Column(String, nullable=True)  # Path to original image if available
    # Tagging fields
    slideset = Column(String, nullable=True, index=True)  # Slideset name
    slide = Column(Integer, nullable=True)  # Slide number within slideset
    topic = Column(String, nullable=True, index=True)  # Topic name
    user_confidence = Column(
        String, nullable=True, index=True
    )  # 'confident', 'uncertain', 'not_confident'
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    class_obj = relationship("Class", back_populates="questions")
    mock_exam = relationship("MockExam", back_populates="questions")

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
