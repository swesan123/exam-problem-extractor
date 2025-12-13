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
        
        # Check if classes table exists
        if "classes" in inspector.get_table_names():
            # Get existing columns
            existing_columns = [col["name"] for col in inspector.get_columns("classes")]
            
            # Migration: Add exam_format column if it doesn't exist
            if "exam_format" not in existing_columns:
                with engine.begin() as conn:  # Use begin() for automatic transaction management
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
