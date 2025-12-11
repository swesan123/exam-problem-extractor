"""Generation service for creating exam-style questions using OpenAI GPT."""

from typing import Dict, List, Optional

from openai import OpenAI

from app.config import settings


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
