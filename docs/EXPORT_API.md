# Export API Documentation

## Overview

The Export API allows you to export all questions from a class to various file formats (TXT, PDF, DOCX, JSON).

## Endpoint

### Export Class Questions

**GET** `/api/classes/{class_id}/export`

Export all questions from a class to a downloadable file.

#### Parameters

- **class_id** (path parameter, required): The ID of the class to export questions from
- **format** (query parameter, optional): Export format. Options: `txt`, `pdf`, `docx`, `json`. Default: `txt`
- **include_solutions** (query parameter, optional): Whether to include solutions in the export. Default: `false`

#### Response

Returns a file download with the appropriate content type and filename.

#### Example Requests

```bash
# Export to TXT format (default)
curl -X GET "http://localhost:8000/api/classes/class_123/export?format=txt" \
  --output questions.txt

# Export to PDF with solutions
curl -X GET "http://localhost:8000/api/classes/class_123/export?format=pdf&include_solutions=true" \
  --output questions.pdf

# Export to JSON
curl -X GET "http://localhost:8000/api/classes/class_123/export?format=json" \
  --output questions.json

# Export to DOCX
curl -X GET "http://localhost:8000/api/classes/class_123/export?format=docx" \
  --output questions.docx
```

#### Response Codes

- **200 OK**: Export successful, file returned
- **400 Bad Request**: Invalid format parameter
- **404 Not Found**: Class not found or no questions in class
- **500 Internal Server Error**: Export processing failed

#### Supported Formats

1. **TXT** (`text/plain`): Plain text format with formatted questions
2. **PDF** (`application/pdf`): PDF document with formatted questions
3. **DOCX** (`application/vnd.openxmlformats-officedocument.wordprocessingml.document`): Microsoft Word document
4. **JSON** (`application/json`): JSON format with structured question data

#### File Format Details

**TXT Format:**
```
================================================================================
EXAM QUESTIONS
================================================================================

Question 1
--------------------------------------------------------------------------------
What is 2 + 2?

Solution:
4

Question 2
--------------------------------------------------------------------------------
What is the capital of France?

Solution:
Paris
```

**JSON Format:**
```json
{
  "questions": [
    {
      "id": "q1",
      "question_text": "What is 2 + 2?",
      "solution": "4",
      "metadata": {"source": "test"},
      "created_at": "2025-12-10T12:00:00"
    }
  ],
  "total": 1
}
```

#### Error Responses

**Class Not Found:**
```json
{
  "detail": "Class with ID 'class_123' not found"
}
```

**No Questions:**
```json
{
  "detail": "No questions found for class 'class_123'"
}
```

**Invalid Format:**
```json
{
  "detail": "Unsupported format 'invalid'. Supported formats: txt, pdf, docx, json"
}
```

## Implementation Details

The export functionality is implemented in:
- `app/services/export_service.py`: Core export service with format-specific methods
- `app/api/classes.py`: API endpoint handler

The service supports:
- Multiple export formats
- Optional solution inclusion
- Proper file formatting
- Error handling

