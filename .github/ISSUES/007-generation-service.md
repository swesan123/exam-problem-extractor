# Issue #7: Generation Service Implementation

## Phase
Phase 2: Core Services

## Description
Implement the generation service that creates exam-style questions using OpenAI GPT models. This service combines OCR text with retrieved context to generate formatted questions using RAG (Retrieval-Augmented Generation).

## Acceptance Criteria
- [ ] Create `app/services/generation_service.py` with `GenerationService` class
- [ ] Implement `generate_question(ocr_text: str, retrieved_context: List[str]) -> str`
- [ ] Implement `generate_with_metadata(ocr_text: str, retrieved_context: List[str]) -> dict`
- [ ] Build effective prompts with OCR text and context
- [ ] Integrate with OpenAI GPT-4 API
- [ ] Format output as exam-style question
- [ ] Handle solution generation (optional flag)
- [ ] Parse and clean generated output
- [ ] Unit tests with mocked OpenAI API

## Technical Details

### Service Interface
```python
class GenerationService:
    def __init__(self, openai_client: OpenAI):
        ...
    
    def generate_question(self, ocr_text: str, retrieved_context: List[str]) -> str:
        """Generate formatted exam question."""
        
    def generate_with_metadata(self, ocr_text: str, retrieved_context: List[str]) -> dict:
        """Generate question with metadata (tokens, model, etc.)."""
```

### Prompt Engineering
- Include OCR text as primary content
- Include retrieved examples as context
- Instruct model to format as exam question
- Specify style and format requirements
- Avoid hallucinated content

### OpenAI Integration
- Use `gpt-4` or `gpt-4-mini` model
- Configure appropriate temperature (0.7-0.9)
- Set max_tokens appropriately
- Handle streaming responses (optional)

### Output Formatting
- Clean and format generated text
- Ensure proper question structure
- Remove any artifacts or formatting issues
- Preserve mathematical expressions

## Implementation Notes
- Use system and user prompts for better control
- Include examples in prompt for consistency
- Handle long contexts (may need truncation)
- Implement retry logic for API failures
- Log token usage for cost monitoring

## Testing Requirements
- Mock OpenAI GPT API responses
- Test with various OCR text inputs
- Test with different context sizes
- Test solution generation flag
- Test output formatting

## References
- Design Document: Section 4.2 (Generation Service), Section 3.1 (Data Flow)
- Implementation Plan: Phase 2, Step 4

