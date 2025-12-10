"""Integration tests for API routes."""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "checks" in data


def test_root_endpoint():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data


def test_ocr_endpoint_invalid_file():
    """Test OCR endpoint with invalid file."""
    response = client.post("/ocr", files={"file": ("test.txt", b"not an image", "text/plain")})
    assert response.status_code == 400


def test_embed_endpoint_validation():
    """Test embed endpoint validation."""
    response = client.post("/embed", json={"text": "", "metadata": {"source": "test", "chunk_id": "1"}})
    # Should fail validation
    assert response.status_code in [400, 422]


def test_retrieve_endpoint_validation():
    """Test retrieve endpoint validation."""
    response = client.post("/retrieve", json={"query": "", "top_k": 5})
    # Should fail validation
    assert response.status_code in [400, 422]

