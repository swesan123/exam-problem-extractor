---
name: "Mock Exam Enhancements: Weighting, Question Count, Tagging, Confidence"
overview: Enhance Max Coverage mode with chunk weighting (pre/post-midterm), question count selection, question tagging (slideset/slide/topic), restructure mock exams as objects containing questions, and add user confidence tracking for confidence-based exam generation.
todos:
  - id: db_schema
    content: Create MockExam model and update Question model with new fields (mock_exam_id, slideset, slide, topic, user_confidence)
    status: pending
  - id: embedding_metadata
    content: Extend EmbeddingMetadata to include is_post_midterm, slideset, slide_number, topic fields
    status: pending
  - id: retrieval_weighting
    content: Update retrieval service to apply pre/post-midterm weighting to similarity scores
    status: pending
  - id: generation_question_count
    content: Add question_count parameter to generate_mock_exam and override exam_format parsing when provided
    status: pending
  - id: generation_tagging
    content: Extract and store slideset, slide, topic from reference metadata when generating questions
    status: pending
  - id: generation_confidence
    content: Add focus_on_uncertain parameter to prioritize chunks from low-confidence topics
    status: pending
  - id: generate_route_params
    content: Add question_count, pre_midterm_weight, post_midterm_weight, focus_on_uncertain parameters to generate route
    status: pending
  - id: generate_route_mock_exam
    content: Update generate route to create MockExam objects and link individual questions
    status: pending
  - id: question_update_endpoint
    content: Add PATCH endpoint to update question tags and confidence
    status: pending
  - id: reference_tagging_endpoint
    content: Add endpoint to tag reference content chunks with is_post_midterm, slideset, slide_number, topic
    status: pending
  - id: frontend_types
    content: Update TypeScript types to include MockExam interface and new Question fields
    status: pending
  - id: frontend_weighting_ui
    content: Add weighting controls to Generate page settings dropdown for mock exam mode
    status: pending
  - id: frontend_question_count
    content: Add question count selector (Auto/5/8/10/12/15/20/Custom) to Generate page
    status: pending
  - id: frontend_confidence_ui
    content: Add confidence selector (✓/~/✗) to questions in ClassQuestions page
    status: pending
  - id: frontend_mock_exam_display
    content: Update ClassQuestions page to display mock exams as objects with header, instructions, and grouped questions
    status: pending
  - id: frontend_topic_grouping
    content: Implement topic-based grouping in ClassQuestions page display (display only)
    status: pending
  - id: frontend_question_tagging
    content: Add UI to edit question tags (slideset, slide, topic) in ClassQuestions page
    status: pending
  - id: frontend_reference_tagging
    content: Add UI to tag reference content in ReferenceContent page
    status: pending
  - id: data_migration
    content: Create migration script to convert existing mock exam data to new MockExam structure
    status: pending
---

# Mock Exam Enhancements: Weighting, Question Count, Tagging, and Confidence

## Overview

This plan implements several enhancements to the Max Coverage mock exam mode:

1. **Dynamic chunk weighting**: Weight chunks based on exam structure (pre/post-midterm regions) with configurable rules
2. **Question count selection**: Allow users to specify number of questions (default: auto)
3. **Question tagging**: Tag questions with slideset, slide, and topic
4. **Mock exam restructuring**: Make mock exams objects containing individual questions
5. **User confidence tracking**: Add confidence levels (✓ / ~ / ✗) and use for exam generation

## Agent Assignment Quick Reference

| Agent | Phase | Tasks | Key Files | Dependencies |

|-------|-------|-------|-----------|--------------|

| **Agent 1** | Phase 1: Database Schema | Steps 1-3 | `app/db/models.py`, `app/models/embedding_models.py` | None (must complete first) |

| **Agent 2** | Phase 2: Backend Services | Steps 4, 5, 6, 10 | `app/services/*.py` | After Agent 1 |

| **Agent 3** | Phase 3: API Endpoints | Steps 7, 8, 9, 17, 18 | `app/routes/generate.py`, `app/api/*.py` | After Agent 2 |

| **Agent 4** | Phase 4: Frontend UI | Steps 11, 12, 13, 14, 15 | `frontend/src/**/*.tsx`, `frontend/src/types/*.ts` | After Agent 3 |

| **Agent 5** | Phase 5: Migration | Step 16 | `migrations/add_mock_exam_fields.py` | After Agents 1 & 2 (can parallel with 3-4) |

**See "Agent Assignment and Implementation Order" section below for detailed breakdown.**

## Chunk Metadata Structure

### Reference Chunk Structure

Chunks will have the following metadata structure:

```python
{
    "id": str,                    # chunk_id
    "slideset": Optional[str],    # Slideset name (e.g., "Lecture_5")
    "slide_number": Optional[int], # Slide number within slideset (subset of slideset)
    "topic": Optional[str],       # Topic name
    "exam_region": Optional[str], # "pre" | "post" | None (pre/post-midterm region)
    "auto_tags": Dict,            # Auto-extracted tags (for audit trail)
    "user_overrides": Dict        # User-manual overrides (takes precedence)
}
```

The effective metadata used for queries will merge `auto_tags` and `user_overrides`, with `user_overrides` taking precedence. Both are stored separately for audit trail.

## Database Schema Changes

### 1. Add MockExam Model

**File**: `app/db/models.py`

Create a new `MockExam` model to represent mock exams as objects:

```python
class MockExam(Base):
    __tablename__ = "mock_exams"
    
    id = Column(String, primary_key=True, index=True)
    class_id = Column(String, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String, nullable=True)  # Exam title/header
    instructions = Column(Text, nullable=True)  # Exam instructions
    exam_format = Column(Text, nullable=True)  # Format template used
    weighting_rules = Column(JSON, nullable=True, default=dict)  # Weighting configuration
    exam_metadata = Column(JSON, nullable=True, default=dict)  # Additional metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationship to questions
    questions = relationship("Question", back_populates="mock_exam", cascade="all, delete-orphan")
```

### 2. Update Question Model

**File**: `app/db/models.py`

Add fields to `Question` model:

- `mock_exam_id`: Foreign key to `MockExam` (nullable, for questions that are part of mock exams)
- `slideset`: String field for slideset name
- `slide`: Integer field for slide number
- `topic`: String field for topic name
- `user_confidence`: String field for confidence level ('confident', 'uncertain', 'not_confident')
- Update `question_metadata` JSON to include slideset/slide/topic if not in dedicated fields

Add relationship:

```python
mock_exam = relationship("MockExam", back_populates="questions")
```

### 3. Update EmbeddingMetadata Model

**File**: `app/models/embedding_models.py`

Extend `EmbeddingMetadata` to include:

- `slideset`: Optional[str] - Slideset name
- `slide_number`: Optional[int] - Slide number within slideset
- `topic`: Optional[str] - Topic name
- `exam_region`: Optional[str] - "pre" | "post" (pre/post-midterm region)
- `auto_tags`: Optional[Dict] - Auto-extracted tags (JSON)
- `user_overrides`: Optional[Dict] - User manual overrides (JSON)

Note: When storing in ChromaDB, merge auto_tags and user_overrides into the main metadata dict, with user_overrides taking precedence. Store both separately in a metadata audit field if needed.

## Backend Changes

### 4. Update Retrieval Service for Dynamic Weighting

**File**: `app/services/retrieval_service.py`

Modify `retrieve_with_scores` to accept weighting configuration:

- Add `weighting_rules: Optional[Dict] = None` parameter
- Weighting rules format:
  ```python
  {
      "pre_midterm_weight": 1.0,
      "post_midterm_weight": 2.0,
      # Or more granular:
      "region_weights": {
          "pre": 1.0,
          "post": 2.0
      },
      # Or slide-based:
      "slide_ranges": [
          {"start": 1, "end": 10, "weight": 1.0},
          {"start": 11, "end": 20, "weight": 2.0}
      ]
  }
  ```

- After retrieving chunks, apply weights to similarity scores based on:

  1. `exam_region` metadata (pre/post)
  2. Slide ranges if specified
  3. Default weights if no rules provided

- Re-sort chunks by weighted scores

### 5. Weighting Rule Generation

**File**: `app/services/generation_service.py`

Add method to generate weighting rules from exam structure:

- `_infer_weighting_rules(exam_format: str, exam_type: Optional[str] = None) -> Dict`
- Logic:

  1. If exam_format contains explicit weighting (e.g., "5 pre-midterm, 3 post-midterm"), parse it
  2. Else if exam_type is "midterm", default to pre: 1.0, post: 0.5 (less weight on post)
  3. Else if exam_type is "final", default to pre: 1.0, post: 2.0 (more weight on post)
  4. Else default to pre: 1.0, post: 1.0 (equal weight)

- Allow override via explicit weighting_rules parameter

### 6. Update Generation Service

**File**: `app/services/generation_service.py`

#### 6.1 Add Question Count Parameter

- Modify `generate_mock_exam` to accept `question_count: Optional[int] = None`
- If `question_count` is None, parse from `exam_format` (current behavior)
- If provided, override parsed count

#### 6.2 Extract Question Tags from References

- When generating questions, extract `slideset`, `slide_number`, and `topic` from reference chunk metadata
- Use merged metadata (user_overrides override auto_tags)
- Store these in question metadata and dedicated fields

#### 6.3 Confidence-Based Selection

- Add `focus_on_uncertain: bool = False` parameter
- When `focus_on_uncertain` is True, prioritize chunks from topics where user has low confidence
- Query existing questions to find topics with low confidence
- Adjust weighting rules to favor those topics

#### 6.4 Return Individual Questions

- Modify return structure to include individual questions with their metadata
- Keep `exam_content` for full formatted exam, but also return structured question list with tags

### 7. Update Generate Route

**File**: `app/routes/generate.py`

#### 7.1 Add New Parameters

- `question_count: Optional[int] = Form(None)` - Number of questions for mock exam
- `weighting_rules: Optional[str] = Form(None)` - JSON string with weighting configuration (optional override)
- `focus_on_uncertain: bool = Form(False)` - Focus on uncertain topics

#### 7.2 Generate Weighting Rules

- Call `_infer_weighting_rules(exam_format, exam_type)` to get default rules
- If `weighting_rules` parameter provided, parse JSON and merge/override defaults
- Pass weighting rules to retrieval service

#### 7.3 Create MockExam Objects

- When saving mock exams, create `MockExam` object first with weighting_rules stored
- Save individual questions linked to the `MockExam`
- Store exam header/instructions in `MockExam.title` and `MockExam.instructions`

### 8. Add Question Update Endpoint

**File**: `app/api/questions.py`

Add endpoint to update question metadata:

- `PATCH /api/questions/{question_id}` - Update question tags (slideset, slide, topic) and confidence
- Accept JSON body with `slideset`, `slide`, `topic`, `user_confidence` fields

### 9. Add Reference Content Tagging Endpoint

**File**: `app/api/reference_content.py` or new endpoint

Add endpoint to tag reference content:

- `PATCH /api/reference-content/{chunk_id}` - Update chunk metadata
- Accept JSON body with:
  - `exam_region`: "pre" | "post" | null
  - `slideset`: string
  - `slide_number`: int
  - `topic`: string
- Store updates in `user_overrides` field
- Return merged metadata (user_overrides override auto_tags)

### 10. Auto-Tagging Service

**File**: `app/services/reference_processor.py` or new `app/services/tagging_service.py`

Add service to auto-extract tags from reference content:

- Extract slideset/slide from filename patterns (e.g., "Lecture_5_Slide_12.pdf")
- Extract topic from document structure or LLM analysis
- Determine exam_region from:
  - Filename patterns (e.g., "pre_midterm", "post_midterm")
  - Document metadata
  - Slide numbers (if midterm slide number is known)
- Store in `auto_tags` field

## Frontend Changes

### 11. Update Generate Page UI

**File**: `frontend/src/pages/Generate.tsx`

#### 11.1 Add Weighting Controls

- When `mode === 'mock_exam'`, show weighting controls in settings dropdown:
  - Default: "Auto (based on exam type)" - uses inferred rules
  - Option: "Custom weights" - shows:
    - Pre-midterm weight: [input] (default 1.0)
    - Post-midterm weight: [input] (default 2.0)
  - Option: "Slide range weights" - advanced mode for slide-based weighting

#### 11.2 Add Question Count Selector

- When `mode === 'mock_exam'`, show question count selector:
  - Dropdown with options: "Auto" (default), "5", "8", "10", "12", "15", "20", "Custom"
  - If "Custom" selected, show number input
  - Pass selected value to backend

#### 11.3 Add Confidence Focus Toggle

- Add toggle: "Focus on uncertain topics" (only when confidence data exists)

### 12. Update Question Types

**File**: `frontend/src/types/question.ts`

Add fields to `Question` interface:

```typescript
slideset?: string
slide?: number
topic?: string
user_confidence?: 'confident' | 'uncertain' | 'not_confident'
mock_exam_id?: string
```

Add `MockExam` interface:

```typescript
interface MockExam {
  id: string
  class_id: string
  title?: string
  instructions?: string
  exam_format?: string
  weighting_rules?: {
    pre_midterm_weight?: number
    post_midterm_weight?: number
    region_weights?: Record<string, number>
    slide_ranges?: Array<{start: number, end: number, weight: number}>
  }
  exam_metadata?: Record<string, any>
  questions: Question[]
  created_at: string
  updated_at: string
}
```

Add `ReferenceChunk` interface:

```typescript
interface ReferenceChunk {
  id: string
  slideset?: string
  slide_number?: number
  topic?: string
  exam_region?: 'pre' | 'post'
  auto_tags?: Record<string, any>
  user_overrides?: Record<string, any>
  // Merged view (for display)
  effective_metadata?: Record<string, any>
}
```

### 13. Update ClassQuestions Page

**File**: `frontend/src/pages/ClassQuestions.tsx`

#### 13.1 Display Mock Exam Structure

- When viewing a mock exam, show it as an object with:
  - Exam header/title
  - Instructions
  - Weighting rules used (if custom)
  - List of individual questions (grouped by topic if topic_grouping is enabled)
  - Each question shows its tags (slideset, slide, topic)

#### 13.2 Add Confidence UI

- Add confidence selector (✓ / ~ / ✗) to each question
- Save confidence via API when changed

#### 13.3 Topic Grouping (Display Only)

- Group questions by topic in the display
- Show topic headers with question counts
- Allow expanding/collapsing topics

### 14. Add Question Tagging UI

**File**: `frontend/src/pages/ClassQuestions.tsx` or new component

- Add edit mode for questions to set:
  - Slideset (text input or dropdown from available slidesets)
  - Slide number (number input, validated against slideset)
  - Topic (text input or dropdown from available topics)
- Auto-populate from reference metadata when available
- Allow manual editing

### 15. Add Reference Content Tagging UI

**File**: `frontend/src/pages/ReferenceContent.tsx`

- Add UI to tag reference content chunks:
  - Exam region: Dropdown ("Pre-midterm" | "Post-midterm" | "Not specified")
  - Slideset: Text input or dropdown
  - Slide number: Number input (validated as subset of slideset)
  - Topic: Text input or dropdown
- Show both auto_tags and user_overrides
- Highlight when user_overrides exist
- Bulk tagging option for multiple chunks

## Data Migration

### 16. Migration Script

**File**: `migrations/add_mock_exam_fields.py` (new)

- Create migration to:

  1. Create `mock_exams` table
  2. Add new columns to `questions` table
  3. Add new metadata fields to ChromaDB chunks (via embedding service update)
  4. Migrate existing mock exam data:

     - Parse existing mock exam questions from `exam_content`
     - Create `MockExam` objects
     - Create individual `Question` entries linked to `MockExam`
     - Extract tags from existing metadata if available

## API Updates

### 17. Update Generate Response

**File**: `app/models/generation_models.py`

Update `GenerateResponse` to include:

- `mock_exam_id`: Optional[str] - ID of created mock exam
- `questions`: List of question objects with tags, not just strings
- `weighting_rules`: Optional[Dict] - Weighting rules used

### 18. Add Mock Exam Endpoints

**File**: `app/api/questions.py` or new `app/api/mock_exams.py`

- `GET /api/mock-exams/{mock_exam_id}` - Get mock exam with all questions
- `GET /api/classes/{class_id}/mock-exams` - List all mock exams for a class
- `PATCH /api/mock-exams/{mock_exam_id}` - Update mock exam metadata

## Agent Assignment and Implementation Order

### Phase 1: Database Schema (Agent 1) - MUST COMPLETE FIRST

**Dependencies**: None

**Blocks**: All other phases

1. **Database schema changes** (steps 1-3)

   - Create `MockExam` model in `app/db/models.py`
   - Update `Question` model with new fields (mock_exam_id, slideset, slide, topic, user_confidence)
   - Update `EmbeddingMetadata` model in `app/models/embedding_models.py`
   - Create and run database migration
   - **Deliverable**: Database schema ready, migration script created

### Phase 2: Backend Core Services (Agent 2) - AFTER Phase 1

**Dependencies**: Phase 1 complete

**Blocks**: Phase 3 (API endpoints)

2. **Chunk metadata structure and auto-tagging** (step 10)

   - Create auto-tagging service (`app/services/tagging_service.py`)
   - Update embedding service to store auto_tags and user_overrides separately
   - Implement metadata merging logic (user_overrides override auto_tags)

3. **Retrieval service weighting** (steps 4-5)

   - Add `_infer_weighting_rules()` method to generation service
   - Update retrieval service to accept and apply weighting_rules
   - Implement dynamic weighting based on exam_region, slide ranges, or default rules

4. **Generation service updates** (step 6)

   - Add question_count parameter to `generate_mock_exam`
   - Add focus_on_uncertain parameter and confidence-based selection logic
   - Extract and store question tags from reference metadata
   - Update return structure to include individual questions with tags

**Deliverable**: All backend services updated and tested

### Phase 3: API Endpoints (Agent 3) - AFTER Phase 2

**Dependencies**: Phase 2 complete

**Blocks**: Phase 4 (Frontend)

5. **Generate route updates** (steps 7.1-7.3)

   - Add new parameters (question_count, weighting_rules, focus_on_uncertain)
   - Integrate weighting rule generation
   - Update mock exam creation to use MockExam model
   - Link individual questions to MockExam

6. **Question update endpoint** (step 8)

   - Add PATCH `/api/questions/{question_id}` endpoint
   - Handle updates to tags and confidence

7. **Reference content tagging endpoint** (step 9)

   - Add PATCH `/api/reference-content/{chunk_id}` endpoint
   - Store updates in user_overrides, return merged metadata

8. **Mock exam endpoints** (step 18)

   - Add GET `/api/mock-exams/{mock_exam_id}`
   - Add GET `/api/classes/{class_id}/mock-exams`
   - Add PATCH `/api/mock-exams/{mock_exam_id}`

9. **Update response models** (step 17)

   - Update `GenerateResponse` to include mock_exam_id, weighting_rules

**Deliverable**: All API endpoints implemented and documented

### Phase 4: Frontend Types and UI (Agent 4) - AFTER Phase 3

**Dependencies**: Phase 3 complete (API contracts defined)

**Blocks**: None

10. **TypeScript types** (step 12)

    - Update `Question` interface with new fields
    - Add `MockExam` interface
    - Add `ReferenceChunk` interface
    - Update `GenerateResponse` type

11. **Generate page UI** (step 11)

    - Add weighting controls (Auto/Custom/Advanced modes)
    - Add question count selector
    - Add confidence focus toggle
    - Update form submission to include new parameters

12. **ClassQuestions page updates** (steps 13.1-13.3)

    - Update mock exam display to show as objects
    - Add confidence selector UI
    - Implement topic-based grouping (display only)

13. **Question tagging UI** (step 14)

    - Add edit mode for question tags
    - Implement slideset/slide/topic inputs with validation

14. **Reference content tagging UI** (step 15)

    - Add tagging interface to ReferenceContent page
    - Show auto_tags vs user_overrides
    - Implement bulk tagging

**Deliverable**: All frontend UI components implemented

### Phase 5: Data Migration (Agent 5) - AFTER Phase 1 & 2

**Dependencies**: Phase 1 (schema) and Phase 2 (services) complete

**Blocks**: None (can run in parallel with Phase 3-4)

15. **Migration script** (step 16)

    - Create migration to convert existing mock exam data
    - Parse exam_content and create MockExam objects
    - Create individual Question entries linked to MockExam
    - Extract and migrate tags from existing metadata
    - Update ChromaDB chunk metadata with new structure

**Deliverable**: Migration script ready, can be run after all code is deployed

## Agent Work Summary

**Agent 1 (Database)**:

- Tasks: 1
- Files: `app/db/models.py`, `app/models/embedding_models.py`, migration scripts
- Must complete before others can proceed

**Agent 2 (Backend Services)**:

- Tasks: 2, 3, 4
- Files: `app/services/tagging_service.py`, `app/services/retrieval_service.py`, `app/services/generation_service.py`, `app/services/embedding_service.py`
- Can start after Agent 1 completes Phase 1
- Must complete before Agent 3 starts

**Agent 3 (API)**:

- Tasks: 5, 6, 7, 8, 9
- Files: `app/routes/generate.py`, `app/api/questions.py`, `app/api/reference_content.py` (or new `app/api/mock_exams.py`), `app/models/generation_models.py`
- Can start after Agent 2 completes Phase 2
- Must complete before Agent 4 starts

**Agent 4 (Frontend)**:

- Tasks: 10, 11, 12, 13, 14
- Files: `frontend/src/types/question.ts`, `frontend/src/pages/Generate.tsx`, `frontend/src/pages/ClassQuestions.tsx`, `frontend/src/pages/ReferenceContent.tsx`
- Can start after Agent 3 completes Phase 3
- No blocking dependencies for others

**Agent 5 (Migration)**:

- Tasks: 15
- Files: `migrations/add_mock_exam_fields.py`
- Can start after Agent 1 and Agent 2 complete
- Can run in parallel with Agent 3-4
- Should be executed last (after code deployment)

## Conflict Prevention

1. **Database schema changes** (Agent 1) must be completed and migrated before any code that uses new models
2. **Service layer** (Agent 2) must be complete before API layer (Agent 3) can use new methods
3. **API contracts** (Agent 3) must be finalized before frontend (Agent 4) can implement UI
4. **Migration script** (Agent 5) should be written after schema is stable but can be executed last
5. **File ownership**: Each agent owns specific files - avoid simultaneous edits to the same file
6. **Shared interfaces**: Agent 2 and Agent 3 should coordinate on method signatures; Agent 3 and Agent 4 should coordinate on API contracts

## Key Design Decisions

1. **Dynamic Weighting**: Weighting rules are inferred from exam structure (exam_type, exam_format) but can be overridden. Supports both simple (pre/post) and advanced (slide ranges) weighting.

2. **Chunk Metadata Structure**: Chunks have `auto_tags` (for audit) and `user_overrides` (for manual control). Effective metadata merges both with user_overrides taking precedence.

3. **Mock Exam as Object**: Mock exams are now first-class objects containing questions, making it easier to manage exam structure, weighting rules, and metadata separately from individual questions.

4. **Tagging Strategy**: Tags are stored both in dedicated columns (for querying) and in metadata JSON (for flexibility). Auto-extraction from reference metadata with manual override capability.

5. **Confidence Tracking**: Stored per-question in database, allowing the system to learn which topics need more practice over time.

6. **Topic Grouping**: Display-only grouping maintains exam structure while providing better organization in the UI.

7. **Slide as Subset**: Slide numbers are validated to be within their slideset, maintaining the hierarchical relationship.