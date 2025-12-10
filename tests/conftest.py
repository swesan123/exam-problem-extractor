"""Pytest configuration and shared fixtures."""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def test_settings(monkeypatch):
    """Override settings for testing."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("VECTOR_DB_PATH", "./tests/test_vector_store")
    return None

