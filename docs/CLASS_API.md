# Class Management API Documentation

## Overview

The Class Management API provides endpoints for creating, reading, updating, and deleting classes. Classes are used to organize exam questions.

## Base URL

All endpoints are prefixed with `/api/classes`

## Endpoints

### List Classes

**GET** `/api/classes`

List all classes with pagination support.

**Query Parameters:**
- `skip` (int, optional): Number of records to skip (default: 0, min: 0)
- `limit` (int, optional): Maximum number of records to return (default: 100, min: 1, max: 100)

**Response:** `200 OK`
```json
{
  "classes": [
    {
      "id": "class_abc123",
      "name": "Mathematics 101",
      "description": "Introduction to Calculus",
      "subject": "Mathematics",
      "question_count": 15,
      "created_at": "2025-12-10T12:00:00Z",
      "updated_at": "2025-12-10T12:00:00Z"
    }
  ],
  "total": 1
}
```

**Example:**
```bash
curl http://localhost:8000/api/classes?skip=0&limit=10
```

### Create Class

**POST** `/api/classes`

Create a new class.

**Request Body:**
```json
{
  "name": "Mathematics 101",
  "description": "Introduction to Calculus",
  "subject": "Mathematics"
}
```

**Fields:**
- `name` (string, required): Class name (1-200 characters)
- `description` (string, optional): Class description (max 1000 characters)
- `subject` (string, optional): Subject area (max 100 characters)

**Response:** `201 Created`
```json
{
  "id": "class_abc123",
  "name": "Mathematics 101",
  "description": "Introduction to Calculus",
  "subject": "Mathematics",
  "question_count": 0,
  "created_at": "2025-12-10T12:00:00Z",
  "updated_at": "2025-12-10T12:00:00Z"
}
```

**Errors:**
- `400 Bad Request`: Class name already exists
- `500 Internal Server Error`: Server error

**Example:**
```bash
curl -X POST http://localhost:8000/api/classes \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Mathematics 101",
    "description": "Introduction to Calculus",
    "subject": "Mathematics"
  }'
```

### Get Class

**GET** `/api/classes/{class_id}`

Get a specific class by ID.

**Path Parameters:**
- `class_id` (string): Class ID

**Response:** `200 OK`
```json
{
  "id": "class_abc123",
  "name": "Mathematics 101",
  "description": "Introduction to Calculus",
  "subject": "Mathematics",
  "question_count": 15,
  "created_at": "2025-12-10T12:00:00Z",
  "updated_at": "2025-12-10T12:00:00Z"
}
```

**Errors:**
- `404 Not Found`: Class not found
- `500 Internal Server Error`: Server error

**Example:**
```bash
curl http://localhost:8000/api/classes/class_abc123
```

### Update Class

**PUT** `/api/classes/{class_id}`

Update a class. All fields are optional - only provided fields will be updated.

**Path Parameters:**
- `class_id` (string): Class ID

**Request Body:**
```json
{
  "name": "Updated Name",
  "description": "Updated description",
  "subject": "Updated Subject"
}
```

**Response:** `200 OK`
```json
{
  "id": "class_abc123",
  "name": "Updated Name",
  "description": "Updated description",
  "subject": "Updated Subject",
  "question_count": 15,
  "created_at": "2025-12-10T12:00:00Z",
  "updated_at": "2025-12-10T12:30:00Z"
}
```

**Errors:**
- `400 Bad Request`: New name conflicts with existing class
- `404 Not Found`: Class not found
- `500 Internal Server Error`: Server error

**Example:**
```bash
curl -X PUT http://localhost:8000/api/classes/class_abc123 \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Name",
    "description": "Updated description"
  }'
```

### Delete Class

**DELETE** `/api/classes/{class_id}`

Delete a class. This will also delete all questions associated with the class (cascade delete).

**Path Parameters:**
- `class_id` (string): Class ID

**Response:** `204 No Content`

**Errors:**
- `404 Not Found`: Class not found
- `500 Internal Server Error`: Server error

**Example:**
```bash
curl -X DELETE http://localhost:8000/api/classes/class_abc123
```

## Data Models

### ClassCreate
```python
{
  "name": str,           # Required, 1-200 chars
  "description": str,    # Optional, max 1000 chars
  "subject": str         # Optional, max 100 chars
}
```

### ClassUpdate
```python
{
  "name": str,           # Optional, 1-200 chars
  "description": str,    # Optional, max 1000 chars
  "subject": str         # Optional, max 100 chars
}
```

### ClassResponse
```python
{
  "id": str,
  "name": str,
  "description": str | None,
  "subject": str | None,
  "question_count": int,
  "created_at": datetime,
  "updated_at": datetime
}
```

## Error Responses

All errors follow this format:
```json
{
  "detail": "Error message here"
}
```

## Notes

- Class names must be unique
- Deleting a class will cascade delete all associated questions
- Question count is automatically calculated
- Timestamps are automatically managed

