"""Service for exporting questions to various file formats."""
import json
import logging
from enum import Enum
from io import BytesIO
from pathlib import Path
from typing import List, Optional

from docx import Document
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from app.db.models import Question

logger = logging.getLogger(__name__)


class ExportFormat(str, Enum):
    """Supported export formats."""

    TXT = "txt"
    PDF = "pdf"
    DOCX = "docx"
    JSON = "json"


class ExportService:
    """Service for exporting questions to files."""

    def export_to_txt(
        self, questions: List[Question], include_solutions: bool = False
    ) -> str:
        """
        Export questions to plain text format.

        Args:
            questions: List of questions to export
            include_solutions: Whether to include solutions

        Returns:
            Formatted text content
        """
        lines = []
        lines.append("=" * 80)
        lines.append("EXAM QUESTIONS")
        lines.append("=" * 80)
        lines.append("")

        for idx, question in enumerate(questions, 1):
            lines.append(f"Question {idx}")
            lines.append("-" * 80)
            lines.append(question.question_text)
            lines.append("")

            if include_solutions and question.solution:
                lines.append("Solution:")
                lines.append(question.solution)
                lines.append("")

            lines.append("")

        return "\n".join(lines)

    def export_to_json(
        self, questions: List[Question], include_solutions: bool = False
    ) -> str:
        """
        Export questions to JSON format.

        Args:
            questions: List of questions to export
            include_solutions: Whether to include solutions

        Returns:
            JSON string
        """
        data = {
            "questions": [
                {
                    "id": q.id,
                    "question_text": q.question_text,
                    "solution": q.solution if include_solutions else None,
                    "metadata": q.question_metadata or {},
                    "created_at": q.created_at.isoformat() if q.created_at else None,
                }
                for q in questions
            ],
            "total": len(questions),
        }
        return json.dumps(data, indent=2, ensure_ascii=False)

    def export_to_pdf(
        self, questions: List[Question], include_solutions: bool = False
    ) -> BytesIO:
        """
        Export questions to PDF format.

        Args:
            questions: List of questions to export
            include_solutions: Whether to include solutions

        Returns:
            BytesIO buffer containing PDF content
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()

        # Title
        title = Paragraph("EXAM QUESTIONS", styles["Title"])
        story.append(title)
        story.append(Spacer(1, 12))

        for idx, question in enumerate(questions, 1):
            # Question number
            q_num = Paragraph(f"Question {idx}", styles["Heading2"])
            story.append(q_num)
            story.append(Spacer(1, 6))

            # Question text
            q_text = Paragraph(question.question_text.replace("\n", "<br/>"), styles["Normal"])
            story.append(q_text)
            story.append(Spacer(1, 12))

            # Solution if included
            if include_solutions and question.solution:
                sol_title = Paragraph("Solution:", styles["Heading3"])
                story.append(sol_title)
                story.append(Spacer(1, 6))
                sol_text = Paragraph(question.solution.replace("\n", "<br/>"), styles["Normal"])
                story.append(sol_text)
                story.append(Spacer(1, 12))

            story.append(Spacer(1, 12))

        doc.build(story)
        buffer.seek(0)
        return buffer

    def export_to_docx(
        self, questions: List[Question], include_solutions: bool = False
    ) -> BytesIO:
        """
        Export questions to DOCX format.

        Args:
            questions: List of questions to export
            include_solutions: Whether to include solutions

        Returns:
            BytesIO buffer containing DOCX content
        """
        doc = Document()
        doc.add_heading("EXAM QUESTIONS", 0)

        for idx, question in enumerate(questions, 1):
            doc.add_heading(f"Question {idx}", level=1)
            doc.add_paragraph(question.question_text)

            if include_solutions and question.solution:
                doc.add_heading("Solution:", level=2)
                doc.add_paragraph(question.solution)

            doc.add_paragraph("")  # Empty line between questions

        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer

    def export_questions(
        self,
        questions: List[Question],
        format: ExportFormat,
        include_solutions: bool = False,
    ) -> tuple[bytes, str, str]:
        """
        Export questions to specified format.

        Args:
            questions: List of questions to export
            format: Export format (txt, pdf, docx, json)
            include_solutions: Whether to include solutions

        Returns:
            Tuple of (content bytes, content type, file extension)

        Raises:
            ValueError: If format is not supported
        """
        if format == ExportFormat.TXT:
            content = self.export_to_txt(questions, include_solutions).encode("utf-8")
            return content, "text/plain", "txt"
        elif format == ExportFormat.JSON:
            content = self.export_to_json(questions, include_solutions).encode("utf-8")
            return content, "application/json", "json"
        elif format == ExportFormat.PDF:
            buffer = self.export_to_pdf(questions, include_solutions)
            return buffer.read(), "application/pdf", "pdf"
        elif format == ExportFormat.DOCX:
            buffer = self.export_to_docx(questions, include_solutions)
            return buffer.read(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "docx"
        else:
            raise ValueError(f"Unsupported export format: {format}")

