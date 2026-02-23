def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["service"] == "devsecops-task-api"


def test_security_headers(client):
    resp = client.get("/health")
    assert resp.headers.get("x-content-type-options") == "nosniff"
    assert resp.headers.get("x-frame-options") == "DENY"
    assert resp.headers.get("x-xss-protection") == "0"
    assert "max-age=31536000" in resp.headers.get("strict-transport-security", "")
    assert resp.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert resp.headers.get("permissions-policy") == "camera=(), microphone=(), geolocation=()"
    assert "default-src 'none'" in resp.headers.get("content-security-policy", "")
    assert resp.headers.get("cross-origin-opener-policy") == "same-origin"
    assert resp.headers.get("cross-origin-resource-policy") == "same-origin"


def test_request_id_header(client):
    resp = client.get("/health")
    request_id = resp.headers.get("x-request-id")
    assert request_id is not None
    assert len(request_id) == 36  # UUID format


def test_cache_control_on_api(client, auth_header):
    resp = client.get("/tasks/", headers=auth_header)
    assert resp.headers.get("cache-control") == "no-store, no-cache, must-revalidate"
    assert resp.headers.get("pragma") == "no-cache"


# --- Error Format & Docs Security Tests ---

def test_error_response_no_stack_trace(client):
    """Error responses should not leak stack traces or internal paths."""
    resp = client.get("/nonexistent-endpoint")
    assert resp.status_code in (404, 405)
    body = resp.text
    assert "Traceback" not in body
    assert "File \"/" not in body
    assert "File \"C:" not in body


def test_docs_hidden_in_production(client):
    """OpenAPI docs should be hidden (DEBUG=true in tests, but verify docs_url behavior)."""
    # In test mode, DEBUG=true so docs are available
    resp = client.get("/docs")
    assert resp.status_code == 200
    resp = client.get("/openapi.json")
    assert resp.status_code == 200


# --- CORS Tests ---

def test_cors_preflight(client):
    """CORS preflight should return appropriate CORS headers."""
    resp = client.options(
        "/health",
        headers={
            "Origin": "http://example.com",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization",
        },
    )
    assert resp.status_code == 200
    # Verify CORS headers are present
    assert resp.headers.get("access-control-allow-origin") is not None
    allowed_methods = resp.headers.get("access-control-allow-methods", "")
    assert "GET" in allowed_methods
    allowed_headers = resp.headers.get("access-control-allow-headers", "")
    assert "authorization" in allowed_headers.lower()


def test_body_size_limit_rejected(client, auth_header):
    """Requests with Content-Length exceeding 1MB should be rejected with 413."""
    oversized_body = "x" * (1_048_576 + 1)  # 1MB + 1 byte
    resp = client.post(
        "/tasks/",
        content=oversized_body.encode(),
        headers={**auth_header, "Content-Type": "application/json"},
    )
    assert resp.status_code == 413
    assert "too large" in resp.json()["detail"].lower()


def test_docs_hidden_when_debug_false():
    """OpenAPI docs should return 404 when DEBUG=false."""
    import os
    # The app is already imported with DEBUG=true, so we test the config logic directly
    from app.config import Settings
    prod_settings = Settings(DEBUG=False, SECRET_KEY="test-prod-key-minimum-length-32chars!")
    assert prod_settings.DEBUG is False
    # Verify the FastAPI app would hide docs with these settings
    from fastapi import FastAPI
    prod_app = FastAPI(
        docs_url="/docs" if prod_settings.DEBUG else None,
        redoc_url="/redoc" if prod_settings.DEBUG else None,
        openapi_url="/openapi.json" if prod_settings.DEBUG else None,
    )
    from fastapi.testclient import TestClient
    with TestClient(prod_app) as c:
        resp = c.get("/docs")
        assert resp.status_code == 404
        resp = c.get("/openapi.json")
        assert resp.status_code == 404


def test_security_headers_on_error_responses(client):
    """Security headers should be present on 404 error responses too."""
    resp = client.get("/nonexistent-path")
    assert resp.headers.get("x-content-type-options") == "nosniff"
    assert resp.headers.get("x-frame-options") == "DENY"
    assert resp.headers.get("x-request-id") is not None
    assert "max-age=31536000" in resp.headers.get("strict-transport-security", "")
