# UI Improvements and Feature Enhancements Design

## Overview
This document outlines the design for UI improvements and feature enhancements including styling updates, question management, and reference content reorganization.

## Requirements

### 1. Styling Updates
- **Change all text boxes, input fields, checkboxes from black to white**
  - All `<input>`, `<textarea>`, `<select>` elements should have white backgrounds
  - Text should be dark (gray-900) for readability
  - Checkboxes should have white backgrounds with proper styling
  - Ensure consistent styling across all pages

### 2. Generate Page Enhancements
- **Multiple file support**: Already implemented, but ensure it processes all files
- **Drag and drop**: Already implemented
- **Copy and paste**: Already implemented
- **Context textbox**: Already exists, but add better labeling/help text

### 3. Question Management
- **Current State**: Questions are stored in database and accessible via `/classes/:id/questions`
- **Enhancements Needed**:
  - Show questions directly in ClassDetails page (preview/list)
  - Add download functionality for individual questions
  - Improve question display and organization
  - Add question deletion capability

### 4. Reference Content Management
- **Current State**: Reference content is stored in vector DB with metadata including `class_id`
- **Enhancements Needed**:
  - Show reference content under each class
  - Allow deletion of reference content
  - Move "Add Reference Content" functionality to ClassDetails page
  - Remove standalone ReferenceContent page or make it redirect to class-specific view

## Architecture

### Component Structure

```
ClassDetails.tsx
├── Class Information Display
├── Questions Section
│   ├── Question List/Preview
│   ├── View All Questions Link
│   ├── Download Questions Button
│   └── Individual Question Actions (view, download, delete)
├── Reference Content Section
│   ├── Reference Content List
│   ├── Add Reference Content Button/Modal
│   └── Delete Reference Content Actions
└── Edit Class Button

ClassQuestions.tsx (Enhanced)
├── Question List with Search
├── Individual Question Cards
│   ├── Question Text
│   ├── Solution (if available)
│   ├── Download Button
│   └── Delete Button
└── Export All Button
```

### Data Flow

```
Reference Content:
1. User navigates to ClassDetails
2. Click "Add Reference Content" → Opens modal/component
3. Upload files → OCR → Embed with class_id metadata
4. Reference content appears in list under class
5. User can delete reference content (removes from vector DB)

Questions:
1. Questions generated with class_id are stored in database
2. ClassDetails shows question count and preview
3. Click "View Questions" → Navigate to ClassQuestions
4. ClassQuestions shows all questions with download/delete options
5. Individual questions can be downloaded as text/PDF
```

## API Changes

### New Endpoints Needed

1. **List Reference Content by Class**
   ```
   GET /api/classes/{class_id}/reference-content
   Returns: List of reference content items with metadata
   ```

2. **Delete Reference Content**
   ```
   DELETE /api/reference-content/{chunk_id}
   Deletes embedding from vector DB
   ```

3. **Download Question**
   ```
   GET /api/questions/{question_id}/download?format=txt|pdf|docx
   Returns: File download
   ```

### Modified Endpoints

1. **List Questions by Class** (already exists)
   - Enhance to include download links
   - Add delete capability

## Implementation Plan

### Phase 1: Styling Updates
1. Update global CSS/Tailwind classes for inputs
2. Update all form components:
   - Generate.tsx
   - ReferenceContent.tsx
   - ClassDetails.tsx
   - ClassQuestions.tsx
   - All modals
3. Ensure checkboxes have white backgrounds
4. Test across all pages

### Phase 2: Question Management
1. Enhance ClassDetails to show question preview
2. Add download functionality to ClassQuestions
3. Add delete functionality to questions
4. Improve question display cards

### Phase 3: Reference Content Management
1. Create API endpoints for reference content management
2. Add reference content section to ClassDetails
3. Create "Add Reference Content" modal/component
4. Implement reference content deletion
5. Update navigation to remove standalone ReferenceContent page

### Phase 4: Integration and Testing
1. Test all new features
2. Update navigation/routing
3. Update documentation

## UI/UX Considerations

### Styling
- Consistent white backgrounds for all inputs
- Dark text (gray-900) for readability
- Proper focus states (blue ring)
- Accessible color contrast

### Reference Content
- Show source, exam type, upload date
- Allow filtering/searching
- Visual indicators for processing status
- Confirmation dialogs for deletion

### Questions
- Clear question/solution separation
- Download options (TXT, PDF, DOCX)
- Search and filter capabilities
- Bulk operations (export all, delete multiple)

## File Structure Changes

```
frontend/src/
├── pages/
│   ├── ClassDetails.tsx (enhanced)
│   ├── ClassQuestions.tsx (enhanced)
│   └── ReferenceContent.tsx (deprecated or repurposed)
├── components/
│   ├── AddReferenceContentModal.tsx (new)
│   ├── ReferenceContentList.tsx (new)
│   └── QuestionCard.tsx (new)
└── services/
    ├── referenceContentService.ts (new)
    └── questionService.ts (enhanced)

app/
├── api/
│   └── reference_content.py (new)
└── services/
    └── reference_content_service.py (new)
```

## Testing Considerations

1. Test styling across all browsers
2. Test file uploads (multiple files, drag/drop, paste)
3. Test question download in all formats
4. Test reference content CRUD operations
5. Test navigation and routing
6. Test responsive design

## Migration Notes

- Existing reference content will need to be queryable by class_id
- Questions already have class_id, no migration needed
- Update navigation to remove ReferenceContent link or redirect to classes

