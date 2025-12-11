"""Unit tests for job service."""

import pytest
from sqlalchemy.orm import Session

from app.db.database import Base, SessionLocal, engine
from app.db.models import ReferenceUploadJob
from app.services.job_service import JobService


@pytest.fixture
def db_session():
    """Create a test database session."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def job_service(db_session: Session):
    """Create a job service instance."""
    return JobService(db_session)


@pytest.fixture
def sample_class(db_session: Session):
    """Create a sample class for testing."""
    from app.db.models import Class

    test_class = Class(id="test_class_1", name="Test Class", description="Test Description")
    db_session.add(test_class)
    db_session.commit()
    return test_class


def test_create_job(job_service: JobService, sample_class):
    """Test creating a job."""
    job = job_service.create_job(
        class_id=sample_class.id, total_files=5, exam_source="Test Exam", exam_type="midterm"
    )

    assert job.id is not None
    assert job.class_id == sample_class.id
    assert job.status == "pending"
    assert job.progress == 0
    assert job.total_files == 5
    assert job.processed_files == 0
    assert job.failed_files == 0
    assert job.exam_source == "Test Exam"
    assert job.exam_type == "midterm"


def test_get_job(job_service: JobService, sample_class):
    """Test getting a job by ID."""
    job = job_service.create_job(class_id=sample_class.id, total_files=3)
    retrieved = job_service.get_job(job.id)

    assert retrieved is not None
    assert retrieved.id == job.id
    assert retrieved.class_id == sample_class.id


def test_get_job_not_found(job_service: JobService):
    """Test getting a non-existent job."""
    retrieved = job_service.get_job("nonexistent_job")
    assert retrieved is None


def test_list_class_jobs(job_service: JobService, sample_class, db_session: Session):
    """Test listing jobs for a class."""
    # Create multiple jobs
    job1 = job_service.create_job(class_id=sample_class.id, total_files=2)
    job2 = job_service.create_job(class_id=sample_class.id, total_files=3)

    jobs = job_service.list_class_jobs(sample_class.id)

    assert len(jobs) == 2
    job_ids = [job.id for job in jobs]
    assert job1.id in job_ids
    assert job2.id in job_ids


def test_list_class_jobs_empty(job_service: JobService, sample_class):
    """Test listing jobs for a class with no jobs."""
    jobs = job_service.list_class_jobs(sample_class.id)
    assert len(jobs) == 0


def test_list_class_jobs_ordered_by_date(job_service: JobService, sample_class, db_session: Session):
    """Test that jobs are ordered by creation date (newest first)."""
    import time

    job1 = job_service.create_job(class_id=sample_class.id, total_files=1)
    time.sleep(0.1)  # Delay to ensure different timestamps
    job2 = job_service.create_job(class_id=sample_class.id, total_files=2)

    jobs = job_service.list_class_jobs(sample_class.id)

    assert len(jobs) == 2
    # Both jobs should be present
    job_ids = [job.id for job in jobs]
    assert job1.id in job_ids
    assert job2.id in job_ids
    # Newest should be first (check timestamps)
    if jobs[0].created_at and jobs[1].created_at:
        assert jobs[0].created_at >= jobs[1].created_at

