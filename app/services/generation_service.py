"""Generation service for creating exam-style questions using OpenAI GPT."""

from typing import Dict, List, Optional

from openai import OpenAI

from app.config import settings
from app.models.retrieval_models import RetrievedChunk
from app.utils.latex_converter import convert_to_latex


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

            # Apply LaTeX conversion
            question = convert_to_latex(question.strip())

            # Extract metadata
            metadata = {
                "model": self.model,
                "tokens_used": response.usage.total_tokens if response.usage else 0,
                "retrieved_count": len(retrieved_context),
            }

            return {
                "question": question,
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

            # Apply LaTeX conversion
            question = convert_to_latex(question)
            solution = convert_to_latex(solution)

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

            # Apply LaTeX conversion
            question = convert_to_latex(question.strip())

            # Extract metadata
            metadata = {
                "model": self.model,
                "tokens_used": response.usage.total_tokens if response.usage else 0,
                "assessment_count": len(assessment_chunks),
                "lecture_count": len(lecture_chunks),
            }

            return {
                "question": question,
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

            # Apply LaTeX conversion
            question = convert_to_latex(question)
            solution = convert_to_latex(solution)

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

    def generate_coverage_batch(
        self,
        class_id: str,
        question_count: int,
        assessment_chunks: List[RetrievedChunk],
        lecture_chunks: List[RetrievedChunk],
        references_used: Optional[Dict[str, List[Dict]]] = None,
    ) -> Dict:
        """
        Generate multiple questions covering different topics from references.

        Args:
            class_id: Class ID for context
            question_count: Number of questions to generate
            assessment_chunks: List of RetrievedChunk objects for structure/format examples
            lecture_chunks: List of RetrievedChunk objects for content/topic examples
            references_used: Optional dict of references used

        Returns:
            Dictionary with list of questions and metadata
        """
        # Retrieve diverse chunks across all references
        # Group chunks by topic/similarity to ensure coverage
        all_chunks = assessment_chunks + lecture_chunks
        
        # Select diverse chunks (simple approach: take chunks with different scores/sources)
        # In a more sophisticated implementation, you might cluster by topic
        selected_chunks = []
        seen_sources = set()
        
        # First pass: get one chunk from each source
        for chunk in all_chunks:
            source = chunk.metadata.get("source_file", "unknown")
            if source not in seen_sources:
                selected_chunks.append(chunk)
                seen_sources.add(source)
                if len(selected_chunks) >= question_count:
                    break
        
        # Second pass: fill remaining slots with diverse chunks
        for chunk in all_chunks:
            if len(selected_chunks) >= question_count:
                break
            if chunk not in selected_chunks:
                selected_chunks.append(chunk)

        # Generate questions for each selected chunk
        questions = []
        total_tokens = 0
        
        for i, chunk in enumerate(selected_chunks[:question_count], 1):
            # Use chunk text as OCR text for generation
            ocr_text = f"Generate a question based on this content:\n\n{chunk.text}"
            
            # Use other chunks as context
            context_chunks = [c for c in selected_chunks if c != chunk][:3]
            
            # Generate question
            result = self.generate_with_reference_types(
                ocr_text,
                [c for c in context_chunks if c.metadata.get("reference_type") == "assessment"],
                [c for c in context_chunks if c.metadata.get("reference_type") == "lecture"],
                references_used,
            )
            
            questions.append(result["question"])
            total_tokens += result["metadata"].get("tokens_used", 0)

        metadata = {
            "model": self.model,
            "tokens_used": total_tokens,
            "question_count": len(questions),
            "assessment_count": len(assessment_chunks),
            "lecture_count": len(lecture_chunks),
        }

        return {
            "questions": questions,
            "metadata": metadata,
        }

    def generate_mock_exam(
        self,
        exam_format: str,
        class_id: str,
        assessment_chunks: List[RetrievedChunk],
        lecture_chunks: List[RetrievedChunk],
        references_used: Optional[Dict[str, List[Dict]]] = None,
        include_solution: bool = False,
    ) -> Dict:
        """
        Generate complete mock exam following exam structure.

        Args:
            exam_format: Exam format template (e.g., "5 multiple choice, 3 short answer, 2 long answer")
            class_id: Class ID for context
            assessment_chunks: List of RetrievedChunk objects for structure/format examples
            lecture_chunks: List of RetrievedChunk objects for content/topic examples
            references_used: Optional dict of references used

        Returns:
            Dictionary with formatted exam document and metadata
        """
        # Parse exam format to extract question types and counts
        # Simple parsing - can be enhanced
        question_specs = self._parse_exam_format(exam_format)
        
        system_prompt = """You are an expert at creating complete exam documents.
Your task is to generate a full exam following the specified structure.
Follow these guidelines:
- Use assessment examples to understand the question structure, format, and style
- Use lecture examples to ensure content accuracy and MAXIMUM topic coverage
- IMPORTANT: Maximize coverage across all provided reference materials - try to incorporate content from as many different sources as possible
- Format the exam professionally with clear sections
- Number all questions sequentially
- Include point values if specified
- Preserve all mathematical expressions and formulas in LaTeX format
- Ensure questions cover diverse topics from the provided references to maximize overall coverage"""
        
        if include_solution:
            system_prompt += "\n- Include detailed solutions for all questions after each question or in a separate solutions section"
        else:
            system_prompt += "\n- Do not include solutions unless explicitly requested"

        # Build assessment examples section - use more chunks for better coverage
        assessment_text = ""
        if assessment_chunks:
            assessment_text = "\n\nAssessment Examples (for structure/format and content - use diverse examples to maximize coverage):\n"
            # Use up to 10 chunks for better coverage
            for i, chunk in enumerate(assessment_chunks[:10], 1):
                assessment_text += f"{i}. {chunk.text}\n"

        # Build lecture examples section - use more chunks for better coverage
        lecture_text = ""
        if lecture_chunks:
            lecture_text = "\n\nLecture Examples (for content/topics - use diverse examples to maximize coverage):\n"
            # Use up to 10 chunks for better coverage
            for i, chunk in enumerate(lecture_chunks[:10], 1):
                lecture_text += f"{i}. {chunk.text}\n"

        # Build format specification
        total_questions = sum(spec['count'] for spec in question_specs)
        format_spec = f"\n\nExam Format Requirements (TOTAL: {total_questions} questions):\n"
        for spec in question_specs:
            format_spec += f"- {spec['count']} {spec['type']} question(s)"
            if spec.get('points'):
                format_spec += f" ({spec['points']} points each)"
            format_spec += "\n"
        format_spec += f"\nYou MUST generate exactly {total_questions} questions total. Number them sequentially from 1 to {total_questions}.\n"

        solution_instruction = "\n\nIMPORTANT: You MUST include detailed solutions for ALL questions. Format each solution clearly after its corresponding question, or provide a separate solutions section at the end." if include_solution else ""
        user_prompt = f"""Generate a complete exam document following this structure:

{format_spec}
{assessment_text}{lecture_text}

Generate a well-formatted exam with all questions numbered and organized by type.
Include a header with exam title and instructions.
Each question must be clearly numbered (1., 2., 3., etc.) and separated from other questions.
{solution_instruction}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=8192,  # Larger for full exam
            )

            exam_content = response.choices[0].message.content or ""

            # Apply LaTeX conversion
            exam_content = convert_to_latex(exam_content)

            # Split into individual questions (simple heuristic)
            # In production, you might want more sophisticated parsing
            questions = self._split_exam_into_questions(exam_content)

            metadata = {
                "model": self.model,
                "tokens_used": response.usage.total_tokens if response.usage else 0,
                "assessment_count": len(assessment_chunks),
                "lecture_count": len(lecture_chunks),
                "question_count": len(questions),
            }

            return {
                "questions": questions,
                "exam_content": exam_content,  # Full formatted exam
                "metadata": metadata,
            }

        except Exception as e:
            raise Exception(f"Mock exam generation failed: {str(e)}") from e

    def generate_mock_exam_batch_for_coverage(
        self,
        exam_format: str,
        class_id: str,
        assessment_chunks: List[RetrievedChunk],
        lecture_chunks: List[RetrievedChunk],
        references_used: Optional[Dict[str, List[Dict]]] = None,
        include_solution: bool = False,
        coverage_threshold: float = 0.95,
        max_exams: int = 5,
    ) -> Dict:
        """
        Generate multiple mock exams iteratively until coverage threshold is reached.

        Args:
            exam_format: Exam format template
            class_id: Class ID for context
            assessment_chunks: List of RetrievedChunk objects for structure/format examples
            lecture_chunks: List of RetrievedChunk objects for content/topic examples
            references_used: Optional dict of references used
            include_solution: Whether to include solutions
            coverage_threshold: Target coverage threshold (default 0.95 = 95%)
            max_exams: Maximum number of exams to generate (default 5)

        Returns:
            Dictionary with list of exam results and overall coverage metrics
        """
        all_exams = []
        all_questions = []
        total_coverage = 0.0
        covered_chunks = set()  # Track which chunks have been covered
        
        # Create chunk map for coverage tracking
        chunk_map = {}
        all_chunks = assessment_chunks + lecture_chunks
        for chunk in all_chunks:
            chunk_map[chunk.chunk_id] = chunk
        
        for exam_num in range(max_exams):
            # Generate one mock exam
            result = self.generate_mock_exam(
                exam_format=exam_format,
                class_id=class_id,
                assessment_chunks=assessment_chunks,
                lecture_chunks=lecture_chunks,
                references_used=references_used,
                include_solution=include_solution,
            )
            
            exam_content = result.get("exam_content", "")
            questions = result.get("questions", [])
            all_exams.append(result)
            all_questions.extend(questions)
            
            # Calculate coverage for this exam and track page references
            all_question_text = " ".join(questions).lower()
            covered_in_exam = set()
            exam_page_references = []
            
            for chunk in all_chunks:
                chunk_text_lower = chunk.text.lower()
                chunk_words = set(chunk_text_lower.split())
                question_words = set(all_question_text.split())
                overlap = len(chunk_words.intersection(question_words))
                total_chunk_words = len(chunk_words)
                
                if total_chunk_words > 0:
                    word_coverage = overlap / total_chunk_words
                    if word_coverage > 0.3:  # Threshold for considering a chunk "covered"
                        covered_chunks.add(chunk.chunk_id)
                        covered_in_exam.add(chunk.chunk_id)
                        
                        # Track page reference
                        page_num = chunk.metadata.get("page")
                        source_file = chunk.metadata.get("source_file", "unknown")
                        if page_num is not None:
                            page_ref = {
                                "source_file": source_file,
                                "page": page_num,
                                "chunk_id": chunk.chunk_id,
                                "coverage": word_coverage
                            }
                            if not any(pr.get("chunk_id") == chunk.chunk_id for pr in exam_page_references):
                                exam_page_references.append(page_ref)
            
            # Store page references in exam metadata
            result["page_references"] = exam_page_references
            
            # Calculate total coverage
            if len(all_chunks) > 0:
                total_coverage = len(covered_chunks) / len(all_chunks)
            
            # Check if we've reached the threshold
            if total_coverage >= coverage_threshold:
                break
        
        # Calculate final coverage metrics
        final_metadata = {
            "model": self.model,
            "total_exams_generated": len(all_exams),
            "total_questions": len(all_questions),
            "final_coverage": total_coverage,
            "coverage_threshold": coverage_threshold,
            "assessment_count": len(assessment_chunks),
            "lecture_count": len(lecture_chunks),
        }
        
        return {
            "exams": all_exams,
            "all_questions": all_questions,
            "metadata": final_metadata,
        }

    def _parse_exam_format(self, exam_format: str) -> List[Dict]:
        """
        Parse exam format string to extract question specifications.

        Args:
            exam_format: Format string like "5 multiple choice, 3 short answer, 2 long answer"

        Returns:
            List of dicts with 'type', 'count', and optional 'points'
        """
        specs = []
        
        # Simple regex-based parsing
        import re
        
        # Pattern: number + type + optional (points)
        pattern = r'(\d+)\s+([^,\(]+?)(?:\s*\((\d+)\s*points?\s*each\))?'
        matches = re.findall(pattern, exam_format, re.IGNORECASE)
        
        for match in matches:
            count = int(match[0])
            qtype = match[1].strip().lower()
            points = int(match[2]) if match[2] else None
            
            specs.append({
                "type": qtype,
                "count": count,
                "points": points,
            })
        
        # If no matches, try simpler pattern
        if not specs:
            # Fallback: split by comma and try to extract numbers
            parts = exam_format.split(',')
            for part in parts:
                numbers = re.findall(r'\d+', part)
                if numbers:
                    count = int(numbers[0])
                    # Try to identify type
                    qtype = "question"
                    if "multiple choice" in part.lower() or "mc" in part.lower():
                        qtype = "multiple choice"
                    elif "short answer" in part.lower():
                        qtype = "short answer"
                    elif "long answer" in part.lower() or "essay" in part.lower():
                        qtype = "long answer"
                    
                    specs.append({
                        "type": qtype,
                        "count": count,
                        "points": None,
                    })
        
        return specs if specs else [{"type": "question", "count": 1, "points": None}]

    def _split_exam_into_questions(self, exam_content: str) -> List[str]:
        """
        Split exam content into individual questions.

        Args:
            exam_content: Full exam document

        Returns:
            List of individual question strings
        """
        questions = []
        import re
        import json
        
        # Try multiple patterns to split questions
        # Pattern 1: Numbered questions (1., 2., 3., etc.)
        question_pattern1 = r'(?:^|\n)(\d+[\.\)]\s+.*?)(?=(?:^|\n)\d+[\.\)]\s+|$)'
        matches1 = re.findall(question_pattern1, exam_content, re.DOTALL | re.MULTILINE)
        
        # Pattern 2: Questions with "Question 1:", "Question 2:", etc.
        question_pattern2 = r'(?:^|\n)(Question\s+\d+[:\-\.]\s+.*?)(?=(?:^|\n)Question\s+\d+[:\-\.]|$)'
        matches2 = re.findall(question_pattern2, exam_content, re.DOTALL | re.MULTILINE | re.IGNORECASE)
        
        # Pattern 3: Questions separated by "---" or similar separators
        if not matches1 and not matches2:
            parts = re.split(r'\n\s*---+\s*\n', exam_content)
            if len(parts) > 1:
                questions = [p.strip() for p in parts if p.strip() and not p.strip().lower().startswith('end of exam')]
        
        # Use the best match
        if matches1:
            questions = [m.strip() for m in matches1 if m.strip()]
        elif matches2:
            questions = [m.strip() for m in matches2 if m.strip()]
        
        # Fallback: split by double newlines if no numbered questions found
        if not questions:
            parts = exam_content.split('\n\n')
            # Filter out headers, footers, and metadata
            questions = []
            for part in parts:
                part = part.strip()
                if part and not any(skip in part.lower() for skip in ['end of exam', 'references used', 'total coverage', 'warning:']):
                    # Check if it looks like a question (has some content, not just metadata)
                    if len(part) > 20:  # Minimum question length
                        questions.append(part)
        
        return questions if questions else [exam_content]
