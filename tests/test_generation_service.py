"""Unit tests for generation service."""

from unittest.mock import MagicMock

import pytest

from app.models.retrieval_models import RetrievedChunk
from app.services.generation_service import GenerationService


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client."""
    client = MagicMock()
    client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="Generated exam question"))],
        usage=MagicMock(total_tokens=100),
    )
    return client


def test_generate_question(mock_openai_client):
    """Test question generation."""
    service = GenerationService(openai_client=mock_openai_client)
    result = service.generate_question("OCR text", ["Context 1", "Context 2"])
    assert result == "Generated exam question"
    mock_openai_client.chat.completions.create.assert_called_once()


def test_generate_with_metadata(mock_openai_client):
    """Test question generation with metadata."""
    service = GenerationService(openai_client=mock_openai_client)
    result = service.generate_with_metadata("OCR text", ["Context 1"])
    assert "question" in result
    assert "metadata" in result
    assert result["metadata"]["tokens_used"] == 100


class TestGenerateWithReferenceTypes:
    """Test generation service with separate assessment/lecture contexts."""

    @pytest.fixture
    def assessment_chunks(self):
        """Create sample assessment chunks."""
        return [
            RetrievedChunk(
                text="Assessment question 1",
                score=0.9,
                metadata={"source_file": "exam_1.pdf", "reference_type": "assessment"},
                chunk_id="chunk_1",
            ),
            RetrievedChunk(
                text="Assessment question 2",
                score=0.8,
                metadata={"source_file": "exam_2.pdf", "reference_type": "assessment"},
                chunk_id="chunk_2",
            ),
        ]

    @pytest.fixture
    def lecture_chunks(self):
        """Create sample lecture chunks."""
        return [
            RetrievedChunk(
                text="Lecture content 1",
                score=0.85,
                metadata={"source_file": "lecture_1.pdf", "reference_type": "lecture"},
                chunk_id="chunk_3",
            ),
            RetrievedChunk(
                text="Lecture content 2",
                score=0.75,
                metadata={"source_file": "lecture_2.pdf", "reference_type": "lecture"},
                chunk_id="chunk_4",
            ),
        ]

    def test_generate_with_reference_types_assessment_only(
        self, mock_openai_client, assessment_chunks
    ):
        """Test generate_with_reference_types with assessment chunks only."""
        mock_openai_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Generated question"))],
            usage=MagicMock(total_tokens=100),
        )

        service = GenerationService(openai_client=mock_openai_client)
        result = service.generate_with_reference_types(
            "OCR text", assessment_chunks, []
        )

        assert "question" in result
        assert "metadata" in result
        assert result["metadata"]["assessment_count"] == 2
        assert result["metadata"]["lecture_count"] == 0

        # Verify prompt includes assessment examples
        call_args = mock_openai_client.chat.completions.create.call_args
        user_prompt = call_args.kwargs["messages"][1]["content"]
        assert "Assessment Examples" in user_prompt
        assert "exam_1.pdf" in result["question"] or "exam_2.pdf" in result["question"]

    def test_generate_with_reference_types_lecture_only(
        self, mock_openai_client, lecture_chunks
    ):
        """Test generate_with_reference_types with lecture chunks only."""
        mock_openai_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Generated question"))],
            usage=MagicMock(total_tokens=100),
        )

        service = GenerationService(openai_client=mock_openai_client)
        result = service.generate_with_reference_types("OCR text", [], lecture_chunks)

        assert "question" in result
        assert "metadata" in result
        assert result["metadata"]["assessment_count"] == 0
        assert result["metadata"]["lecture_count"] == 2

        # Verify prompt includes lecture examples
        call_args = mock_openai_client.chat.completions.create.call_args
        user_prompt = call_args.kwargs["messages"][1]["content"]
        assert "Lecture Examples" in user_prompt
        assert "lecture_1.pdf" in result["question"] or "lecture_2.pdf" in result[
            "question"
        ]

    def test_generate_with_reference_types_both(
        self, mock_openai_client, assessment_chunks, lecture_chunks
    ):
        """Test generate_with_reference_types with both assessment and lecture chunks."""
        mock_openai_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Generated question"))],
            usage=MagicMock(total_tokens=100),
        )

        service = GenerationService(openai_client=mock_openai_client)
        result = service.generate_with_reference_types(
            "OCR text", assessment_chunks, lecture_chunks
        )

        assert "question" in result
        assert "metadata" in result
        assert result["metadata"]["assessment_count"] == 2
        assert result["metadata"]["lecture_count"] == 2

        # Verify prompt includes both sections
        call_args = mock_openai_client.chat.completions.create.call_args
        user_prompt = call_args.kwargs["messages"][1]["content"]
        assert "Assessment Examples" in user_prompt
        assert "Lecture Examples" in user_prompt

    def test_generate_with_reference_types_empty_chunks(self, mock_openai_client):
        """Test generate_with_reference_types with empty chunks (fallback)."""
        mock_openai_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Generated question"))],
            usage=MagicMock(total_tokens=100),
        )

        service = GenerationService(openai_client=mock_openai_client)
        result = service.generate_with_reference_types("OCR text", [], [])

        assert "question" in result
        assert "metadata" in result
        assert result["metadata"]["assessment_count"] == 0
        assert result["metadata"]["lecture_count"] == 0

    def test_citations_included_in_generated_question(
        self, mock_openai_client, assessment_chunks, lecture_chunks
    ):
        """Test citations included in generated question text."""
        mock_openai_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Generated question"))],
            usage=MagicMock(total_tokens=100),
        )

        service = GenerationService(openai_client=mock_openai_client)
        result = service.generate_with_reference_types(
            "OCR text", assessment_chunks, lecture_chunks
        )

        # Verify references section is appended
        assert "References:" in result["question"]
        assert "exam_1.pdf" in result["question"] or "exam_2.pdf" in result["question"]
        assert "lecture_1.pdf" in result["question"] or "lecture_2.pdf" in result[
            "question"
        ]

    def test_assessment_filenames_appear_in_citations(
        self, mock_openai_client, assessment_chunks
    ):
        """Test assessment filenames appear in citations."""
        mock_openai_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Generated question"))],
            usage=MagicMock(total_tokens=100),
        )

        service = GenerationService(openai_client=mock_openai_client)
        result = service.generate_with_reference_types(
            "OCR text", assessment_chunks, []
        )

        assert "exam_1.pdf" in result["question"] or "exam_2.pdf" in result["question"]
        assert "Structure/Format:" in result["question"]

    def test_lecture_filenames_appear_in_citations(
        self, mock_openai_client, lecture_chunks
    ):
        """Test lecture filenames appear in citations."""
        mock_openai_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Generated question"))],
            usage=MagicMock(total_tokens=100),
        )

        service = GenerationService(openai_client=mock_openai_client)
        result = service.generate_with_reference_types("OCR text", [], lecture_chunks)

        assert "lecture_1.pdf" in result["question"] or "lecture_2.pdf" in result[
            "question"
        ]
        assert "Content:" in result["question"]

    def test_generate_with_reference_types_and_solution_includes_citations(
        self, mock_openai_client, assessment_chunks, lecture_chunks
    ):
        """Test generate_with_reference_types_and_solution includes citations."""
        mock_openai_client.chat.completions.create.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content="Question text\n\nSolution:\nSolution text"
                    )
                )
            ],
            usage=MagicMock(total_tokens=200),
        )

        service = GenerationService(openai_client=mock_openai_client)
        result = service.generate_with_reference_types_and_solution(
            "OCR text", assessment_chunks, lecture_chunks
        )

        assert "question" in result
        assert "solution" in result
        assert "References:" in result["question"]

    def test_prompt_structure_separates_assessment_and_lecture_sections(
        self, mock_openai_client, assessment_chunks, lecture_chunks
    ):
        """Test prompt structure separates assessment and lecture sections."""
        mock_openai_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Generated question"))],
            usage=MagicMock(total_tokens=100),
        )

        service = GenerationService(openai_client=mock_openai_client)
        service.generate_with_reference_types(
            "OCR text", assessment_chunks, lecture_chunks
        )

        call_args = mock_openai_client.chat.completions.create.call_args
        user_prompt = call_args.kwargs["messages"][1]["content"]
        system_prompt = call_args.kwargs["messages"][0]["content"]

        # Verify structure
        assert "Assessment Examples" in user_prompt
        assert "Lecture Examples" in user_prompt
        assert "structure" in system_prompt.lower() or "format" in system_prompt.lower()
        assert "content" in system_prompt.lower()

    def test_system_prompt_includes_citation_instructions(
        self, mock_openai_client, assessment_chunks, lecture_chunks
    ):
        """Test system prompt includes citation instructions."""
        mock_openai_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Generated question"))],
            usage=MagicMock(total_tokens=100),
        )

        service = GenerationService(openai_client=mock_openai_client)
        service.generate_with_reference_types(
            "OCR text", assessment_chunks, lecture_chunks
        )

        call_args = mock_openai_client.chat.completions.create.call_args
        system_prompt = call_args.kwargs["messages"][0]["content"]

        assert "References:" in system_prompt
        assert "filename" in system_prompt.lower()

    def test_metadata_includes_assessment_and_lecture_counts(
        self, mock_openai_client, assessment_chunks, lecture_chunks
    ):
        """Test metadata includes assessment_count and lecture_count."""
        mock_openai_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Generated question"))],
            usage=MagicMock(total_tokens=100),
        )

        service = GenerationService(openai_client=mock_openai_client)
        result = service.generate_with_reference_types(
            "OCR text", assessment_chunks, lecture_chunks
        )

        assert "metadata" in result
        assert "assessment_count" in result["metadata"]
        assert "lecture_count" in result["metadata"]
        assert result["metadata"]["assessment_count"] == 2
        assert result["metadata"]["lecture_count"] == 2
