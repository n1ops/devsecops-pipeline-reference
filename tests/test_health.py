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
