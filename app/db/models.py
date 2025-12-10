"""SQLAlchemy database models for classes and questions."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.sqlite import UUID

from app.db.database import Base


class Class(Base):
    """Class model for organizing exam questions."""
    
    __tablename__ = "classes"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    subject = Column(String, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationship to questions
    questions = relationship("Question", back_populates="class_obj", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Class(id={self.id}, name={self.name})>"


class Question(Base):
    """Question model for storing exam questions."""
    
    __tablename__ = "questions"
    
    id = Column(String, primary_key=True, index=True)
    class_id = Column(String, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True)
    question_text = Column(Text, nullable=False)
    solution = Column(Text, nullable=True)
    metadata = Column(JSON, nullable=True, default=dict)
    source_image = Column(String, nullable=True)  # Path to original image if available
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationship to class
    class_obj = relationship("Class", back_populates="questions")
    
    def __repr__(self):
        return f"<Question(id={self.id}, class_id={self.class_id})>"

