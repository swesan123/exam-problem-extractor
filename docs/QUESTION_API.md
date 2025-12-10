# Question Management API Documentation

## Overview

The Question Management API provides endpoints for creating, reading, updating, and deleting exam questions. Questions are associated with classes.

## Base URL

All endpoints are prefixed with `/api/questions`

## Endpoints

### List Questions

**GET** `/api/questions`

List all questions with optional class filter and pagination.

**Query Parameters:**
- `class_id` (string, optional): Filter by class ID
- `page` (int, optional): Page number (default: 1, min: 1)
- `limit` (int, optional): Number of items per page (default: 20, min: 1, max: 100)

**Response:** `200 OK`
```json
{
  "questions": [
    {
      "id": "q_abc123",
      "class_id": "class_xyz789",
      "question_text": "What is 2+2?",
      "solution": "4",
      "metadata": {"difficulty": "easy"},
      "source_image": null,
      "created_at": "2025-12-10T12:00:00Z",
      "updated_at": "2025-12-10T12:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "limit": 20
}
```

**Example:**
```bash
curl "http://localhost:8000/api/questions?class_id=class_xyz789&page=1&limit=10"
```

### List Questions by Class

**GET** `/api/questions/classes/{class_id}/questions`

List all questions for a specific class.

**Path Parameters:**
- `class_id` (string): Class ID

**Query Parameters:**
- `page` (int, optional): Page number (default: 1)
- `limit` (int, optional): Number of items per page (default: 20)

**Response:** `200 OK`
```json
{
  "questions": [...],
  "total": 15,
  "page": 1,
  "limit": 20
}
```

**Example:**
```bash
curl "http://localhost:8000/api/questions/classes/class_xyz789/questions?page=1&limit=10"
```

### Create Question

**POST** `/api/questions/classes/{class_id}/questions`

Create a new question in a class.

**Path Parameters:**
- `class_id` (string): Class ID

**Request Body:**
```json
{
  "class_id": "class_xyz789",
  "question_text": "What is 2+2?",
  "solution": "4",
  "metadata": {"difficulty": "easy", "topics": ["arithmetic"]},
  "source_image": "path/to/image.png"
}
```

**Fields:**
- `class_id` (string, required): Must match path parameter
- `question_text` (string, required): The question text (min 1 character)
- `solution` (string, optional): Solution to the question
- `metadata` (object, optional): Additional metadata (JSON object)
- `source_image` (string, optional): Path to original image if available

**Response:** `201 Created`
```json
{
  "id": "q_abc123",
  "class_id": "class_xyz789",
  "question_text": "What is 2+2?",
  "solution": "4",
  "metadata": {"difficulty": "easy"},
  "source_image": null,
  "created_at": "2025-12-10T12:00:00Z",
  "updated_at": "2025-12-10T12:00:00Z"
}
```

**Errors:**
- `400 Bad Request`: Class not found or class_id mismatch
- `500 Internal Server Error`: Server error

**Example:**
```bash
curl -X POST http://localhost:8000/api/questions/classes/class_xyz789/questions \
  -H "Content-Type: application/json" \
  -d '{
    "class_id": "class_xyz789",
    "question_text": "What is 2+2?",
    "solution": "4"
  }'
```

### Get Question

**GET** `/api/questions/{question_id}`

Get a specific question by ID.

**Path Parameters:**
- `question_id` (string): Question ID

**Response:** `200 OK`
```json
{
  "id": "q_abc123",
  "class_id": "class_xyz789",
  "question_text": "What is 2+2?",
  "solution": "4",
  "metadata": {"difficulty": "easy"},
  "source_image": null,
  "created_at": "2025-12-10T12:00:00Z",
  "updated_at": "2025-12-10T12:00:00Z"
}
```

**Errors:**
- `404 Not Found`: Question not found
- `500 Internal Server Error`: Server error

**Example:**
```bash
curl http://localhost:8000/api/questions/q_abc123
```

### Update Question

**PUT** `/api/questions/{question_id}`

Update a question. All fields are optional - only provided fields will be updated.

**Path Parameters:**
- `question_id` (string): Question ID

**Request Body:**
```json
{
  "question_text": "Updated question text",
  "solution": "Updated solution",
  "metadata": {"difficulty": "hard"}
}
```

**Response:** `200 OK`
```json
{
  "id": "q_abc123",
  "class_id": "class_xyz789",
  "question_text": "Updated question text",
  "solution": "Updated solution",
  "metadata": {"difficulty": "hard"},
  "created_at": "2025-12-10T12:00:00Z",
  "updated_at": "2025-12-10T12:30:00Z"
}
```

**Errors:**
- `404 Not Found`: Question not found
- `500 Internal Server Error`: Server error

**Example:**
```bash
curl -X PUT http://localhost:8000/api/questions/q_abc123 \
  -H "Content-Type: application/json" \
  -d '{
    "question_text": "Updated question text",
    "solution": "Updated solution"
  }'
```

### Delete Question

**DELETE** `/api/questions/{question_id}`

Delete a question.

**Path Parameters:**
- `question_id` (string): Question ID

**Response:** `204 No Content`

**Errors:**
- `404 Not Found`: Question not found
- `500 Internal Server Error`: Server error

**Example:**
```bash
curl -X DELETE http://localhost:8000/api/questions/q_abc123
```

## Data Models

### QuestionCreate
```python
{
  "class_id": str,           # Required
  "question_text": str,      # Required, min 1 char
  "solution": str | None,    # Optional
  "metadata": dict | None,   # Optional, JSON object
  "source_image": str | None # Optional
}
```

### QuestionUpdate
```python
{
  "question_text": str | None,    # Optional, min 1 char
  "solution": str | None,         # Optional
  "metadata": dict | None,        # Optional
  "source_image": str | None      # Optional
}
```

### QuestionResponse
```python
{
  "id": str,
  "class_id": str,
  "question_text": str,
  "solution": str | None,
  "metadata": dict | None,
  "source_image": str | None,
  "created_at": datetime,
  "updated_at": datetime
}
```

## Notes

- Questions must belong to an existing class
- Metadata can store arbitrary JSON data (difficulty, topics, points, etc.)
- Timestamps are automatically managed
- Pagination uses 1-based page numbers

