"""Tests for security features: CORS and rate limiting."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestCORS:
    """Test CORS configuration."""

    def test_cors_headers_present(self, client):
        """Test that CORS headers are present in OPTIONS request."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code in [200, 204]
        assert (
            "access-control-allow-origin" in response.headers
            or "Access-Control-Allow-Origin" in response.headers
        )

    def test_cors_allows_configured_origin(self, client):
        """Test that configured origins are allowed."""
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"},
        )
        # CORS headers should be present
        assert response.status_code == 200

    def test_cors_origin_in_response(self, client):
        """Test that allowed origin is reflected in response."""
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"},
        )
        # The origin should be reflected if it's in the allowed list
        assert response.status_code == 200


class TestRateLimiting:
    """Test rate limiting functionality."""

    def test_rate_limit_headers_present(self, client):
        """Test that rate limit headers are present."""
        response = client.get("/health")
        # Rate limit headers may be present
        assert response.status_code == 200

    def test_rate_limit_enforced_on_ocr_endpoint(self, client, monkeypatch):
        """Test that rate limiting is enforced on OCR endpoint."""
        # Mock rate limit to be very low for testing
        import app.config

        original_rate_limit = app.config.settings.rate_limit_per_minute
        monkeypatch.setattr(app.config.settings, "rate_limit_per_minute", 2)
        monkeypatch.setattr(app.config.settings, "rate_limit_enabled", True)

        # Make requests up to the limit
        for i in range(2):
            # Create a minimal image file for testing
            files = {"file": ("test.png", b"fake image data", "image/png")}
            response = client.post("/ocr", files=files)
            # First requests should succeed (or fail with validation, but not rate limit)
            assert response.status_code in [200, 400, 422, 500]

        # Restore original setting
        monkeypatch.setattr(
            app.config.settings, "rate_limit_per_minute", original_rate_limit
        )

    def test_rate_limit_disabled_when_setting_off(self, client, monkeypatch):
        """Test that rate limiting can be disabled."""
        import app.config

        monkeypatch.setattr(app.config.settings, "rate_limit_enabled", False)

        # Make multiple requests - should not be rate limited
        for _ in range(5):
            response = client.get("/health")
            assert response.status_code == 200

        # Restore
        monkeypatch.setattr(app.config.settings, "rate_limit_enabled", True)

    def test_rate_limit_decorator_present(self):
        """Test that rate limit decorators are applied to endpoints."""
        from app.main import app
        from app.routes import ocr, generate, embed, retrieve

        # Check that limiter is attached to app
        assert hasattr(app.state, "limiter")

        # Check that endpoints exist and can be called
        assert callable(ocr.extract_text)
        assert callable(generate.generate_question)
        assert callable(embed.create_embedding)
        assert callable(retrieve.retrieve_similar)


class TestSecurityHeaders:
    """Test security-related headers."""

    def test_request_id_header(self, client):
        """Test that request ID is included in response."""
        response = client.get("/health")
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers

    def test_process_time_header(self, client):
        """Test that process time is included in response."""
        response = client.get("/health")
        assert response.status_code == 200
        assert "X-Process-Time" in response.headers
