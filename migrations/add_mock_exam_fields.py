"""Migration script to convert existing mock exam questions to MockExam objects.

This migration:
1. Finds all questions with is_mock_exam=True in metadata
2. Parses exam_content to extract individual questions
3. Creates MockExam objects
4. Creates individual Question entries linked to MockExam
5. Extracts tags from existing metadata if available
6. Updates ChromaDB chunk metadata with new structure (auto_tags and user_overrides)
"""

import logging
import re
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import chromadb
from chromadb.config import Settings as ChromaSettings
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.config import settings
from app.db.database import SessionLocal, engine, init_db
from app.db.models import MockExam, Question

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def split_exam_into_questions(exam_content: str) -> List[str]:
    """
    Split exam content into individual questions.
    
    Uses the same logic as GenerationService._split_exam_into_questions.
    
    Args:
        exam_content: Full exam document
        
    Returns:
        List of individual question strings
    """
    questions = []
    
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


def extract_exam_title_and_instructions(exam_content: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract exam title and instructions from exam content.
    
    Args:
        exam_content: Full exam document
        
    Returns:
        Tuple of (title, instructions)
    """
    lines = exam_content.split('\n')
    title = None
    instructions = None
    instructions_start = None
    
    # Look for title patterns
    for i, line in enumerate(lines[:10]):  # Check first 10 lines
        line_lower = line.lower().strip()
        if any(keyword in line_lower for keyword in ['exam', 'test', 'midterm', 'final', 'quiz']):
            # Check if it's a title (usually short, no question numbers)
            if len(line.strip()) < 100 and not re.match(r'^\d+[\.\)]', line.strip()):
                title = line.strip()
                instructions_start = i + 1
                break
    
    # Look for instructions section
    if instructions_start is None:
        instructions_start = 0
    
    instructions_lines = []
    for i in range(instructions_start, min(instructions_start + 20, len(lines))):
        line = lines[i].strip()
        if not line:
            continue
        # Stop if we hit a question number
        if re.match(r'^\d+[\.\)]', line) or re.match(r'^Question\s+\d+', line, re.IGNORECASE):
            break
        # Collect instruction lines
        if any(keyword in line.lower() for keyword in ['instruction', 'directions', 'note', 'time', 'points', 'total']):
            instructions_lines.append(line)
        elif instructions_lines:  # Continue collecting if we've started
            instructions_lines.append(line)
    
    if instructions_lines:
        instructions = '\n'.join(instructions_lines)
    
    return title, instructions


def extract_tags_from_metadata(metadata: Dict) -> Dict:
    """
    Extract tags from existing question metadata.
    
    Args:
        metadata: Question metadata dictionary
        
    Returns:
        Dictionary with extracted tags (slideset, slide, topic, exam_region)
    """
    tags = {}
    
    # Check for tags in metadata
    if 'slideset' in metadata:
        tags['slideset'] = metadata['slideset']
    if 'slide' in metadata or 'slide_number' in metadata:
        tags['slide'] = metadata.get('slide') or metadata.get('slide_number')
    if 'topic' in metadata:
        tags['topic'] = metadata['topic']
    if 'exam_region' in metadata:
        tags['exam_region'] = metadata['exam_region']
    
    # Check in generation_metadata if present
    gen_metadata = metadata.get('generation_metadata', {})
    if 'slideset' in gen_metadata:
        tags['slideset'] = gen_metadata['slideset']
    if 'slide' in gen_metadata or 'slide_number' in gen_metadata:
        tags['slide'] = gen_metadata.get('slide') or gen_metadata.get('slide_number')
    if 'topic' in gen_metadata:
        tags['topic'] = gen_metadata['topic']
    if 'exam_region' in gen_metadata:
        tags['exam_region'] = gen_metadata['exam_region']
    
    return tags


def update_chromadb_metadata(embedding_service, chunk_id: str, tags: Dict) -> None:
    """
    Update ChromaDB chunk metadata with new structure (auto_tags and user_overrides).
    
    Args:
        embedding_service: EmbeddingService instance
        chunk_id: Chunk ID to update
        tags: Tags to add to auto_tags
    """
    try:
        # Get existing chunk
        collection = embedding_service.collection
        existing = collection.get(ids=[chunk_id])
        
        if not existing['ids']:
            logger.warning(f"Chunk {chunk_id} not found in ChromaDB, skipping metadata update")
            return
        
        # Get existing metadata
        existing_metadata = existing['metadatas'][0] if existing['metadatas'] else {}
        
        # Create auto_tags from existing metadata and new tags
        auto_tags = {}
        if tags:
            auto_tags.update(tags)
        
        # Preserve existing tag fields in auto_tags
        for field in ['slideset', 'slide_number', 'topic', 'exam_region']:
            if field in existing_metadata and field not in auto_tags:
                auto_tags[field] = existing_metadata[field]
        
        # Create updated metadata with auto_tags and user_overrides
        updated_metadata = existing_metadata.copy()
        updated_metadata['auto_tags'] = auto_tags
        if 'user_overrides' not in updated_metadata:
            updated_metadata['user_overrides'] = {}
        
        # Remove None values
        updated_metadata = {k: v for k, v in updated_metadata.items() if v is not None}
        
        # Update in ChromaDB
        collection.update(
            ids=[chunk_id],
            metadatas=[updated_metadata]
        )
        
        logger.info(f"Updated ChromaDB metadata for chunk {chunk_id}")
    except Exception as e:
        logger.warning(f"Failed to update ChromaDB metadata for chunk {chunk_id}: {e}")


def migrate_mock_exams(dry_run: bool = False) -> Dict:
    """
    Migrate existing mock exam questions to MockExam objects.
    
    Args:
        dry_run: If True, only report what would be done without making changes
        
    Returns:
        Dictionary with migration statistics
    """
    stats = {
        'total_mock_exams_found': 0,
        'mock_exams_created': 0,
        'questions_created': 0,
        'errors': 0,
        'skipped': 0,
    }
    
    # Initialize database
    init_db()
    
    # Create database session
    db: Session = SessionLocal()
    
    try:
        # Find all questions with is_mock_exam=True in metadata
        all_questions = db.query(Question).all()
        mock_exam_questions = []
        
        for question in all_questions:
            metadata = question.question_metadata or {}
            if metadata.get('is_mock_exam') is True:
                mock_exam_questions.append(question)
        
        stats['total_mock_exams_found'] = len(mock_exam_questions)
        logger.info(f"Found {len(mock_exam_questions)} mock exam question(s) to migrate")
        
        if not mock_exam_questions:
            logger.info("No mock exam questions found. Migration complete.")
            return stats
        
        # Initialize embedding service for ChromaDB updates
        try:
            from app.services.embedding_service import EmbeddingService
            embedding_service = EmbeddingService()
        except Exception as e:
            logger.warning(f"Could not initialize EmbeddingService: {e}. ChromaDB updates will be skipped.")
            embedding_service = None
        
        # Process each mock exam question
        for old_question in mock_exam_questions:
            try:
                metadata = old_question.question_metadata or {}
                exam_content = old_question.question_text
                
                # Skip if already migrated (has mock_exam_id)
                if old_question.mock_exam_id:
                    logger.info(f"Question {old_question.id} already has mock_exam_id, skipping")
                    stats['skipped'] += 1
                    continue
                
                # Extract individual questions
                individual_questions = split_exam_into_questions(exam_content)
                
                # Use individual_questions from metadata if available (more accurate)
                if 'individual_questions' in metadata and isinstance(metadata['individual_questions'], list):
                    if len(metadata['individual_questions']) > 0:
                        individual_questions = metadata['individual_questions']
                
                if not individual_questions:
                    logger.warning(f"No questions found in exam content for question {old_question.id}, skipping")
                    stats['skipped'] += 1
                    continue
                
                # Extract title and instructions
                title, instructions = extract_exam_title_and_instructions(exam_content)
                
                # Extract weighting rules from metadata
                weighting_rules = metadata.get('weighting_rules') or {}
                
                # Extract exam format
                exam_format = metadata.get('exam_format') or old_question.class_obj.exam_format if old_question.class_obj else None
                
                # Create exam metadata
                exam_metadata = {
                    'migrated_from_question_id': old_question.id,
                    'migration_timestamp': str(uuid.uuid4()),  # Simple timestamp placeholder
                }
                
                # Preserve existing metadata
                for key in ['exam_type', 'final_coverage', 'coverage_metric', 'exam_set_id', 'exam_index', 'total_exams_in_set']:
                    if key in metadata:
                        exam_metadata[key] = metadata[key]
                
                if not dry_run:
                    # Create MockExam object
                    mock_exam_id = str(uuid.uuid4())
                    mock_exam = MockExam(
                        id=mock_exam_id,
                        class_id=old_question.class_id,
                        title=title,
                        instructions=instructions,
                        exam_format=exam_format,
                        weighting_rules=weighting_rules,
                        exam_metadata=exam_metadata,
                    )
                    db.add(mock_exam)
                    db.flush()  # Flush to get the ID
                    
                    logger.info(f"Created MockExam {mock_exam_id} from question {old_question.id}")
                    stats['mock_exams_created'] += 1
                    
                    # Create individual Question objects
                    for idx, question_text in enumerate(individual_questions):
                        # Extract tags from metadata
                        tags = extract_tags_from_metadata(metadata)
                        
                        # Try to extract tags from page_references if available
                        page_refs = metadata.get('page_references', [])
                        if page_refs and isinstance(page_refs, list) and len(page_refs) > idx:
                            ref = page_refs[idx]
                            if isinstance(ref, dict):
                                ref_metadata = ref.get('metadata', {})
                                if 'slideset' in ref_metadata:
                                    tags['slideset'] = ref_metadata['slideset']
                                if 'slide_number' in ref_metadata:
                                    tags['slide'] = ref_metadata['slide_number']
                                if 'topic' in ref_metadata:
                                    tags['topic'] = ref_metadata['topic']
                                if 'exam_region' in ref_metadata:
                                    tags['exam_region'] = ref_metadata['exam_region']
                                
                                # Update ChromaDB metadata if chunk_id is available
                                if embedding_service and 'chunk_id' in ref_metadata:
                                    update_chromadb_metadata(embedding_service, ref_metadata['chunk_id'], tags)
                        
                        # Create question metadata
                        question_metadata = {
                            'generated': True,
                            'is_mock_exam_question': True,
                            'question_index': idx,
                            'total_questions': len(individual_questions),
                        }
                        
                        # Preserve generation metadata if available
                        if 'generation_metadata' in metadata:
                            question_metadata['generation_metadata'] = metadata['generation_metadata']
                        
                        # Create new Question object
                        new_question = Question(
                            id=str(uuid.uuid4()),
                            class_id=old_question.class_id,
                            mock_exam_id=mock_exam_id,
                            question_text=question_text,
                            solution=None,  # Solutions are in exam_content if included
                            question_metadata=question_metadata,
                            source_image=old_question.source_image,
                            slideset=tags.get('slideset'),
                            slide=tags.get('slide'),
                            topic=tags.get('topic'),
                            user_confidence=None,  # Will be set by user later
                        )
                        db.add(new_question)
                        stats['questions_created'] += 1
                    
                    # Delete or mark the old question as migrated
                    # Option 1: Delete the old question (recommended)
                    db.delete(old_question)
                    # Option 2: Keep but mark as migrated (uncomment if preferred)
                    # old_question.question_metadata['migrated_to_mock_exam_id'] = mock_exam_id
                    # old_question.mock_exam_id = mock_exam_id
                    
                    db.commit()
                    logger.info(f"Migrated mock exam from question {old_question.id}: created {len(individual_questions)} questions")
                else:
                    logger.info(f"[DRY RUN] Would migrate question {old_question.id}: {len(individual_questions)} questions")
                    stats['mock_exams_created'] += 1
                    stats['questions_created'] += len(individual_questions)
                    
            except Exception as e:
                logger.error(f"Error migrating question {old_question.id}: {e}", exc_info=True)
                stats['errors'] += 1
                db.rollback()
        
        if not dry_run:
            db.commit()
        
        logger.info(f"Migration complete. Stats: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


def main():
    """Main entry point for migration script."""
    import sys
    
    dry_run = '--dry-run' in sys.argv or '-d' in sys.argv
    
    if dry_run:
        logger.info("Running in DRY RUN mode - no changes will be made")
    
    try:
        stats = migrate_mock_exams(dry_run=dry_run)
        print("\n" + "="*60)
        print("Migration Summary")
        print("="*60)
        print(f"Total mock exams found: {stats['total_mock_exams_found']}")
        print(f"Mock exams {'would be ' if dry_run else ''}created: {stats['mock_exams_created']}")
        print(f"Questions {'would be ' if dry_run else ''}created: {stats['questions_created']}")
        print(f"Errors: {stats['errors']}")
        print(f"Skipped: {stats['skipped']}")
        print("="*60)
        
        if dry_run:
            print("\nTo apply the migration, run without --dry-run flag:")
            print("  python migrations/add_mock_exam_fields.py")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
