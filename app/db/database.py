"""Database connection and session management."""

from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.config import settings

# Database URL - SQLite file (use absolute path from config)
# Resolve to absolute path to ensure consistency across different working directories
_db_path = settings.database_path.resolve()
DATABASE_URL = f"sqlite:///{_db_path}"

# Create engine with SQLite-specific configuration
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Needed for SQLite multi-threading
    echo=False,  # Set to True for SQL query logging (useful for debugging)
)

# Session factory - creates new sessions on each call
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all database models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session.

    Yields:
        Database session

    Note: Services are responsible for calling commit() explicitly.
    This function only ensures proper session cleanup and rollback on exceptions.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        # Rollback on any exception to prevent partial commits
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize database by creating all tables.
    Should be called on application startup.

    Creates the data directory if it doesn't exist and creates all
    database tables defined in the models.
    """
    # Ensure data directory exists
    data_dir = _db_path.parent
    data_dir.mkdir(parents=True, exist_ok=True)

    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Run migrations
    _run_migrations()


def _run_migrations() -> None:
    """
    Run database migrations to add new columns to existing tables.
    """
    from sqlalchemy import inspect, text
    
    try:
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        
        # Migration: Create mock_exams table if it doesn't exist
        if "mock_exams" not in table_names:
            with engine.begin() as conn:
                # SQLite doesn't support JSON type natively, use TEXT
                conn.execute(text("""
                    CREATE TABLE mock_exams (
                        id VARCHAR NOT NULL PRIMARY KEY,
                        class_id VARCHAR NOT NULL,
                        title VARCHAR,
                        instructions TEXT,
                        exam_format TEXT,
                        weighting_rules TEXT,
                        exam_metadata TEXT,
                        created_at DATETIME NOT NULL DEFAULT (datetime('now')),
                        updated_at DATETIME NOT NULL DEFAULT (datetime('now')),
                        FOREIGN KEY(class_id) REFERENCES classes (id) ON DELETE CASCADE
                    )
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_mock_exams_class_id ON mock_exams (class_id)"))
                
                import logging
                logger = logging.getLogger(__name__)
                logger.info("Migration: Created mock_exams table")
        
        # Migration: Add new columns to questions table if it exists
        if "questions" in table_names:
            existing_columns = [col["name"] for col in inspector.get_columns("questions")]
            migrations_applied = []
            
            with engine.begin() as conn:
                # Add mock_exam_id column
                if "mock_exam_id" not in existing_columns:
                    conn.execute(text("ALTER TABLE questions ADD COLUMN mock_exam_id VARCHAR"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_questions_mock_exam_id ON questions (mock_exam_id)"))
                    conn.execute(text("""
                        CREATE TRIGGER IF NOT EXISTS update_questions_updated_at 
                        AFTER UPDATE ON questions 
                        BEGIN 
                            UPDATE questions SET updated_at = datetime('now') WHERE id = NEW.id;
                        END
                    """))
                    migrations_applied.append("mock_exam_id")
                
                # Add slideset column
                if "slideset" not in existing_columns:
                    conn.execute(text("ALTER TABLE questions ADD COLUMN slideset VARCHAR"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_questions_slideset ON questions (slideset)"))
                    migrations_applied.append("slideset")
                
                # Add slide column
                if "slide" not in existing_columns:
                    conn.execute(text("ALTER TABLE questions ADD COLUMN slide INTEGER"))
                    migrations_applied.append("slide")
                
                # Add topic column
                if "topic" not in existing_columns:
                    conn.execute(text("ALTER TABLE questions ADD COLUMN topic VARCHAR"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_questions_topic ON questions (topic)"))
                    migrations_applied.append("topic")
                
                # Add user_confidence column
                if "user_confidence" not in existing_columns:
                    conn.execute(text("ALTER TABLE questions ADD COLUMN user_confidence VARCHAR"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_questions_user_confidence ON questions (user_confidence)"))
                    migrations_applied.append("user_confidence")
                
                if migrations_applied:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.info(f"Migration: Added columns to questions table: {', '.join(migrations_applied)}")
        
        # Migration: Add exam_format column to classes if it doesn't exist
        if "classes" in table_names:
            existing_columns = [col["name"] for col in inspector.get_columns("classes")]
            if "exam_format" not in existing_columns:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE classes ADD COLUMN exam_format TEXT"))
                    
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.info("Migration: Added exam_format column to classes table")
                    
    except Exception as e:
        # Log error but don't fail startup - migrations are best-effort
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Migration failed: {e}", exc_info=True)


def drop_db() -> None:
    """
    Drop all database tables.
    Use with caution - only for development/testing.
    """
    Base.metadata.drop_all(bind=engine)


# Export _db_path for logging/debugging (read-only access)
__all__ = ["get_db", "init_db", "drop_db", "Base", "SessionLocal", "engine", "_db_path"]
