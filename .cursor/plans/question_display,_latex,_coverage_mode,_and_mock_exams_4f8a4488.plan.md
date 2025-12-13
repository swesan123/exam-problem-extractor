---
name: Question Display, LaTeX, Coverage Mode, and Mock Exams
overview: Add inline question display with LaTeX rendering, batch coverage mode, mock exam generation, and limit downloads to PDFs only. Store exam format per class and convert generated text to LaTeX format.
todos: []
---

# Question Display, LaTeX Support, Coverage Mode, and Mock Exam Generation

## Overview

This plan implements:

1. Inline question display in chat with LaTeX math rendering using KaTeX
2. LaTeX conversion utility for consistent math formatting
3. Batch coverage mode to generate multiple questions covering all reference material
4. Mock exam generation following class-defined exam structure
5. PDF-only downloads
6. Exam format/structure storage per class

## Architecture

### Data Flow

```
User Input → Generate Request (with mode: normal/coverage/mock_exam)
  ↓
Generation Service (with LaTeX conversion)
  ↓
Response (LaTeX-formatted question text)
  ↓
Frontend (KaTeX rendering) → Inline Display
```

### Database Changes

- Add `exam_format` (Text) field to `Class` model in [app/db/models.py](app/db/models.py)
- Migration needed to add column to existing classes

### Backend Changes

#### 1. Database Model Update

**File**: [app/db/models.py](app/db/models.py)

- Add `exam_format` column to `Class` model:
  ```python
  exam_format = Column(Text, nullable=True)
  ```


#### 2. LaTeX Conversion Utility

**New File**: [app/utils/latex_converter.py](app/utils/latex_converter.py)

- Create utility to convert plain text math expressions to LaTeX
- Detect math patterns (e.g., `x^2`, `sqrt(x)`, fractions, integrals)
- Convert inline math: `$...$` or `\(...\)`
- Convert display math: `$$...$$` or `\[...\]`
- Preserve existing LaTeX if already formatted
- Handle common math notation conversions

#### 3. Generation Service Updates

**File**: [app/services/generation_service.py](app/services/generation_service.py)

**New Methods:**

- `generate_coverage_batch()`: Generate multiple questions covering different topics from references
  - Takes `question_count` parameter
  - Retrieves diverse chunks from all references
  - Generates questions ensuring coverage across topics
  - Returns list of questions

- `generate_mock_exam()`: Generate complete mock exam following exam structure
  - Takes `exam_format` (text template) and `class_id`
  - Parses exam format to determine question types/counts
  - Uses assessment references for structure
  - Generates all questions in single response
  - Returns formatted exam document

**Modifications:**

- Update existing generation methods to apply LaTeX conversion via `latex_converter.convert_to_latex()`
- Add mode parameter to generation methods

#### 4. Generation Models Update

**File**: [app/models/generation_models.py](app/models/generation_models.py)

**Update `GenerateRequest`:**

- Add `mode` field: `Optional[Literal["normal", "coverage", "mock_exam"]]`
- Add `question_count` field: `Optional[int]` (for coverage mode)
- Add `exam_format` field: `Optional[str]` (for mock exam mode, can be inherited from class)

**Update `GenerateResponse`:**

- Add `questions` field: `Optional[List[str]]` (for batch/mock exam responses)
- Keep `question` field for single question mode (backward compatible)

#### 5. Generation Route Updates

**File**: [app/routes/generate.py](app/routes/generate.py)

**Modifications:**

- Add `mode`, `question_count`, `exam_format` parameters to endpoint
- If `mode == "coverage"`:
  - Call `generate_coverage_batch()` with `question_count`
  - Return response with `questions` list
- If `mode == "mock_exam"`:
  - Get `exam_format` from class if not provided
  - Call `generate_mock_exam()` with format and class_id
  - Return response with `questions` list (formatted as exam)
- Apply LaTeX conversion to all generated questions

#### 6. Class API Updates

**File**: [app/api/classes.py](app/api/classes.py) (or wherever class endpoints are)

**New Endpoint:**

- `PATCH /api/classes/{class_id}/exam-format`: Update exam format for a class
  - Accepts `exam_format` (text) in request body
  - Updates `Class.exam_format` field

**Update Class Response Models:**

- Include `exam_format` field in class responses

#### 7. Question Download Updates

**File**: [app/routes/questions.py](app/routes/questions.py) (or wherever download endpoint is)

**Modifications:**

- Remove support for `txt`, `docx`, `json` formats
- Keep only `pdf` format
- Update validation to reject non-PDF format requests

### Frontend Changes

#### 1. Dependencies

**File**: [frontend/package.json](frontend/package.json)

- Add `katex` and `react-katex` packages:
  ```json
  "katex": "^0.16.9",
  "react-katex": "^3.0.1"
  ```


#### 2. LaTeX Rendering Component

**New File**: [frontend/src/components/LatexRenderer.tsx](frontend/src/components/LatexRenderer.tsx)

- Component to render LaTeX math in text
- Uses `react-katex` for rendering
- Handles both inline (`$...$`) and display (`$$...$$`) math
- Falls back to plain text if LaTeX parsing fails

#### 3. Generate Page Updates

**File**: [frontend/src/pages/Generate.tsx](frontend/src/pages/Generate.tsx)

**Additions:**

- Import `LatexRenderer` component
- Add mode selector in settings dropdown:
  - "Normal" (default)
  - "Coverage Mode" (with question count input)
  - "Mock Exam" (only if class selected)
- Update message rendering to use `LatexRenderer` for assistant messages
- Handle `questions` array in response (for batch/mock exam modes)
- Display multiple questions in single message for mock exam mode

**Modifications:**

- Update `handleSubmit` to include `mode`, `question_count`, `exam_format` in request
- Update message display to render LaTeX-formatted question text

#### 4. Class Details/Settings Updates

**File**: [frontend/src/pages/ClassDetails.tsx](frontend/src/pages/ClassDetails.tsx) or new settings component

**Additions:**

- Add "Exam Format" section
- Text area for entering exam format template (e.g., "5 multiple choice, 3 short answer, 2 long answer")
- Save button to update class exam format
- Display current exam format if set

#### 5. Question Service Updates

**File**: [frontend/src/services/questionService.ts](frontend/src/services/questionService.ts)

**Modifications:**

- Update `download()` method to only accept `'pdf'` format
- Remove other format options from type definitions

#### 6. Class Questions Page Updates

**File**: [frontend/src/pages/ClassQuestions.tsx](frontend/src/pages/ClassQuestions.tsx)

**Modifications:**

- Remove `txt`, `docx`, `json` options from download menu
- Keep only PDF download option
- Update question preview to use `LatexRenderer` component

#### 7. Generate Service Updates

**File**: [frontend/src/services/generateService.ts](frontend/src/services/generateService.ts)

**Update `GenerateRequest` interface:**

- Add `mode?: 'normal' | 'coverage' | 'mock_exam'`
- Add `question_count?: number`
- Add `exam_format?: string`

**Update `GenerateResponse` interface:**

- Add `questions?: string[]` (for batch responses)

## Implementation Details

### LaTeX Conversion Strategy

1. Detect common math patterns in generated text
2. Convert to LaTeX syntax:

   - `x^2` → `$x^2$`
   - `sqrt(x)` → `$\sqrt{x}$`
   - `1/2` → `$\frac{1}{2}$` (in math context)

3. Preserve existing LaTeX if detected
4. Use regex patterns for detection and conversion

### Coverage Mode Algorithm

1. Retrieve all reference chunks for the class
2. Group chunks by topic/similarity
3. Select diverse chunks across topics
4. Generate questions ensuring each topic is covered
5. Return list of questions with topic distribution

### Mock Exam Generation

1. Parse exam format text to extract:

   - Question types (multiple choice, short answer, etc.)
   - Counts for each type
   - Point values (if specified)

2. Retrieve assessment references for structure
3. Generate questions following the structure
4. Format as complete exam document with:

   - Header/title
   - Instructions
   - Questions numbered and formatted
   - Point values (if specified)

### Exam Format Template Examples

- "5 multiple choice questions, 3 short answer questions, 2 long answer questions"
- "10 questions total: 6 multiple choice (2 points each), 4 short answer (5 points each)"
- "Midterm format: 20 multiple choice, 5 short answer, 2 essays"

## Testing Considerations

- Test LaTeX conversion with various math expressions
- Test coverage mode with different question counts
- Test mock exam generation with various format templates
- Test PDF download only (verify other formats rejected)
- Test exam format storage and retrieval per class
- Test inline LaTeX rendering in chat interface

## Migration Notes

- Database migration needed for `exam_format` column
- Existing classes will have `exam_format = NULL`
- Backward compatible: existing single-question generation still works