# Issue #3: Utility Functions Implementation

## Phase
Phase 1: Foundation

## Description
Implement all utility functions for file handling, text cleaning, and text chunking. These are pure functions used across multiple services.

## Acceptance Criteria
- [ ] Create `app/utils/file_utils.py` with:
  - `validate_image_file(file: UploadFile) -> bool`
  - `save_temp_file(file: UploadFile) -> Path`
  - `cleanup_temp_file(path: Path) -> None`
  - `get_file_size_mb(path: Path) -> float`
- [ ] Create `app/utils/text_cleaning.py` with:
  - `clean_ocr_text(text: str) -> str`
  - `remove_artifacts(text: str) -> str`
  - `normalize_whitespace(text: str) -> str`
  - `extract_math_expressions(text: str) -> List[str]`
- [ ] Create `app/utils/chunking.py` with:
  - `chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]`
  - `chunk_by_sentences(text: str, max_chunk_size: int) -> List[str]`
  - `smart_chunk(text: str, max_size: int) -> List[str]`
- [ ] All functions have type hints
- [ ] All functions have docstrings
- [ ] All functions are pure (no side effects except file I/O)
- [ ] Unit tests for all utility functions

## Technical Details

### File Utils
- Validate MIME types: PNG, JPG, JPEG
- Max file size: 10MB
- Use `pathlib.Path` for all file operations
- Temp files stored in system temp directory
- Auto-cleanup on context exit (consider context manager)

### Text Cleaning
- Remove OCR artifacts (stray characters, formatting issues)
- Normalize whitespace (multiple spaces → single space)
- Preserve mathematical expressions
- Handle special characters appropriately

### Chunking
- `chunk_text`: Simple character-based chunking with overlap
- `chunk_by_sentences`: Sentence-aware chunking
- `smart_chunk`: Context-aware chunking that preserves meaning
- Default chunk size: 1000 characters
- Default overlap: 200 characters

## Implementation Notes
- Use `pathlib` instead of `os.path`
- Use `tempfile` module for temporary file handling
- Consider using regex for text cleaning
- For chunking, preserve sentence boundaries when possible
- Handle edge cases (empty text, very short text, etc.)

## Testing Requirements
- Test file validation with various file types
- Test text cleaning with sample OCR output
- Test chunking with various text lengths
- Test edge cases (empty inputs, very large inputs)

## References
- Design Document: Section 4.4 (Utility Modules)
- Implementation Plan: Phase 1, Step 5

