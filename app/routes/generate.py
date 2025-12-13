"""Generation route endpoint."""
import json
import logging
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.generation_models import GenerateResponse, ReferenceCitation
from app.models.question_models import QuestionCreate
from app.services.generation_service import GenerationService
from app.services.ocr_service import OCRService
from app.services.embedding_service import EmbeddingService
from app.services.retrieval_service import RetrievalService
from app.services.question_service import QuestionService
from app.utils.file_utils import cleanup_temp_file, save_temp_file, validate_upload_file

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generate", tags=["generation"])


@router.post("", response_model=GenerateResponse, status_code=status.HTTP_200_OK)
async def generate_question(
    request: Request,
    ocr_text: Optional[str] = Form(None),
    image_file: Optional[UploadFile] = File(None),
    retrieved_context: Optional[str] = Form(None),  # JSON string
    include_solution: bool = Form(False),
    class_id: Optional[str] = Form(None),  # Optional class ID to save question to
    mode: Optional[str] = Form("normal"),  # Generation mode: normal, mock_exam
    exam_format: Optional[str] = Form(None),  # For mock_exam mode
    max_coverage: bool = Form(False),  # For mock_exam mode: generate multiple exams until 95% coverage
    question_count: Optional[int] = Form(None),  # Number of questions for mock exam (overrides parsed count)
    weighting_rules: Optional[str] = Form(None),  # JSON string with weighting configuration (optional override)
    focus_on_uncertain: bool = Form(False),  # Focus on uncertain topics
    db: Session = Depends(get_db),
):
    """
    Generate exam question from image or text.

    Supports multiple modes:
    1. normal: Single question generation (default)
    2. mock_exam: Generate a complete mock exam with maximum coverage over references
    3. mock_exam: Generate complete mock exam following exam structure

    If class_id is provided, the generated question(s) will be automatically saved to that class.

    Args:
        request: FastAPI Request object
        ocr_text: Pre-extracted OCR text (alternative to image_file)
        image_file: Image file for OCR extraction (alternative to ocr_text)
        retrieved_context: JSON string of pre-retrieved context (optional)
        include_solution: Whether to include solution in generated question
        class_id: Optional class ID to automatically save question to
        mode: Generation mode (normal, mock_exam)
        exam_format: Exam format template for mock_exam mode
        question_count: Number of questions for mock exam (overrides parsed count from exam_format)
        weighting_rules: JSON string with weighting configuration (optional override)
        focus_on_uncertain: Focus on uncertain topics when generating mock exam
        db: Database session

    Returns:
        GenerateResponse with formatted question(s) and metadata
    """
    temp_path: Path | None = None
    processing_steps: List[str] = []

    try:
        # Validate mode
        if mode not in ["normal", "mock_exam"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="mode must be one of: normal, mock_exam",
            )
        
        # Validate mode-specific requirements
        if mode == "mock_exam":
            if not class_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="class_id is required for mock_exam mode",
                )
            
            # Get exam_format from class if not provided
            if not exam_format and class_id:
                from app.services.class_service import ClassService
                class_service = ClassService(db)
                class_obj = class_service.get_class(class_id)
                if class_obj and class_obj.exam_format:
                    exam_format = class_obj.exam_format
            
            if not exam_format:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="exam_format is required for mock_exam mode. Please set the exam format for this class first.",
                )
        
        # Validate that at least one input is provided (for normal mode)
        if mode == "normal" and not ocr_text and not image_file:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one of 'ocr_text' or 'image_file' must be provided",
            )

        # Step 1: OCR extraction (if image provided)
        if image_file:
            validate_upload_file(image_file)
            temp_path = save_temp_file(image_file)
            ocr_service = OCRService()
            
            # Handle PDF by converting pages to images first
            if image_file.content_type == "application/pdf":
                from app.utils.file_utils import convert_pdf_to_images
                image_paths = convert_pdf_to_images(temp_path)
                all_text_parts = []
                try:
                    for page_num, image_path in enumerate(image_paths, start=1):
                        text = ocr_service.extract_text(image_path)
                        page_header = f"=== Page {page_num} ===\n"
                        all_text_parts.append(page_header + text)
                    ocr_text = "\n\n".join(all_text_parts)
                finally:
                    # Clean up generated images
                    for img_path in image_paths:
                        cleanup_temp_file(img_path)
            else:
                # Handle regular image files
                ocr_text = ocr_service.extract_text(temp_path)
            
            processing_steps.append("ocr")

        # For mock_exam mode, allow empty ocr_text (it will use a default query for retrieval)
        # For normal mode, ocr_text is required
        if mode == "mock_exam" and not ocr_text:
            ocr_text = "exam questions"  # Default query for mock exam retrieval
        
        if not ocr_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OCR text extraction failed or not provided",
            )

        # Step 2: Pre-compute weighting rules for mock_exam mode (needed for retrieval)
        final_weighting_rules = None
        saved_mock_exam_ids = []
        
        if mode == "mock_exam":
            generation_service = GenerationService()  # Initialize early for weighting rules
            
            # Parse weighting_rules if provided
            parsed_weighting_rules = None
            if weighting_rules:
                try:
                    parsed_weighting_rules = json.loads(weighting_rules)
                except json.JSONDecodeError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="weighting_rules must be valid JSON",
                    )
            
            # Generate default weighting rules if not provided
            default_weighting_rules = None
            if hasattr(generation_service, '_infer_weighting_rules'):
                # Get exam_type from class if available
                exam_type = None
                if class_id:
                    from app.services.class_service import ClassService
                    class_service = ClassService(db)
                    class_obj = class_service.get_class(class_id)
                    if class_obj:
                        # Try to get exam_type from class metadata or exam_format
                        exam_type = getattr(class_obj, 'exam_type', None)
                
                default_weighting_rules = generation_service._infer_weighting_rules(
                    exam_format, exam_type
                )
            
            # Merge default and provided weighting rules (provided takes precedence)
            final_weighting_rules = default_weighting_rules or {}
            if parsed_weighting_rules:
                final_weighting_rules.update(parsed_weighting_rules)
        
        # Step 2: Retrieval (if context not provided)
        assessment_chunks = []
        lecture_chunks = []
        assessment_chunks_all = []
        lecture_chunks_all = []
        references_used = {"assessment": [], "lecture": []}
        
        if retrieved_context:
            # Parse JSON string if provided
            try:
                context_list = json.loads(retrieved_context)
                if not isinstance(context_list, list):
                    context_list = [retrieved_context]
            except json.JSONDecodeError:
                # If not valid JSON, treat as single string
                context_list = [retrieved_context]
            # For manual context, treat as generic (no reference tracking)
            assessment_chunks = []
            lecture_chunks = []
        else:
            # Perform retrieval with class-scoped filtering if class_id provided
            embedding_service = EmbeddingService()
            retrieval_service = RetrievalService(embedding_service)
            
            if class_id:
                from app.config import settings
                
                # For mock exam mode, retrieve more chunks to maximize coverage
                # For other modes, use standard retrieval
                top_k_assessment = 20 if mode == "mock_exam" else 3
                top_k_lecture = 20 if mode == "mock_exam" else 3
                
                # Retrieve assessment references separately (for structure/format)
                # Pass weighting_rules if available (for mock_exam mode)
                retrieve_kwargs_assessment = {
                    "query": ocr_text or "exam questions",
                    "top_k": top_k_assessment,
                    "class_id": class_id,
                    "reference_type": "assessment"
                }
                retrieve_kwargs_lecture = {
                    "query": ocr_text or "exam questions",
                    "top_k": top_k_lecture,
                    "class_id": class_id,
                    "reference_type": "lecture"
                }
                
                # Add weighting_rules if available (for mock_exam mode)
                if mode == "mock_exam" and final_weighting_rules:
                    retrieve_kwargs_assessment["weighting_rules"] = final_weighting_rules
                    retrieve_kwargs_lecture["weighting_rules"] = final_weighting_rules
                
                assessment_chunks_all = retrieval_service.retrieve_with_scores(**retrieve_kwargs_assessment)
                lecture_chunks_all = retrieval_service.retrieve_with_scores(**retrieve_kwargs_lecture)
                
                # For mock exam, use all chunks to maximize coverage (no threshold filtering)
                # For other modes, filter by similarity threshold
                min_threshold = settings.min_similarity_threshold
                if mode == "mock_exam":
                    # Use all chunks for maximum coverage
                    assessment_chunks = assessment_chunks_all
                    lecture_chunks = lecture_chunks_all
                else:
                    assessment_chunks = [
                        chunk for chunk in assessment_chunks_all 
                        if chunk.score >= min_threshold
                    ]
                    lecture_chunks = [
                        chunk for chunk in lecture_chunks_all 
                        if chunk.score >= min_threshold
                    ]
                
                # Build references_used tracking (include all retrieved, even if below threshold)
                # This allows us to show what was retrieved but not used
                for chunk in assessment_chunks_all:
                    references_used["assessment"].append(
                        ReferenceCitation(
                            source_file=chunk.metadata.get("source_file", "unknown"),
                            chunk_id=chunk.chunk_id,
                            reference_type=chunk.metadata.get("reference_type", "assessment"),
                            score=chunk.score,
                        )
                    )
                
                for chunk in lecture_chunks_all:
                    references_used["lecture"].append(
                        ReferenceCitation(
                            source_file=chunk.metadata.get("source_file", "unknown"),
                            chunk_id=chunk.chunk_id,
                            reference_type=chunk.metadata.get("reference_type", "lecture"),
                            score=chunk.score,
                        )
                    )
            else:
                # Fallback: retrieve without filtering (backward compatibility)
                retrieved_chunks = retrieval_service.retrieve_with_scores(ocr_text, top_k=5)
                # Try to categorize by reference_type if available
                for chunk in retrieved_chunks:
                    ref_type = chunk.metadata.get("reference_type", "").lower()
                    if ref_type == "assessment":
                        assessment_chunks.append(chunk)
                    elif ref_type == "lecture":
                        lecture_chunks.append(chunk)
                    else:
                        # If no type specified, add to both (generic)
                        if not assessment_chunks:
                            assessment_chunks.append(chunk)
                        if not lecture_chunks:
                            lecture_chunks.append(chunk)
            
            processing_steps.append("retrieval")

        # Step 3: Generation
        # Initialize generation service if not already done (for normal mode)
        if mode != "mock_exam":
            generation_service = GenerationService()
        
        # Parse weighting_rules if provided (for mock_exam mode)
        parsed_weighting_rules = None
        if mode == "mock_exam" and weighting_rules:
            try:
                parsed_weighting_rules = json.loads(weighting_rules)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="weighting_rules must be valid JSON",
                )
        
        # Generate default weighting rules if not provided (for mock_exam mode)
        # Note: This assumes Agent 2 has added _infer_weighting_rules method
        default_weighting_rules = None
        if mode == "mock_exam" and hasattr(generation_service, '_infer_weighting_rules'):
            # Get exam_type from class if available
            exam_type = None
            if class_id:
                from app.services.class_service import ClassService
                class_service = ClassService(db)
                class_obj = class_service.get_class(class_id)
                if class_obj:
                    # Try to get exam_type from class metadata or exam_format
                    exam_type = getattr(class_obj, 'exam_type', None)
            
            default_weighting_rules = generation_service._infer_weighting_rules(
                exam_format, exam_type
            )
        
        # Merge default and provided weighting rules (provided takes precedence)
        if mode == "mock_exam":
            final_weighting_rules = default_weighting_rules or {}
            if parsed_weighting_rules:
                final_weighting_rules.update(parsed_weighting_rules)
        
        # Route to appropriate generation method based on mode
        all_exams = []  # Initialize for use in saving logic
        result = None  # Initialize for use in saving logic
        
        if mode == "mock_exam":
            if max_coverage:
                # Max coverage mode: generate multiple exams until threshold reached
                batch_result = generation_service.generate_mock_exam_batch_for_coverage(
                    exam_format=exam_format,
                    class_id=class_id,
                    assessment_chunks=assessment_chunks,
                    lecture_chunks=lecture_chunks,
                    references_used=references_used,
                    include_solution=include_solution,
                    coverage_threshold=0.95,
                    max_exams=5,
                )
                all_exams = batch_result.get("exams", [])
                all_questions_list = batch_result.get("all_questions", [])
                metadata = batch_result.get("metadata", {})
                
                # Collect page references from all exams
                all_page_references = []
                for exam in all_exams:
                    exam_page_refs = exam.get("page_references", [])
                    for ref in exam_page_refs:
                        # Avoid duplicates
                        if not any(pr.get("chunk_id") == ref.get("chunk_id") for pr in all_page_references):
                            all_page_references.append(ref)
                
                # Store combined page references in metadata
                if all_page_references:
                    metadata["page_references"] = all_page_references
                
                # For max coverage, we'll save each exam as a separate entry
                # Store the full exam_content for each
                exam_contents = [exam.get("exam_content", "") for exam in all_exams]
                questions = exam_contents  # Use exam_contents as the questions list for saving
                question = None
                processing_steps.append("generation")
            else:
                # Single mock exam mode
                result = generation_service.generate_mock_exam(
                    exam_format=exam_format,
                    class_id=class_id,
                    assessment_chunks=assessment_chunks,
                    lecture_chunks=lecture_chunks,
                    references_used=references_used,
                    include_solution=include_solution,
                    question_count=question_count,
                    focus_on_uncertain=focus_on_uncertain,
                )
                exam_content = result.get("exam_content", "")
                questions_list = result.get("questions", [])
                # For single mock exam, save the full exam_content as one entry
                questions = [exam_content] if exam_content else []
                # #region agent log
                with open('/home/swesan/exam-problem-extractor/.cursor/debug.log', 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"generate.py:294","message":"Single mock exam questions set","data":{"exam_content_length":len(exam_content) if exam_content else 0,"exam_content_empty":not exam_content,"questions_count":len(questions),"questions":questions[:1] if questions else None,"timestamp":__import__('time').time()*1000},"timestamp":int(__import__('time').time()*1000)})+'\n')
                # #endregion
                question = None
                processing_steps.append("generation")
                
                # Initialize metadata from result
                metadata = result.get("metadata", {})
                
                # Calculate coverage for mock exam mode and track page references
                # Coverage is based on which references were actually used in generation
                # For mock exam, we use all retrieved chunks, so calculate coverage based on usage
                if questions_list and class_id and (assessment_chunks_all or lecture_chunks_all):
                    # Combine all question text to check coverage
                    all_question_text = " ".join(questions_list).lower()
                    
                    # Create a map of chunk_id to chunk for quick lookup
                    chunk_map = {}
                    for chunk_list in [assessment_chunks_all, lecture_chunks_all]:
                        for c in chunk_list:
                            chunk_map[c.chunk_id] = c
                    
                    # Calculate coverage for each reference and track page references
                    page_references = []
                    for ref_list in [references_used.get("assessment", []), references_used.get("lecture", [])]:
                        for ref in ref_list:
                            chunk = chunk_map.get(ref.chunk_id)
                            
                            if chunk:
                                # Check if chunk text appears in generated questions
                                chunk_text_lower = chunk.text.lower()
                                # Simple coverage: calculate word overlap
                                # Count how many unique words from chunk appear in questions
                                chunk_words = set(chunk_text_lower.split())
                                question_words = set(all_question_text.split())
                                overlap = len(chunk_words.intersection(question_words))
                                total_chunk_words = len(chunk_words)
                                
                                if total_chunk_words > 0:
                                    word_coverage = overlap / total_chunk_words
                                    # Coverage is max of word overlap or similarity score
                                    ref.coverage = max(word_coverage, ref.score)
                                    
                                    # Track page reference if chunk is significantly covered
                                    if word_coverage > 0.2:  # Threshold for considering chunk used
                                        page_num = chunk.metadata.get("page")
                                        source_file = chunk.metadata.get("source_file", "unknown")
                                        if page_num is not None:
                                            page_ref = {
                                                "source_file": source_file,
                                                "page": page_num,
                                                "chunk_id": chunk.chunk_id,
                                                "coverage": word_coverage
                                            }
                                            # Avoid duplicates
                                            if not any(pr.get("chunk_id") == chunk.chunk_id for pr in page_references):
                                                page_references.append(page_ref)
                                else:
                                    ref.coverage = ref.score
                            else:
                                # If chunk not found, use score as coverage
                                ref.coverage = ref.score
                    
                    # Store page references in metadata
                    if page_references:
                        metadata["page_references"] = page_references
                    
                    # Calculate total coverage metric (average coverage across all references)
                    all_refs = references_used.get("assessment", []) + references_used.get("lecture", [])
                    if all_refs:
                        total_coverage = sum(ref.coverage or ref.score for ref in all_refs) / len(all_refs)
                        metadata["coverage_metric"] = total_coverage
        else:
            # Normal mode - use existing logic
            # Initialize variables for normal mode
            questions = None
            question = None
            
            # Use separate assessment/lecture contexts if available, otherwise fallback
            # Note: assessment_chunks and lecture_chunks are now filtered by similarity threshold
            if (assessment_chunks or lecture_chunks):
                # Convert references_used to dict format for generation service
                # Only include references that passed the similarity threshold (those in assessment_chunks/lecture_chunks)
                refs_dict = None
                if references_used:
                    from app.config import settings
                    min_threshold = settings.min_similarity_threshold
                    
                    # Filter to only include references that passed threshold
                    filtered_assessment = [
                        ref.dict() for ref in references_used.get("assessment", [])
                        if ref.score >= min_threshold
                    ]
                    filtered_lecture = [
                        ref.dict() for ref in references_used.get("lecture", [])
                        if ref.score >= min_threshold
                    ]
                    
                    if filtered_assessment or filtered_lecture:
                        refs_dict = {
                            "assessment": filtered_assessment,
                            "lecture": filtered_lecture,
                        }
                
                # Use new method with reference types
                if include_solution:
                    result = generation_service.generate_with_reference_types_and_solution(
                        ocr_text, assessment_chunks, lecture_chunks, refs_dict
                    )
                    question = result["question"]
                    if result.get("solution"):
                        question += f"\n\nSolution:\n{result['solution']}"
                else:
                    result = generation_service.generate_with_reference_types(
                        ocr_text, assessment_chunks, lecture_chunks, refs_dict
                    )
                    question = result["question"]
            else:
                # Fallback to old method if no chunks retrieved (manual context or no class_id)
                context_list: List[str] = []
                if retrieved_context:
                    # Use manually provided context (already parsed above)
                    try:
                        parsed = json.loads(retrieved_context)
                        context_list = parsed if isinstance(parsed, list) else [retrieved_context]
                    except (json.JSONDecodeError, TypeError):
                        context_list = [retrieved_context] if isinstance(retrieved_context, str) else []
                else:
                    # No context at all - use empty list
                    context_list = []
                
                if include_solution:
                    result = generation_service.generate_with_solution(ocr_text, context_list)
                    question = result["question"]
                    if result.get("solution"):
                        question += f"\n\nSolution:\n{result['solution']}"
                else:
                    result = generation_service.generate_with_metadata(ocr_text, context_list)
                    question = result["question"]
            
            processing_steps.append("generation")

        # Build response
        # metadata is already initialized for mock_exam mode, initialize for normal mode here
        if mode != "mock_exam":
            metadata = result.get("metadata", {})
        metadata["processing_steps"] = processing_steps

        # Step 4: Save to class if class_id provided
        question_id = None
        saved_class_id = None
        if class_id:
            try:
                question_service = QuestionService(db)
                
                # For mock_exam mode, create MockExam objects and link individual questions
                if mode == "mock_exam" and questions:
                    from app.db.models import MockExam
                    
                    saved_question_ids = []
                    saved_mock_exam_ids = []
                    exam_set_id = str(uuid.uuid4()) if max_coverage else None
                    
                    for idx, exam_content_text in enumerate(questions):
                        try:
                            # Get the individual questions list for this exam
                            individual_questions = []
                            if max_coverage and idx < len(all_exams):
                                individual_questions = all_exams[idx].get("questions", [])
                            elif not max_coverage and result:
                                individual_questions = result.get("questions", [])
                            
                            # Extract exam title and instructions from exam_content
                            exam_title = None
                            exam_instructions = None
                            if exam_content_text:
                                lines = exam_content_text.split('\n')
                                # Try to extract title (usually first line or after "Exam:" or "Title:")
                                for i, line in enumerate(lines[:5]):  # Check first 5 lines
                                    line_lower = line.lower().strip()
                                    if line_lower.startswith('exam:') or line_lower.startswith('title:'):
                                        exam_title = line.split(':', 1)[1].strip() if ':' in line else None
                                    elif i == 0 and len(line.strip()) > 0 and len(line.strip()) < 100:
                                        exam_title = line.strip()
                                    
                                    # Look for instructions section
                                    if 'instruction' in line_lower:
                                        # Get next few lines as instructions
                                        exam_instructions = '\n'.join(lines[i+1:i+5]).strip()
                            
                            # Create MockExam object
                            mock_exam_id = str(uuid.uuid4())
                            mock_exam = MockExam(
                                id=mock_exam_id,
                                class_id=class_id,
                                title=exam_title,
                                instructions=exam_instructions,
                                exam_format=exam_format,
                                weighting_rules=final_weighting_rules if final_weighting_rules else {},
                                exam_metadata={
                                    "generated": True,
                                    "processing_steps": processing_steps,
                                    "generation_metadata": metadata,
                                    "exam_type": "max_coverage" if max_coverage else "single",
                                }
                            )
                            
                            # For max coverage, add set metadata
                            if max_coverage:
                                mock_exam.exam_metadata["exam_set_id"] = exam_set_id
                                mock_exam.exam_metadata["exam_index"] = idx
                                mock_exam.exam_metadata["total_exams_in_set"] = len(questions)
                            
                            # Add page references and coverage metrics
                            if max_coverage and idx < len(all_exams):
                                exam_page_refs = all_exams[idx].get("page_references", [])
                                if exam_page_refs:
                                    mock_exam.exam_metadata["page_references"] = exam_page_refs
                                mock_exam.exam_metadata["final_coverage"] = metadata.get("final_coverage", 0.0)
                            elif not max_coverage and "page_references" in metadata:
                                mock_exam.exam_metadata["page_references"] = metadata.get("page_references", [])
                            
                            if "coverage_metric" in metadata:
                                mock_exam.exam_metadata["coverage_metric"] = metadata.get("coverage_metric")
                            elif max_coverage and "final_coverage" in metadata:
                                mock_exam.exam_metadata["coverage_metric"] = metadata.get("final_coverage", 0.0)
                            
                            db.add(mock_exam)
                            db.flush()  # Flush to get the ID
                            
                            # Create individual Question objects linked to MockExam
                            # Extract tags from reference chunks if available
                            for q_idx, question_text in enumerate(individual_questions):
                                # Try to extract tags from reference chunks
                                # Use the chunk that was most relevant for this question
                                question_slideset = None
                                question_slide = None
                                question_topic = None
                                
                                # For now, we'll extract tags from the first relevant chunk
                                # Agent 2 should have added logic to extract tags per question
                                if assessment_chunks or lecture_chunks:
                                    # Use first chunk's metadata as default (can be improved)
                                    first_chunk = (assessment_chunks + lecture_chunks)[0] if (assessment_chunks or lecture_chunks) else None
                                    if first_chunk and first_chunk.metadata:
                                        # Merge auto_tags and user_overrides (user_overrides take precedence)
                                        effective_metadata = first_chunk.metadata.get("auto_tags", {}).copy()
                                        effective_metadata.update(first_chunk.metadata.get("user_overrides", {}))
                                        
                                        question_slideset = effective_metadata.get("slideset") or first_chunk.metadata.get("slideset")
                                        question_slide = effective_metadata.get("slide_number") or first_chunk.metadata.get("slide_number")
                                        question_topic = effective_metadata.get("topic") or first_chunk.metadata.get("topic")
                                
                                question_data = QuestionCreate(
                                    class_id=class_id,
                                    question_text=question_text,
                                    solution=None,  # Solutions are included in exam_content if include_solution was True
                                    metadata={
                                        "generated": True,
                                        "is_mock_exam_question": True,
                                        "question_index": q_idx + 1,
                                    },
                                    source_image=str(temp_path) if temp_path else None,
                                )
                                
                                saved_question = question_service.create_question(question_data)
                                
                                # Update question with mock_exam_id and tags
                                saved_question.mock_exam_id = mock_exam_id
                                saved_question.slideset = question_slideset
                                saved_question.slide = question_slide
                                saved_question.topic = question_topic
                                
                                saved_question_ids.append(saved_question.id)
                            
                            # If no individual questions were extracted, create one question with full exam content
                            if not individual_questions:
                                question_data = QuestionCreate(
                                    class_id=class_id,
                                    question_text=exam_content_text,
                                    solution=None,
                                    metadata={
                                        "generated": True,
                                        "is_mock_exam_question": True,
                                        "full_exam_content": True,
                                    },
                                    source_image=str(temp_path) if temp_path else None,
                                )
                                saved_question = question_service.create_question(question_data)
                                saved_question.mock_exam_id = mock_exam_id
                                saved_question_ids.append(saved_question.id)
                            
                            db.commit()
                            saved_mock_exam_ids.append(mock_exam_id)
                            
                            logger.info(f"Created mock exam {mock_exam_id} with {len(individual_questions) or 1} question(s)")
                            
                        except Exception as e:
                            db.rollback()
                            logger.warning(f"Failed to save mock exam {idx + 1} of {len(questions)}: {e}", exc_info=True)
                    
                    if saved_mock_exam_ids:
                        question_id = saved_question_ids[0] if saved_question_ids else None
                        saved_class_id = class_id
                        logger.info(f"Saved {len(saved_mock_exam_ids)} mock exam(s) to class {class_id}")
                    else:
                        logger.warning(f"No mock exams saved for class {class_id}")
                elif mode == "normal" and question:
                    # Normal mode: save single question
                    # Extract solution if included
                    solution_text = None
                    if include_solution and result.get("solution"):
                        solution_text = result["solution"]
                    
                    # Create question data
                    question_data = QuestionCreate(
                        class_id=class_id,
                        question_text=question,
                        solution=solution_text,
                        metadata={
                            "generated": True,
                            "processing_steps": processing_steps,
                            "generation_metadata": metadata,
                        },
                        source_image=str(temp_path) if temp_path else None,
                    )
                    
                    saved_question = question_service.create_question(question_data)
                    question_id = saved_question.id
                    saved_class_id = class_id
                    
                    logger.info(f"Saved generated question {question_id} to class {class_id}")
                
            except ValueError as e:
                # Class not found - log but don't fail the request
                # #region agent log
                with open('/home/swesan/exam-problem-extractor/.cursor/debug.log', 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"generate.py:540","message":"ValueError saving question","data":{"error":str(e),"class_id":class_id,"mode":mode,"timestamp":__import__('time').time()*1000},"timestamp":int(__import__('time').time()*1000)})+'\n')
                # #endregion
                logger.warning(f"Failed to save question to class {class_id}: {e}")
            except Exception as e:
                # Log error but don't fail the request
                # #region agent log
                with open('/home/swesan/exam-problem-extractor/.cursor/debug.log', 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A,C","location":"generate.py:544","message":"Exception saving question","data":{"error":str(e),"error_type":type(e).__name__,"class_id":class_id,"mode":mode,"timestamp":__import__('time').time()*1000},"timestamp":int(__import__('time').time()*1000)})+'\n')
                # #endregion
                logger.error(f"Error saving question to class: {e}", exc_info=True)

        # For max coverage mode, return all exam contents
        questions_for_response = questions if mode == "mock_exam" else None
        
        # Get mock_exam_id if we created one
        mock_exam_id = None
        if mode == "mock_exam" and saved_class_id and saved_mock_exam_ids:
            mock_exam_id = saved_mock_exam_ids[0]  # Return first mock exam ID
        
        return GenerateResponse(
            question=question if mode == "normal" else None,
            questions=questions_for_response,
            metadata=metadata,
            processing_steps=processing_steps,
            question_id=question_id,
            class_id=saved_class_id,
            references_used=references_used,
            mock_exam_id=mock_exam_id,
            weighting_rules=final_weighting_rules if mode == "mock_exam" and final_weighting_rules else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        from app.config import settings
        from app.utils.error_utils import get_safe_error_detail

        logger.error(f"Question generation failed: {str(e)}", exc_info=True)
        is_production = settings.environment.lower() == "production"
        # Sanitize the full error message, not just the exception
        full_error_msg = f"Question generation failed: {str(e)}"
        from app.utils.error_utils import sanitize_error_message
        safe_detail = sanitize_error_message(full_error_msg, is_production)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=safe_detail,
        ) from e
    finally:
        # Clean up temporary file
        if temp_path:
            cleanup_temp_file(temp_path)

