# Frontend and Class Management System Design

## Overview

This document describes the design for a web frontend that allows users to:
1. Create and manage multiple classes
2. Store exam questions for each class
3. Select a class when extracting exam questions
4. Append extracted questions to a downloadable file per class

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React/Vue)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Class Mgmt   │  │ Question Gen │  │ File Export  │      │
│  │   UI         │  │     UI       │  │     UI       │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└───────────────────────┬─────────────────────────────────────┘
                        │ HTTP/REST API
┌───────────────────────▼─────────────────────────────────────┐
│              FastAPI Backend (Extended)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Class API    │  │ Question API │  │ File API     │      │
│  │ /classes     │  │ /generate    │  │ /export      │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
┌───────▼────┐  ┌───────▼────┐  ┌───────▼────┐
│  SQLite/   │  │  Vector DB │  │  File      │
│  JSON DB   │  │  (ChromaDB)│  │  Storage   │
│  (Classes) │  │  (Questions)│  │  (Exports) │
└────────────┘  └────────────┘  └────────────┘
```

## Components

### 1. Frontend Application

**Technology Stack:**
- **Framework**: React (or Vue.js) with TypeScript
- **UI Library**: Tailwind CSS + shadcn/ui (or Material-UI)
- **State Management**: React Query / Zustand (or Pinia for Vue)
- **HTTP Client**: Axios or Fetch API
- **File Handling**: FileSaver.js for downloads

**Key Pages/Components:**

1. **Dashboard**
   - List of all classes
   - Quick stats (total questions per class)
   - Create new class button

2. **Class Management**
   - Create/Edit/Delete classes
   - Class metadata (name, description, subject)
   - View questions in class

3. **Question Generation**
   - Image upload interface
   - Class selector dropdown
   - Generation options (include solution, etc.)
   - Preview generated question
   - Save to class

4. **Question List View**
   - Filter by class
   - Search questions
   - Edit/Delete questions
   - Bulk operations

5. **Export/Download**
   - Select class
   - Choose format (TXT, PDF, DOCX, JSON)
   - Download button

### 2. Backend API Extensions

**New Endpoints:**

#### Class Management
```
GET    /api/classes              - List all classes
POST   /api/classes              - Create new class
GET    /api/classes/{class_id}   - Get class details
PUT    /api/classes/{class_id}   - Update class
DELETE /api/classes/{class_id}   - Delete class
```

#### Question Management
```
GET    /api/classes/{class_id}/questions  - List questions in class
POST   /api/classes/{class_id}/questions  - Add question to class
GET    /api/questions/{question_id}       - Get question details
PUT    /api/questions/{question_id}       - Update question
DELETE /api/questions/{question_id}       - Delete question
```

#### File Export
```
GET    /api/classes/{class_id}/export     - Export class questions
POST   /api/generate                      - Generate question (extended)
```

**Data Models:**

```python
class Class(BaseModel):
    id: str
    name: str
    description: Optional[str]
    subject: Optional[str]
    created_at: datetime
    updated_at: datetime
    question_count: int

class Question(BaseModel):
    id: str
    class_id: str
    question_text: str
    solution: Optional[str]
    metadata: dict
    created_at: datetime
    source_image: Optional[str]  # Path to original image if available
```

### 3. Data Storage

**Option A: SQLite Database (Recommended)**
- Lightweight, file-based
- Easy to backup
- Good for small-medium scale
- Tables: `classes`, `questions`, `class_questions` (junction)

**Option B: JSON File Storage**
- Simple, no dependencies
- Easy to read/edit manually
- Good for very small scale
- Structure: `data/classes.json`, `data/questions.json`

**Option C: Extend ChromaDB**
- Use ChromaDB metadata for class association
- Store questions in ChromaDB with class_id metadata
- Export from ChromaDB queries

**Recommendation**: Start with SQLite for structured data, keep ChromaDB for vector search.

### 4. File Export System

**Storage:**
- Generated files stored in `exports/` directory
- Format: `exports/{class_id}_{timestamp}.{ext}`
- Or generate on-demand (no storage)

**Formats:**
1. **TXT** - Plain text, simple formatting
2. **PDF** - Formatted document (using reportlab or weasyprint)
3. **DOCX** - Word document (using python-docx)
4. **JSON** - Structured data export
5. **Markdown** - Markdown formatted

**File Structure (TXT example):**
```
Class: Mathematics 101
Generated: 2025-12-10 12:00:00

Question 1:
[Question text here]

Solution:
[Solution text here]

---

Question 2:
[Question text here]

---
```

## Data Flow

### Question Generation Flow

```
1. User uploads image → Frontend
2. Frontend sends to POST /api/generate with class_id
3. Backend:
   a. Performs OCR
   b. Retrieves similar questions (from selected class if specified)
   c. Generates question
   d. Saves to database with class_id
   e. Returns question
4. Frontend displays question
5. User confirms → Question saved to class
6. Question appended to class export file
```

### Export Flow

```
1. User selects class → Frontend
2. Frontend requests GET /api/classes/{class_id}/export?format=txt
3. Backend:
   a. Queries all questions for class
   b. Formats according to requested format
   c. Generates file (or returns stream)
   d. Returns file download
4. Frontend triggers download
```

## API Design

### Extended Generate Endpoint

```python
POST /api/generate
{
    "image_file": <file>,
    "class_id": "class_123",  # NEW: Optional class selection
    "ocr_text": "optional text",
    "include_solution": false,
    "auto_save": true  # NEW: Auto-save to class
}

Response:
{
    "question": "...",
    "metadata": {...},
    "question_id": "q_123",  # NEW: ID if auto-saved
    "class_id": "class_123"  # NEW: Class it was saved to
}
```

### Class Management Endpoints

```python
# List classes
GET /api/classes
Response: {
    "classes": [
        {
            "id": "class_123",
            "name": "Mathematics 101",
            "description": "Intro to Calculus",
            "question_count": 45,
            "created_at": "2025-12-10T12:00:00Z"
        }
    ]
}

# Create class
POST /api/classes
{
    "name": "Mathematics 101",
    "description": "Intro to Calculus",
    "subject": "Mathematics"
}

# Get class questions
GET /api/classes/{class_id}/questions?page=1&limit=20
Response: {
    "questions": [...],
    "total": 45,
    "page": 1
}
```

### Export Endpoint

```python
GET /api/classes/{class_id}/export?format=txt&include_solutions=true
Response: File download (Content-Type: text/plain)
```

## Frontend State Management

### State Structure

```typescript
interface AppState {
  classes: Class[];
  selectedClass: Class | null;
  questions: Question[];
  currentQuestion: Question | null;
  exportFormat: 'txt' | 'pdf' | 'docx' | 'json';
}
```

### Key Actions

- `fetchClasses()` - Load all classes
- `createClass(data)` - Create new class
- `selectClass(classId)` - Set active class
- `generateQuestion(image, classId)` - Generate and save
- `exportClass(classId, format)` - Download export

## Security Considerations

1. **File Upload Validation**
   - Validate file types and sizes
   - Sanitize filenames
   - Limit upload rate

2. **Class Access Control** (Future)
   - User authentication
   - Class ownership/permissions
   - Private vs public classes

3. **Export Security**
   - Validate class_id ownership
   - Rate limit exports
   - Sanitize file paths

## Scalability Considerations

1. **Database**
   - Index on class_id for fast queries
   - Pagination for question lists
   - Archive old questions

2. **File Storage**
   - Clean up old export files
   - Consider cloud storage (S3) for large scale
   - Generate exports on-demand vs pre-generate

3. **Frontend**
   - Lazy load question lists
   - Virtual scrolling for large lists
   - Cache class data

## Implementation Plan

### Phase 1: Backend Foundation
1. Add SQLite database setup
2. Create class and question models
3. Implement class management API
4. Extend generate endpoint with class_id
5. Implement question storage

### Phase 2: Export System
1. Implement file generation (TXT first)
2. Add export endpoint
3. Support multiple formats
4. Add file cleanup job

### Phase 3: Frontend Setup
1. Initialize React/Vue project
2. Set up routing
3. Create base components
4. Implement API client

### Phase 4: Frontend Features
1. Class management UI
2. Question generation UI
3. Question list view
4. Export/download UI

### Phase 5: Polish
1. Error handling
2. Loading states
3. Responsive design
4. Testing

## Technology Recommendations

### Backend
- **Database**: SQLite with SQLAlchemy ORM
- **File Generation**: 
  - TXT: Built-in Python
  - PDF: reportlab or weasyprint
  - DOCX: python-docx
  - Markdown: Built-in

### Frontend
- **Framework**: React 18+ with TypeScript
- **Build Tool**: Vite
- **UI**: Tailwind CSS + shadcn/ui
- **State**: React Query + Zustand
- **Forms**: React Hook Form
- **File Upload**: react-dropzone

## File Structure

```
exam-problem-extractor/
├── app/
│   ├── api/              # NEW: API routes
│   │   ├── classes.py
│   │   ├── questions.py
│   │   └── export.py
│   ├── models/           # NEW: Database models
│   │   ├── class_model.py
│   │   └── question_model.py
│   ├── services/         # NEW: Business logic
│   │   ├── class_service.py
│   │   ├── question_service.py
│   │   └── export_service.py
│   └── db/               # NEW: Database setup
│       ├── database.py
│       └── migrations/
├── frontend/             # NEW: Frontend app
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── types/
│   └── package.json
├── exports/              # NEW: Generated files
└── data/                 # NEW: SQLite database
    └── app.db
```

## Testing Strategy

1. **Backend Tests**
   - Unit tests for services
   - API endpoint tests
   - Database integration tests

2. **Frontend Tests**
   - Component tests (React Testing Library)
   - Integration tests
   - E2E tests (Playwright/Cypress)

3. **Manual Testing**
   - Full workflow testing
   - Cross-browser testing
   - File format validation

## Future Enhancements

1. **User Authentication**
   - Multi-user support
   - Class sharing
   - Permissions

2. **Advanced Features**
   - Question templates
   - Bulk import/export
   - Question versioning
   - Search within questions

3. **Analytics**
   - Question generation stats
   - Class usage metrics
   - Export history

4. **Collaboration**
   - Share classes with others
   - Comments on questions
   - Question review workflow

