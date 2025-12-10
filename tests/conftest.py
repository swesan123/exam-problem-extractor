"""Pytest configuration and shared fixtures."""
import pytest
import os
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def test_settings(monkeypatch):
    """Override settings for testing."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-12345")
    monkeypatch.setenv("VECTOR_DB_PATH", "./tests/test_vector_store")
    monkeypatch.setenv("VECTOR_DB_TYPE", "chroma")
    return None


@pytest.fixture
def sample_image_bytes():
    """Create sample image bytes for testing."""
    # Minimal valid PNG header
    return b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"


@pytest.fixture
def sample_text():
    """Sample text for testing."""
    return "This is a sample exam question about quadratic equations."


@pytest.fixture
def sample_metadata():
    """Sample metadata for testing."""
    return {
        "source": "test_exam_2023",
        "page": 1,
        "chunk_id": "test_chunk_001"
    }


@pytest.fixture(autouse=True)
def cleanup_test_vector_store():
    """Clean up test vector store before and after tests."""
    test_db_path = Path("./tests/test_vector_store")
    if test_db_path.exists():
        import shutil
        shutil.rmtree(test_db_path, ignore_errors=True)
    yield
    # Cleanup after test
    if test_db_path.exists():
        import shutil
        shutil.rmtree(test_db_path, ignore_errors=True)
