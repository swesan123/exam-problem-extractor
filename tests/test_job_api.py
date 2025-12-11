"""Integration tests for job API endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.database import Base, SessionLocal, engine
from app.db.models import Class, ReferenceUploadJob
from app.main import app


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
def sample_class(db_session: Session):
    """Create a sample class for testing."""
    test_class = Class(id="test_class_1", name="Test Class", description="Test Description")
    db_session.add(test_class)
    db_session.commit()
    return test_class


@pytest.fixture
def client(db_session):
    """Create a test client with database dependency override."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    from app.db.database import get_db

    app.dependency_overrides[get_db] = override_get_db

    yield TestClient(app)

    app.dependency_overrides.clear()


def test_get_job_status(client: TestClient, sample_class, db_session: Session):
    """Test getting job status."""
    from app.services.job_service import JobService

    job_service = JobService(db_session)
    job = job_service.create_job(class_id=sample_class.id, total_files=3)

    response = client.get(f"/api/reference-content/jobs/{job.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job.id
    assert data["status"] == "pending"
    assert data["total_files"] == 3
    assert data["processed_files"] == 0
    assert data["failed_files"] == 0


def test_get_job_status_not_found(client: TestClient):
    """Test getting status for non-existent job."""
    response = client.get("/api/reference-content/jobs/nonexistent_job")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_list_class_jobs(client: TestClient, sample_class, db_session: Session):
    """Test listing jobs for a class."""
    from app.services.job_service import JobService

    job_service = JobService(db_session)
    job1 = job_service.create_job(class_id=sample_class.id, total_files=2)
    job2 = job_service.create_job(class_id=sample_class.id, total_files=3)

    response = client.get(f"/api/reference-content/jobs/class/{sample_class.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["class_id"] == sample_class.id
    assert len(data["jobs"]) == 2
    job_ids = [job["job_id"] for job in data["jobs"]]
    assert job1.id in job_ids
    assert job2.id in job_ids


def test_list_class_jobs_empty(client: TestClient, sample_class):
    """Test listing jobs for a class with no jobs."""
    response = client.get(f"/api/reference-content/jobs/class/{sample_class.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["class_id"] == sample_class.id
    assert len(data["jobs"]) == 0

