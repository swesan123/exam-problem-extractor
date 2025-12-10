# Frontend & Class Management Implementation Plan

## Overview
This document outlines the step-by-step implementation plan for adding frontend and class management features to the exam-problem-extractor.

## Phase 1: Backend Foundation (Issues #27-31)

### Issue #27: Database Setup
**Priority**: High  
**Estimated Time**: 2-3 hours

1. Install SQLAlchemy
2. Create database models:
   - `Class` model
   - `Question` model
3. Set up database connection
4. Create database initialization script
5. Add migration support (Alembic)

**Files to Create:**
- `app/db/database.py` - Database connection and session
- `app/db/models.py` - SQLAlchemy models
- `app/db/base.py` - Base model class

### Issue #28: Class Management API
**Priority**: High  
**Estimated Time**: 3-4 hours

1. Create Pydantic models for classes
2. Implement class service
3. Create API routes for class CRUD
4. Add error handling
5. Write tests

**Files to Create:**
- `app/models/class_models.py`
- `app/services/class_service.py`
- `app/api/classes.py`

### Issue #29: Question Management API
**Priority**: High  
**Estimated Time**: 3-4 hours

1. Create Pydantic models for questions
2. Implement question service
3. Create API routes for question CRUD
4. Link questions to classes
5. Add pagination
6. Write tests

**Files to Create:**
- `app/models/question_models.py`
- `app/services/question_service.py`
- `app/api/questions.py`

### Issue #30: Extend Generate Endpoint
**Priority**: High  
**Estimated Time**: 2-3 hours

1. Add `class_id` parameter to generate endpoint
2. Auto-save generated questions
3. Update response model
4. Update tests

**Files to Modify:**
- `app/routes/generate.py`
- `app/models/generation_models.py`

### Issue #31: File Export Service
**Priority**: Medium  
**Estimated Time**: 4-5 hours

1. Implement export service
2. Support TXT format (required)
3. Support PDF, DOCX, JSON (optional)
4. Create export endpoint
5. Add file cleanup

**Files to Create:**
- `app/services/export_service.py`
- `app/api/export.py`
- `app/utils/export_formatters.py`

## Phase 2: Frontend Setup (Issue #32)

### Issue #32: React Application Setup
**Priority**: High  
**Estimated Time**: 2-3 hours

1. Initialize React app with Vite
2. Configure TypeScript
3. Set up Tailwind CSS
4. Configure routing
5. Set up API client
6. Create base layout

**Commands:**
```bash
cd frontend
npm create vite@latest . -- --template react-ts
npm install
npm install -D tailwindcss postcss autoprefixer
npm install react-router-dom axios
```

**Files to Create:**
- `frontend/package.json`
- `frontend/vite.config.ts`
- `frontend/tsconfig.json`
- `frontend/tailwind.config.js`
- `frontend/src/main.tsx`
- `frontend/src/App.tsx`
- `frontend/src/services/api.ts`

## Phase 3: Frontend Features (Issues #33-35)

### Issue #33: Class Management UI
**Priority**: High  
**Estimated Time**: 4-5 hours

1. Create class list component
2. Create class form component
3. Add edit/delete functionality
4. Add loading and error states
5. Style with Tailwind

**Files to Create:**
- `frontend/src/pages/ClassesPage.tsx`
- `frontend/src/components/ClassList.tsx`
- `frontend/src/components/ClassForm.tsx`
- `frontend/src/components/ClassCard.tsx`

### Issue #34: Question Generation UI
**Priority**: High  
**Estimated Time**: 5-6 hours

1. Create image upload component
2. Add class selector
3. Create generation form
4. Add question preview
5. Implement auto-save
6. Add notifications

**Files to Create:**
- `frontend/src/pages/GeneratePage.tsx`
- `frontend/src/components/ImageUpload.tsx`
- `frontend/src/components/ClassSelector.tsx`
- `frontend/src/components/QuestionPreview.tsx`

### Issue #35: Question List and Export UI
**Priority**: Medium  
**Estimated Time**: 4-5 hours

1. Create question list component
2. Add filtering and search
3. Create export UI
4. Implement download functionality
5. Add question preview/edit

**Files to Create:**
- `frontend/src/pages/QuestionsPage.tsx`
- `frontend/src/components/QuestionList.tsx`
- `frontend/src/components/ExportDialog.tsx`
- `frontend/src/components/QuestionCard.tsx`

## Implementation Order

### Week 1: Backend Foundation
1. ✅ Issue #27: Database Setup
2. ✅ Issue #28: Class Management API
3. ✅ Issue #29: Question Management API
4. ✅ Issue #30: Extend Generate Endpoint

### Week 2: Export & Frontend Setup
5. ✅ Issue #31: File Export Service
6. ✅ Issue #32: React Application Setup

### Week 3: Frontend Features
7. ✅ Issue #33: Class Management UI
8. ✅ Issue #34: Question Generation UI
9. ✅ Issue #35: Question List and Export UI

## Testing Strategy

### Backend Tests
- Unit tests for services
- Integration tests for API endpoints
- Database tests

### Frontend Tests
- Component tests
- Integration tests
- E2E tests (optional)

## Dependencies to Add

### Backend
```txt
sqlalchemy>=2.0.0
python-docx>=1.1.0
reportlab>=4.0.0
```

### Frontend
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "axios": "^1.6.0",
    "file-saver": "^2.0.5"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "typescript": "^5.2.0",
    "vite": "^5.0.0",
    "tailwindcss": "^3.3.0"
  }
}
```

## Next Steps

1. Start with Issue #27 (Database Setup)
2. Work through backend issues sequentially
3. Set up frontend after backend APIs are ready
4. Build frontend features incrementally
5. Test each feature as it's completed

