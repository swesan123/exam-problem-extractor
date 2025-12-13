---
name: Parallel Multi-Issue Implementation
overview: "Break down issues #57, #58, and #59 into separate branches that can be worked on in parallel. Each issue is independent and can be completed simultaneously by different agents/instances."
todos:
  - id: issue-57-class-cards
    content: "Update class cards: remove View Details, add View Questions and View References buttons"
    status: completed
  - id: issue-57-class-details
    content: Remove duplicate Add Reference button from ClassDetails empty state
    status: in_progress
  - id: issue-57-modal-naming
    content: Replace Exam Source/Type with single 'Name of reference' field in AddReferenceContentModal
    status: pending
  - id: issue-57-inline-files
    content: Display selected files inside dropzone with reference name and filename
    status: pending
    dependencies:
      - issue-57-modal-naming
  - id: issue-57-progress-box
    content: "Update ReferenceUploadProgress: black text, round loading circle, ETA, file names"
    status: pending
  - id: issue-58-db-model
    content: Create UploadMetrics database model for per-file metrics tracking
    status: completed
  - id: issue-58-metrics-service
    content: Create metrics_service.py with methods for tracking and calculating metrics
    status: completed
    dependencies:
      - issue-58-db-model
  - id: issue-58-processor-integration
    content: Integrate metrics tracking into reference_processor.py
    status: completed
    dependencies:
      - issue-58-metrics-service
  - id: issue-58-api-response
    content: Extend job API response to include ETA and metrics summary
    status: completed
    dependencies:
      - issue-58-processor-integration
  - id: issue-59-ui-audit
    content: Audit all frontend components for consistency and UX issues
    status: pending
  - id: issue-59-accessibility-audit
    content: "Perform accessibility checklist: keyboard nav, ARIA, contrast, labels"
    status: pending
  - id: issue-59-create-doc
    content: Create UI_UX_ACCESSIBILITY_AUDIT.md with findings and recommendations
    status: pending
    dependencies:
      - issue-59-ui-audit
      - issue-59-accessibility-audit
---

# Parallel Multi-Issue Implementation Plan

## Overview

Three independent issues can be worked on in parallel across separate branches:

- **Issue #57**: Frontend UX refresh (Classes & References)
- **Issue #58**: Backend analytics (Upload Performance Telemetry)
- **Issue #59**: UI/UX audit (Documentation only, no code)

## Branch Strategy

### Branch 1: `issue-57-classes-references-ux` (Frontend)

**Status**: Can work in parallel with #58 and #59

#### Tasks:

1. **Update Class Cards** (`frontend/src/pages/Classes.tsx`)

- Remove "View Details" link (line 119)
- Add "View Questions" button (already exists, line 122-126)
- Add "View References" button linking to `/classes/${id}` (ClassDetails page)
- Update button styling to match design system

2. **Update ClassDetails Page** (`frontend/src/pages/ClassDetails.tsx`)

- Remove duplicate "Add Reference Content" button from empty state (lines 166-171)
- Keep only the button beside the heading (lines 153-158)

3. **Update AddReferenceContentModal** (`frontend/src/components/AddReferenceContentModal.tsx`)

- Replace "Exam Source" and "Exam Type" inputs with single "Name of reference" field
- Update state: remove `examSource` and `examType`, add `referenceName`
- Update `handleProcessAll` to pass `referenceName` to job service
- Display selected files inside dropzone with:
- User-entered reference name
- Actual filename
- File chips/thumbnails

4. **Update ReferenceUploadProgress** (`frontend/src/components/ReferenceUploadProgress.tsx`)

- Change text color to black (currently white/gray)
- Add round loading circle with percentage display
- Add ETA display (from job status if available)
- List files with both reference name and actual filename
- Update styling for better readability

5. **Update Job Service** (`frontend/src/services/jobService.ts`)

- Update `uploadReferenceContent` to accept `referenceName` instead of `examSource`/`examType`
- Update TypeScript types accordingly

#### Files to Modify:

- `frontend/src/pages/Classes.tsx`
- `frontend/src/pages/ClassDetails.tsx`
- `frontend/src/components/AddReferenceContentModal.tsx`
- `frontend/src/components/ReferenceUploadProgress.tsx`
- `frontend/src/services/jobService.ts`

#### Dependencies:

- None (frontend-only changes)

---

### Branch 2: `issue-58-upload-analytics` (Backend)

**Status**: Can work in parallel with #57 and #59

#### Tasks:

1. **Extend Database Model** (`app/db/models.py`)

- Add `UploadMetrics` model to store per-file metrics:
- `id`, `job_id` (FK to ReferenceUploadJob)
- `filename`, `file_size_bytes`, `file_type`
- `page_count` (for PDFs), `upload_start_time`, `upload_end_time`
- `ocr_start_time`, `ocr_end_time`, `ocr_duration_ms`
- `chunking_start_time`, `chunking_end_time`, `chunking_duration_ms`
- `embedding_start_time`, `embedding_end_time`, `embedding_duration_ms`
- `storage_start_time`, `storage_end_time`, `storage_duration_ms`
- `total_duration_ms`, `network_throughput_bps` (calculated)
- `created_at`

2. **Create Metrics Service** (`app/services/metrics_service.py` - NEW)

- `create_file_metrics(job_id, filename, file_size, file_type) -> UploadMetrics`
- `update_upload_times(metrics_id, start_time, end_time)`
- `update_processing_step(metrics_id, step_name, start_time, end_time)`
- `calculate_throughput(file_size_bytes, duration_seconds) -> float`
- `get_job_metrics_summary(job_id) -> dict`

3. **Update Reference Processor** (`app/services/reference_processor.py`)

- Integrate metrics tracking in `_process_single_file`:
- Create metrics record at start
- Record timestamps for each processing step (OCR, chunking, embedding, storage)
- Update metrics after each step completes
- Calculate network throughput on upload completion

4. **Update Job Service** (`app/services/job_service.py`)

- Add method to retrieve metrics: `get_job_metrics(job_id) -> List[UploadMetrics]`
- Calculate ETA based on historical averages in `get_job_status`

5. **Update Job API** (`app/api/jobs.py`)

- Extend `GET /api/jobs/{job_id}` response to include:
- `estimated_completion_time` (ETA in seconds)
- `metrics_summary` (optional, per-file metrics)

6. **Update Job Models** (`app/models/job_models.py` - if exists, or create)

- Add `JobStatusResponse` with `estimated_completion_time` and `metrics_summary` fields

7. **Add Database Migration**

- Create migration script or update `app/db/database.py` to create `upload_metrics` table

#### Files to Modify/Create:

- `app/db/models.py` (add UploadMetrics model)
- `app/services/metrics_service.py` (NEW)
- `app/services/reference_processor.py` (integrate metrics)
- `app/services/job_service.py` (add metrics retrieval)
- `app/api/jobs.py` (extend response)
- `app/models/job_models.py` (NEW or update)
- Database migration script

#### Dependencies:

- None (backend-only, independent of frontend changes)

---

### Branch 3: `issue-59-ui-ux-audit` (Documentation)

**Status**: Can work in parallel with #57 and #58

#### Tasks:

1. **Audit Current UI** (Review all frontend components)

- Check consistency: spacing, typography, colors, input states, focus styles
- Review component files in `frontend/src/`:
- Pages: `Generate.tsx`, `Classes.tsx`, `ClassDetails.tsx`, `ClassQuestions.tsx`
- Components: All modals, forms, buttons, inputs

2. **Accessibility Checklist**

- Keyboard navigation (Tab order, Enter/Space on buttons)
- Focus indicators (visible focus rings)
- ARIA labels/roles (forms, buttons, modals)
- Color contrast (WCAG AA compliance)
- Form labels (all inputs have associated labels)
- Error messages (accessible, clear)

3. **Create Audit Document** (`docs/UI_UX_ACCESSIBILITY_AUDIT.md` - NEW)

- Findings organized by category:
- **Consistency Issues**: Spacing scale, typography hierarchy, color usage
- **Accessibility Issues**: Missing ARIA, poor contrast, keyboard traps
- **UX Issues**: Confusing flows, missing feedback, unclear states
- Recommendations with priority levels
- Code examples for fixes (no implementation)

4. **Propose UI Refinements**

- Spacing scale (Tailwind spacing tokens)
- Button/input style guide
- Focus ring patterns
- Hover/active state patterns
- Heading hierarchy
- Empty state patterns

#### Files to Create:

- `docs/UI_UX_ACCESSIBILITY_AUDIT.md`

#### Files to Review (Read-only):

- `frontend/src/pages/*.tsx`
- `frontend/src/components/*.tsx`
- `frontend/src/services/*.ts`

#### Dependencies:

- None (documentation only, no code changes)

---

## Workflow for Each Branch

For each branch, follow this sequence:

1. Create branch: `git checkout -b issue-{N}-{name}`
2. Implement changes
3. Run lint: `npm --prefix frontend run lint` (frontend) or `python -m pytest tests -q` (backend)
4. Cleanup unused code
5. Review code
6. Refactor if needed
7. Audit for issues
8. Make/run tests
9. Create PR: `/pr`
10. Merge PR
11. Close issue

## Parallelization Notes

- **#57 and #58**: Completely independent (frontend vs backend)
- **#59**: Independent audit that can inform future improvements
- All three can be worked on simultaneously without conflicts
- Merge order: Any order is fine, but recommend #59 first (documentation), then #57 and #58

## Testing Strategy

- **#57**: Frontend component tests, visual regression checks
- **#58**: Backend unit tests for metrics service, integration tests for job API
- **#59**: No tests needed (documentation only)