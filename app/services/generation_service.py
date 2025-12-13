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
        references_used: Optional[Dict[str, List[Dict]]] = None,
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
- Use assessment examples to understand the question structure, format, and style, as well as for content when relevant
- Use lecture examples to ensure content accuracy and topic coverage
- IMPORTANT: Only use information that is actually present in the provided reference examples
- If the reference examples are not relevant to the problem, generate the question based solely on the problem statement without relying on the references
- Do NOT fabricate or infer information that is not in the provided references
- Format the question clearly and professionally
- Preserve all mathematical expressions and formulas
- Use proper exam question structure
- Do not include solutions unless explicitly requested
- At the end of the generated question, include a "References:" section listing:
  * Assessment references used for structure/format and content: [filename1, filename2, ...] (only list if actually used)
  * Lecture references used for content: [filename3, filename4, ...] (only list if actually used)
- If no references were relevant or used, omit the References section entirely
- Maintain the original problem's intent and difficulty level"""

        # Build assessment examples section
        assessment_text = ""
        assessment_files = []
        if assessment_chunks:
            assessment_text = "\n\nAssessment Examples (for structure/format and content):\n"
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
Use the assessment examples to match the structure, format, and content when relevant.
Use the lecture examples to ensure content accuracy and topic coverage."""

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

            # Only include references if they were actually used (filtered by threshold)
            # The model should have already included references if it used them, but we ensure accuracy
            # Remove any existing references section first
            ref_markers = ["\n\n**References:**", "\n**References:**", "**References:**", "\n\nReferences:", "\nReferences:", "References:"]
            has_refs_section = False
            for marker in ref_markers:
                if marker in question:
                    question = question.split(marker)[0].strip()
                    has_refs_section = True
                    break
            
            # Only add references if we have files that passed the similarity threshold
            # Note: assessment_files and lecture_files come from references_used which includes all,
            # but we only want to list those that were actually used (passed threshold)
            # The model should handle this, but we can add them if the model didn't
            if (assessment_files or lecture_files) and not has_refs_section:
                ref_section = "\n\n**References:**\n"
                if assessment_files:
                    ref_section += f"- Assessment references used for structure/format and content: [{', '.join(assessment_files)}]\n"
                if lecture_files:
                    ref_section += f"- Lecture references used for content: [{', '.join(lecture_files)}]\n"
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
        references_used: Optional[Dict[str, List[Dict]]] = None,
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
- IMPORTANT: Only use information that is actually present in the provided reference examples
- If the reference examples are not relevant to the problem, generate the question based solely on the problem statement without relying on the references
- Do NOT fabricate or infer information that is not in the provided references
- Format the question clearly and professionally
- Provide a complete, step-by-step solution
- Preserve all mathematical expressions and formulas
- Use proper exam question structure
- At the end of the generated question, include a "References:" section listing:
  * Assessment references used for structure/format: [filename1, filename2, ...] (only list if actually used)
  * Lecture references used for content: [filename3, filename4, ...] (only list if actually used)
- If no references were relevant or used, omit the References section entirely"""

        # Build assessment examples section
        assessment_text = ""
        if assessment_chunks:
            assessment_text = "\n\nAssessment Examples (for structure/format and content):\n"
            for i, chunk in enumerate(assessment_chunks[:5], 1):  # Limit to 5 examples
                assessment_text += f"{i}. {chunk.text}\n"
        
        # Get filenames from references_used if provided (more accurate)
        assessment_files = []
        if references_used and "assessment" in references_used:
            assessment_files = [
                ref.get("source_file", "unknown") 
                for ref in references_used["assessment"]
            ]
            # Remove duplicates while preserving order
            seen = set()
            assessment_files = [f for f in assessment_files if f not in seen and not seen.add(f)]
        else:
            # Fallback to extracting from chunks
            for chunk in assessment_chunks:
                source_file = chunk.metadata.get("source_file") or chunk.metadata.get("original_filename") or "unknown"
                if source_file not in assessment_files:
                    assessment_files.append(source_file)

        # Build lecture examples section
        lecture_text = ""
        if lecture_chunks:
            lecture_text = "\n\nLecture Examples (for content/topics):\n"
            for i, chunk in enumerate(lecture_chunks[:5], 1):  # Limit to 5 examples
                lecture_text += f"{i}. {chunk.text}\n"
        
        # Get filenames from references_used if provided (more accurate)
        lecture_files = []
        if references_used and "lecture" in references_used:
            lecture_files = [
                ref.get("source_file", "unknown") 
                for ref in references_used["lecture"]
            ]
            # Remove duplicates while preserving order
            seen = set()
            lecture_files = [f for f in lecture_files if f not in seen and not seen.add(f)]
        else:
            # Fallback to extracting from chunks
            for chunk in lecture_chunks:
                source_file = chunk.metadata.get("source_file") or chunk.metadata.get("original_filename") or "unknown"
                if source_file not in lecture_files:
                    lecture_files.append(source_file)

        user_prompt = f"""Convert the following problem into an exam-style question with solution:

{ocr_text}
{assessment_text}{lecture_text}

Generate a clean, well-formatted exam question with a complete solution based on the problem above.
Use the assessment examples to match the structure, format, and content when relevant.
Use the lecture examples to ensure content accuracy and topic coverage."""

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

            # Ensure references are included with accurate filenames in question
            if assessment_files or lecture_files:
                ref_section = "\n\n**References:**\n"
                if assessment_files:
                    ref_section += f"- Assessment references used for structure/format and content: [{', '.join(assessment_files)}]\n"
                if lecture_files:
                    ref_section += f"- Lecture references used for content: [{', '.join(lecture_files)}]\n"
                
                # Remove any existing references section and add accurate one
                ref_markers = ["\n\n**References:**", "\n**References:**", "**References:**", "\n\nReferences:", "\nReferences:", "References:"]
                for marker in ref_markers:
                    if marker in question:
                        question = question.split(marker)[0].strip()
                        break
                
                # Append accurate references to question
                question += ref_section
                
                # Remove references from solution if present
                for marker in ref_markers:
                    if marker in solution:
                        solution = solution.split(marker)[0].strip()
                        break

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
