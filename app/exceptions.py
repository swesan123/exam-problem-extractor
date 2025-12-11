"""Custom exception classes."""

from typing import Any, Dict, Optional


class ExamProblemExtractorException(Exception):
    """Base exception for the application."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize exception.

        Args:
            message: Error message
            details: Additional error details
        """
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class OCRException(ExamProblemExtractorException):
    """Exception raised during OCR processing."""

    pass


class EmbeddingException(ExamProblemExtractorException):
    """Exception raised during embedding generation or storage."""

    pass


class RetrievalException(ExamProblemExtractorException):
    """Exception raised during retrieval operations."""

    pass


class GenerationException(ExamProblemExtractorException):
    """Exception raised during question generation."""

    pass


class ValidationException(ExamProblemExtractorException):
    """Exception raised during input validation."""

    pass
