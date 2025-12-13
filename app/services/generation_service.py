"""Generation service for creating exam-style questions using OpenAI GPT."""

from typing import Dict, List, Optional

from openai import OpenAI

from app.config import settings
from app.models.retrieval_models import RetrievedChunk


class GenerationService:
    """Service for generating exam-style questions."""

    def __init__(self, openai_client: Optional[OpenAI] = None):
        """
        Initialize generation service.

        Args:
            openai_client: OpenAI client instance
        """
        self.client = openai_client or OpenAI(api_key=settings.openai_api_key)
        self.model = settings.generation_model

    def generate_question(self, ocr_text: str, retrieved_context: List[str]) -> str:
        """
        Generate formatted exam question.

        Args:
            ocr_text: Extracted text from OCR
            retrieved_context: List of similar exam questions for context

        Returns:
            Generated exam-style question

        Raises:
            Exception: If generation fails
        """
        result = self.generate_with_metadata(ocr_text, retrieved_context)
        return result["question"]

    def generate_with_metadata(
        self, ocr_text: str, retrieved_context: List[str]
    ) -> Dict:
        """
        Generate question with metadata.

        Args:
            ocr_text: Extracted text from OCR
            retrieved_context: List of similar exam questions for context

        Returns:
            Dictionary with question and metadata

        Raises:
            Exception: If generation fails
        """
        # Build prompt
        system_prompt = """You are an expert at creating exam-style questions from problem statements.
Your task is to convert the given problem into a clean, well-formatted exam question.
Follow these guidelines:
- Format the question clearly and professionally
- Preserve all mathematical expressions and formulas
- Use proper exam question structure
- Do not include solutions unless explicitly requested
- Maintain the original problem's intent and difficulty level"""

        context_text = ""
        if retrieved_context:
            context_text = "\n\nSimilar exam questions for reference:\n"
            for i, ctx in enumerate(retrieved_context[:5], 1):  # Limit to 5 examples
                context_text += f"{i}. {ctx}\n"

        user_prompt = f"""Convert the following problem into an exam-style question:

{ocr_text}
{context_text}

Generate a clean, well-formatted exam question based on the problem above."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=2048,
            )

            question = response.choices[0].message.content or ""

            # Extract metadata
            metadata = {
                "model": self.model,
                "tokens_used": response.usage.total_tokens if response.usage else 0,
                "retrieved_count": len(retrieved_context),
            }

            return {
                "question": question.strip(),
                "metadata": metadata,
            }

        except Exception as e:
            raise Exception(f"Question generation failed: {str(e)}") from e

    def generate_with_solution(
        self, ocr_text: str, retrieved_context: List[str]
    ) -> Dict:
        """
        Generate question with solution included.

        Args:
            ocr_text: Extracted text from OCR
            retrieved_context: List of similar exam questions for context

        Returns:
            Dictionary with question, solution, and metadata
        """
        system_prompt = """You are an expert at creating exam-style questions with solutions.
Your task is to convert the given problem into a clean, well-formatted exam question with a complete solution.
Follow these guidelines:
- Format the question clearly and professionally
- Provide a complete, step-by-step solution
- Preserve all mathematical expressions and formulas
- Use proper exam question structure"""

        context_text = ""
        if retrieved_context:
            context_text = "\n\nSimilar exam questions for reference:\n"
            for i, ctx in enumerate(retrieved_context[:5], 1):
                context_text += f"{i}. {ctx}\n"

        user_prompt = f"""Convert the following problem into an exam-style question with solution:

{ocr_text}
{context_text}

Generate a clean, well-formatted exam question with a complete solution based on the problem above."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=4096,
            )

            content = response.choices[0].message.content or ""

            # Try to separate question and solution
            # This is a simple heuristic - in production, you might want more sophisticated parsing
            parts = content.split("\n\nSolution:", 1)
            if len(parts) == 2:
                question = parts[0].replace("Question:", "").strip()
                solution = parts[1].strip()
            else:
                question = content
                solution = ""

            metadata = {
                "model": self.model,
                "tokens_used": response.usage.total_tokens if response.usage else 0,
                "retrieved_count": len(retrieved_context),
            }

            return {
                "question": question,
                "solution": solution,
                "metadata": metadata,
            }

        except Exception as e:
            raise Exception(
                f"Question generation with solution failed: {str(e)}"
            ) from e

    def generate_with_reference_types(
        self,
        ocr_text: str,
        assessment_chunks: List[RetrievedChunk],
        lecture_chunks: List[RetrievedChunk],
    ) -> Dict:
        """
        Generate question with separate assessment and lecture reference contexts.

        Args:
            ocr_text: Extracted text from OCR
            assessment_chunks: List of RetrievedChunk objects for structure/format examples
            lecture_chunks: List of RetrievedChunk objects for content/topic examples

        Returns:
            Dictionary with question and metadata
        """
        # Build prompt with explicit sections for assessment and lecture references
        system_prompt = """You are an expert at creating exam-style questions from problem statements.
Your task is to convert the given problem into a clean, well-formatted exam question.
Follow these guidelines:
- Use assessment examples to understand the question structure, format, and style
- Use lecture examples to ensure content accuracy and topic coverage
- Format the question clearly and professionally
- Preserve all mathematical expressions and formulas
- Use proper exam question structure
- Do not include solutions unless explicitly requested
- Maintain the original problem's intent and difficulty level
- At the end of the generated question, include a "References:" section listing:
  * Assessment references used for structure/format: [filename1, filename2, ...]
  * Lecture references used for content: [filename3, filename4, ...]"""

        # Build assessment examples section
        assessment_text = ""
        assessment_files = []
        if assessment_chunks:
            assessment_text = "\n\nAssessment Examples (for structure/format):\n"
            for i, chunk in enumerate(assessment_chunks[:5], 1):  # Limit to 5 examples
                assessment_text += f"{i}. {chunk.text}\n"
                source_file = chunk.metadata.get("source_file", "unknown")
                if source_file not in assessment_files:
                    assessment_files.append(source_file)

        # Build lecture examples section
        lecture_text = ""
        lecture_files = []
        if lecture_chunks:
            lecture_text = "\n\nLecture Examples (for content/topics):\n"
            for i, chunk in enumerate(lecture_chunks[:5], 1):  # Limit to 5 examples
                lecture_text += f"{i}. {chunk.text}\n"
                source_file = chunk.metadata.get("source_file", "unknown")
                if source_file not in lecture_files:
                    lecture_files.append(source_file)

        user_prompt = f"""Convert the following problem into an exam-style question:

{ocr_text}
{assessment_text}{lecture_text}

Generate a clean, well-formatted exam question based on the problem above.
Use the assessment examples to match the structure and format.
Use the lecture examples to ensure content accuracy."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=2048,
            )

            question = response.choices[0].message.content or ""

            # Ensure references are included (append if not already present)
            if assessment_files or lecture_files:
                ref_section = "\n\nReferences:\n"
                if assessment_files:
                    ref_section += f"- Structure/Format: {', '.join(assessment_files)}\n"
                if lecture_files:
                    ref_section += f"- Content: {', '.join(lecture_files)}\n"
                
                # Only append if not already in question
                if "References:" not in question:
                    question += ref_section

            # Extract metadata
            metadata = {
                "model": self.model,
                "tokens_used": response.usage.total_tokens if response.usage else 0,
                "assessment_count": len(assessment_chunks),
                "lecture_count": len(lecture_chunks),
            }

            return {
                "question": question.strip(),
                "metadata": metadata,
            }

        except Exception as e:
            raise Exception(f"Question generation failed: {str(e)}") from e

    def generate_with_reference_types_and_solution(
        self,
        ocr_text: str,
        assessment_chunks: List[RetrievedChunk],
        lecture_chunks: List[RetrievedChunk],
    ) -> Dict:
        """
        Generate question with solution using separate assessment and lecture reference contexts.

        Args:
            ocr_text: Extracted text from OCR
            assessment_chunks: List of RetrievedChunk objects for structure/format examples
            lecture_chunks: List of RetrievedChunk objects for content/topic examples

        Returns:
            Dictionary with question, solution, and metadata
        """
        # Build prompt with explicit sections for assessment and lecture references
        system_prompt = """You are an expert at creating exam-style questions with solutions.
Your task is to convert the given problem into a clean, well-formatted exam question with a complete solution.
Follow these guidelines:
- Use assessment examples to understand the question structure, format, and style
- Use lecture examples to ensure content accuracy and topic coverage
- Format the question clearly and professionally
- Provide a complete, step-by-step solution
- Preserve all mathematical expressions and formulas
- Use proper exam question structure
- At the end of the generated question, include a "References:" section listing:
  * Assessment references used for structure/format: [filename1, filename2, ...]
  * Lecture references used for content: [filename3, filename4, ...]"""

        # Build assessment examples section
        assessment_text = ""
        assessment_files = []
        if assessment_chunks:
            assessment_text = "\n\nAssessment Examples (for structure/format):\n"
            for i, chunk in enumerate(assessment_chunks[:5], 1):  # Limit to 5 examples
                assessment_text += f"{i}. {chunk.text}\n"
                source_file = chunk.metadata.get("source_file", "unknown")
                if source_file not in assessment_files:
                    assessment_files.append(source_file)

        # Build lecture examples section
        lecture_text = ""
        lecture_files = []
        if lecture_chunks:
            lecture_text = "\n\nLecture Examples (for content/topics):\n"
            for i, chunk in enumerate(lecture_chunks[:5], 1):  # Limit to 5 examples
                lecture_text += f"{i}. {chunk.text}\n"
                source_file = chunk.metadata.get("source_file", "unknown")
                if source_file not in lecture_files:
                    lecture_files.append(source_file)

        user_prompt = f"""Convert the following problem into an exam-style question with solution:

{ocr_text}
{assessment_text}{lecture_text}

Generate a clean, well-formatted exam question with a complete solution based on the problem above.
Use the assessment examples to match the structure and format.
Use the lecture examples to ensure content accuracy."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=4096,
            )

            content = response.choices[0].message.content or ""

            # Try to separate question and solution
            parts = content.split("\n\nSolution:", 1)
            if len(parts) == 2:
                question = parts[0].replace("Question:", "").strip()
                solution = parts[1].strip()
            else:
                question = content
                solution = ""

            # Ensure references are included (append if not already present)
            if assessment_files or lecture_files:
                ref_section = "\n\nReferences:\n"
                if assessment_files:
                    ref_section += f"- Structure/Format: {', '.join(assessment_files)}\n"
                if lecture_files:
                    ref_section += f"- Content: {', '.join(lecture_files)}\n"
                
                # Only append if not already in question
                if "References:" not in question:
                    question += ref_section

            metadata = {
                "model": self.model,
                "tokens_used": response.usage.total_tokens if response.usage else 0,
                "assessment_count": len(assessment_chunks),
                "lecture_count": len(lecture_chunks),
            }

            return {
                "question": question,
                "solution": solution,
                "metadata": metadata,
            }

        except Exception as e:
            raise Exception(
                f"Question generation with solution failed: {str(e)}"
            ) from e
