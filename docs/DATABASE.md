# Database Documentation

## Overview

The application uses SQLite with SQLAlchemy ORM for storing classes and questions. The database is automatically initialized on application startup.

## Database Location

- **Path**: `./data/app.db`
- **Type**: SQLite
- **ORM**: SQLAlchemy 2.0+

## Models

### Class Model

Represents a class/course that contains exam questions.

**Fields:**
- `id` (String, Primary Key): Unique identifier for the class
- `name` (String, Required): Name of the class
- `description` (Text, Optional): Description of the class
- `subject` (String, Optional): Subject area (e.g., "Mathematics")
- `created_at` (DateTime): Timestamp when class was created
- `updated_at` (DateTime): Timestamp when class was last updated

**Relationships:**
- `questions`: One-to-many relationship with Question model

**Example:**
```python
from app.db.models import Class
from app.db.database import SessionLocal

db = SessionLocal()
class_obj = Class(
    id="math_101",
    name="Mathematics 101",
    description="Introduction to Calculus",
    subject="Mathematics"
)
db.add(class_obj)
db.commit()
```

### Question Model

Represents an exam question associated with a class.

**Fields:**
- `id` (String, Primary Key): Unique identifier for the question
- `class_id` (String, Foreign Key, Required): ID of the associated class
- `question_text` (Text, Required): The question text
- `solution` (Text, Optional): Solution to the question
- `metadata` (JSON, Optional): Additional metadata (difficulty, topics, etc.)
- `source_image` (String, Optional): Path to original image if available
- `created_at` (DateTime): Timestamp when question was created
- `updated_at` (DateTime): Timestamp when question was last updated

**Relationships:**
- `class_obj`: Many-to-one relationship with Class model

**Example:**
```python
from app.db.models import Question

question = Question(
    id="q_001",
    class_id="math_101",
    question_text="Find the derivative of f(x) = x^2",
    solution="f'(x) = 2x",
    metadata={"difficulty": "easy", "topics": ["calculus", "derivatives"]}
)
db.add(question)
db.commit()
```

## Database Operations

### Getting a Database Session

Use FastAPI's dependency injection:

```python
from fastapi import Depends
from app.db.database import get_db
from sqlalchemy.orm import Session

@app.get("/items")
async def get_items(db: Session = Depends(get_db)):
    # Use db session here
    items = db.query(Class).all()
    return items
```

### Initialization

The database is automatically initialized on application startup via the `lifespan` function in `app/main.py`.

To manually initialize:

```python
from app.db.database import init_db

init_db()
```

### Dropping Tables

**Warning**: This will delete all data!

```python
from app.db.database import drop_db

drop_db()
```

## Relationships

### Class → Questions (One-to-Many)

```python
class_obj = db.query(Class).filter_by(id="math_101").first()
questions = class_obj.questions  # List of Question objects
```

### Question → Class (Many-to-One)

```python
question = db.query(Question).filter_by(id="q_001").first()
class_obj = question.class_obj  # Class object
```

### Cascade Delete

When a class is deleted, all associated questions are automatically deleted:

```python
class_obj = db.query(Class).filter_by(id="math_101").first()
db.delete(class_obj)
db.commit()  # All questions in this class are also deleted
```

## Indexes

The following fields are indexed for performance:
- `Class.id`
- `Class.name`
- `Class.subject`
- `Question.id`
- `Question.class_id`

## Timestamps

Both models automatically set `created_at` and `updated_at` timestamps:
- `created_at`: Set when record is created
- `updated_at`: Set when record is created and updated on each modification

## Metadata Field

The `metadata` field in the Question model can store arbitrary JSON data:

```python
question.metadata = {
    "difficulty": "hard",
    "topics": ["calculus", "integration"],
    "points": 10,
    "estimated_time": "15 minutes"
}
```

## Best Practices

1. **Always use dependency injection** for database sessions in FastAPI routes
2. **Commit transactions** after making changes
3. **Handle exceptions** when working with the database
4. **Use relationships** instead of manual joins when possible
5. **Index frequently queried fields** (already done)

## Migration Support

For future migrations, consider using Alembic:

```bash
pip install alembic
alembic init alembic
```

This will be added in a future update.

## Testing

See `tests/test_database.py` for comprehensive database tests including:
- Model creation
- Relationships
- Cascade deletes
- Timestamps
- Metadata storage

