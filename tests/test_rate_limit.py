def test_login_rate_limit(client_with_rate_limit):
    """Login endpoint should return 429 after exceeding 5 requests/minute."""
    client = client_with_rate_limit

    # Register a user first
    client.post(
        "/auth/register",
        json={"username": "ratelimituser", "password": "SecurePass123!"},
    )

    # Send 6 login attempts (limit is 5/minute)
    for i in range(5):
        client.post(
            "/auth/login",
            json={"username": "ratelimituser", "password": "WrongPass123!"},
        )

    # 6th request should be rate limited
    resp = client.post(
        "/auth/login",
        json={"username": "ratelimituser", "password": "WrongPass123!"},
    )
    assert resp.status_code == 429


def test_register_rate_limit(client_with_rate_limit):
    """Register endpoint should return 429 after exceeding 5 requests/minute."""
    client = client_with_rate_limit

    for i in range(5):
        client.post(
            "/auth/register",
            json={"username": f"rateuser{i}", "password": "SecurePass123!"},
        )

    # 6th request should be rate limited
    resp = client.post(
        "/auth/register",
        json={"username": "rateuser99", "password": "SecurePass123!"},
    )
    assert resp.status_code == 429
