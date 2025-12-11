# Frontend Improvements Design

## Overview
This document outlines the design for improving the frontend user experience with enhanced file upload capabilities, better UI styling, and improved navigation.

## Requirements

### 1. Fix Reference Content Page
- **Issue**: Page goes black when clicked (function order issue - already fixed)
- **Status**: ✅ Fixed (function order corrected)

### 2. Add Context Textbox for Images in Generate
- **Requirement**: Allow users to provide additional context when generating questions from images
- **Implementation**: Add optional `retrieved_context` textarea field
- **Location**: Generate page input form

### 3. Change Textbox Colors from Black to White
- **Requirement**: All textareas and input fields should have white background
- **Current**: Default Tailwind styling (white by default, but text might be black)
- **Implementation**: Ensure all inputs have explicit white background and dark text

### 4. Enhanced File Upload in Generate Page
- **Requirement**: Add drag-and-drop, multi-file support, and clipboard paste
- **Features**:
  - Drag and drop PDFs and images
  - Click to select files
  - Paste from clipboard (Ctrl+V / Cmd+V)
  - Support multiple files
  - Show file preview/status
- **Similar to**: ReferenceContent page functionality

### 5. Questions Navigation
- **Issue**: Questions are stored but not easily accessible from class details
- **Current**: Questions accessible via `/classes/:id/questions` route
- **Solution**: Add "View Questions" button/link in ClassDetails page

## Architecture

### Component Structure

```
Generate.tsx
├── File Upload Zone (drag & drop, paste, click)
│   ├── File list with status
│   └── File removal
├── Context Textbox (optional)
├── Class Selection
├── Options (include solution)
└── Generate Button

ClassDetails.tsx
├── Class Information
├── View Questions Button (NEW)
└── Back to Classes Link
```

### Data Flow

```
Generate Page:
1. User uploads file(s) or pastes image
2. Files are stored in state
3. User optionally provides context text
4. User selects class (optional)
5. On submit:
   - If image/file: OCR → Retrieval → Generation
   - If context provided: Use context directly
   - Save to class if selected

ClassDetails Page:
1. Display class info
2. Show "View Questions" button
3. Navigate to /classes/:id/questions
```

## Implementation Plan

### Phase 1: Generate Page Enhancements
1. Add drag-and-drop zone
2. Add clipboard paste support
3. Add context textbox
4. Support multiple files
5. Update styling (white backgrounds)

### Phase 2: Navigation Improvements
1. Add "View Questions" link to ClassDetails
2. Ensure proper routing

### Phase 3: Styling Updates
1. Update all textareas to white background
2. Update all inputs to white background
3. Ensure proper text contrast

## API Changes

### Generate Endpoint
- Already supports `retrieved_context` as optional Form field
- Already supports `image_file` as File upload
- No backend changes needed

## UI/UX Considerations

### File Upload Zone
- Visual feedback for drag-over state
- File list with status indicators
- Support for both images and PDFs
- Clear instructions for all upload methods

### Context Textbox
- Optional field
- Placeholder text explaining usage
- Multi-line support

### Navigation
- Clear path from class to questions
- Breadcrumb or back navigation
- Question count display

## Testing Considerations

1. Test drag-and-drop with multiple files
2. Test clipboard paste
3. Test context textbox functionality
4. Test navigation from class to questions
5. Test styling across all pages

