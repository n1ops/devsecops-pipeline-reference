def test_register_success(client):
    resp = client.post(
        "/auth/register",
        json={"username": "newuser", "password": "SecurePass123!"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "newuser"
    assert "id" in data


def test_register_duplicate(client):
    client.post(
        "/auth/register",
        json={"username": "dupuser", "password": "SecurePass123!"},
    )
    resp = client.post(
        "/auth/register",
        json={"username": "dupuser", "password": "SecurePass123!"},
    )
    assert resp.status_code == 409


def test_login_success(client):
    client.post(
        "/auth/register",
        json={"username": "loginuser", "password": "SecurePass123!"},
    )
    resp = client.post(
        "/auth/login",
        json={"username": "loginuser", "password": "SecurePass123!"},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_wrong_password(client):
    client.post(
        "/auth/register",
        json={"username": "wrongpw", "password": "SecurePass123!"},
    )
    resp = client.post(
        "/auth/login",
        json={"username": "wrongpw", "password": "WrongPass123!"},
    )
    assert resp.status_code == 401


def test_register_weak_password(client):
    resp = client.post(
        "/auth/register",
        json={"username": "weakpw", "password": "alllowercase"},
    )
    assert resp.status_code == 422


def test_login_nonexistent_user(client):
    resp = client.post(
        "/auth/login",
        json={"username": "noexist", "password": "any"},
    )
    assert resp.status_code == 401


def test_login_weak_password_accepted_at_login(client):
    """Login endpoint uses UserLogin schema -- no password complexity check."""
    client.post(
        "/auth/register",
        json={"username": "loginweak", "password": "SecurePass123!"},
    )
    resp = client.post(
        "/auth/login",
        json={"username": "loginweak", "password": "weak"},
    )
    assert resp.status_code == 401  # Wrong password, but NOT 422


def test_account_lockout(client):
    client.post(
        "/auth/register",
        json={"username": "lockme", "password": "SecurePass123!"},
    )
    # 5 failed attempts
    for _ in range(5):
        client.post(
            "/auth/login",
            json={"username": "lockme", "password": "wrong"},
        )
    # 6th attempt should be locked — returns 401 (not 423) to prevent account enumeration
    resp = client.post(
        "/auth/login",
        json={"username": "lockme", "password": "SecurePass123!"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid username or password"


def test_logout(client, auth_token):
    # Use token - should work
    resp = client.get("/tasks/", headers={"Authorization": f"Bearer {auth_token}"})
    assert resp.status_code == 200

    # Logout
    resp = client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 200

    # Use same token again - should fail
    resp = client.get("/tasks/", headers={"Authorization": f"Bearer {auth_token}"})
    assert resp.status_code == 401


def test_change_password(client, auth_header):
    resp = client.post(
        "/auth/change-password",
        json={"current_password": "SecurePass123!", "new_password": "NewSecure456!"},
        headers=auth_header,
    )
    assert resp.status_code == 200

    # Login with new password
    resp = client.post(
        "/auth/login",
        json={"username": "testuser", "password": "NewSecure456!"},
    )
    assert resp.status_code == 200


def test_change_password_wrong_current(client, auth_header):
    resp = client.post(
        "/auth/change-password",
        json={"current_password": "WrongCurrent1!", "new_password": "NewSecure456!"},
        headers=auth_header,
    )
    assert resp.status_code == 401


def test_register_invalid_username(client):
    resp = client.post(
        "/auth/register",
        json={"username": "bad user!", "password": "SecurePass123!"},
    )
    assert resp.status_code == 422


def test_register_username_with_special_chars(client):
    resp = client.post(
        "/auth/register",
        json={"username": "<script>alert(1)</script>", "password": "SecurePass123!"},
    )
    assert resp.status_code == 422


def test_invalid_token(client):
    resp = client.get("/tasks/", headers={"Authorization": "Bearer invalidtoken123"})
    assert resp.status_code == 401


def test_empty_token(client):
    resp = client.get("/tasks/", headers={"Authorization": "Bearer "})
    assert resp.status_code == 401


def test_double_logout(client, auth_token):
    """Double logout should not cause a 500 error."""
    headers = {"Authorization": f"Bearer {auth_token}"}

    # First logout
    resp = client.post("/auth/logout", headers=headers)
    assert resp.status_code == 200

    # Second logout with same token - should get 401 (token already revoked)
    resp = client.post("/auth/logout", headers=headers)
    assert resp.status_code == 401


def test_change_password_revokes_token(client):
    """After changing password, the old token should be revoked."""
    # Register and login
    client.post(
        "/auth/register",
        json={"username": "pwchange_revoke", "password": "SecurePass123!"},
    )
    resp = client.post(
        "/auth/login",
        json={"username": "pwchange_revoke", "password": "SecurePass123!"},
    )
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Change password
    resp = client.post(
        "/auth/change-password",
        json={"current_password": "SecurePass123!", "new_password": "NewSecure456!"},
        headers=headers,
    )
    assert resp.status_code == 200

    # Try to use old token - should fail
    resp = client.get("/tasks/", headers=headers)
    assert resp.status_code == 401

    # Login with new password should work
    resp = client.post(
        "/auth/login",
        json={"username": "pwchange_revoke", "password": "NewSecure456!"},
    )
    assert resp.status_code == 200


def test_expired_token_rejected(client):
    """Expired JWT should be rejected with 401."""
    import jwt as _jwt
    from datetime import datetime, timedelta, timezone

    payload = {
        "sub": "expireduser",
        "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        "iat": datetime.now(timezone.utc) - timedelta(minutes=31),
        "iss": "DevSecOps Task API",
        "aud": "DevSecOps Task API",
        "jti": "test-expired-jti",
    }
    token = _jwt.encode(payload, "test-secret-key-for-testing-only-not-production", algorithm="HS256")
    resp = client.get("/tasks/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_token_wrong_secret_rejected(client):
    """JWT signed with a different secret should be rejected."""
    import jwt as _jwt
    from datetime import datetime, timedelta, timezone

    payload = {
        "sub": "testuser",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
        "iat": datetime.now(timezone.utc),
        "iss": "DevSecOps Task API",
        "aud": "DevSecOps Task API",
        "jti": "test-wrong-secret-jti",
    }
    token = _jwt.encode(payload, "wrong-secret-key", algorithm="HS256")
    resp = client.get("/tasks/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_token_wrong_audience_rejected(client):
    """JWT with wrong audience claim should be rejected."""
    import jwt as _jwt
    from datetime import datetime, timedelta, timezone

    payload = {
        "sub": "testuser",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
        "iat": datetime.now(timezone.utc),
        "iss": "DevSecOps Task API",
        "aud": "Wrong Audience",
        "jti": "test-wrong-aud-jti",
    }
    token = _jwt.encode(payload, "test-secret-key-for-testing-only-not-production", algorithm="HS256")
    resp = client.get("/tasks/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_token_wrong_issuer_rejected(client):
    """JWT with wrong issuer claim should be rejected."""
    import jwt as _jwt
    from datetime import datetime, timedelta, timezone

    payload = {
        "sub": "testuser",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
        "iat": datetime.now(timezone.utc),
        "iss": "Wrong Issuer",
        "aud": "DevSecOps Task API",
        "jti": "test-wrong-iss-jti",
    }
    token = _jwt.encode(payload, "test-secret-key-for-testing-only-not-production", algorithm="HS256")
    resp = client.get("/tasks/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_token_missing_sub_claim_rejected(client):
    """JWT without 'sub' claim should be rejected."""
    import jwt as _jwt
    from datetime import datetime, timedelta, timezone

    payload = {
        "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
        "iat": datetime.now(timezone.utc),
        "iss": "DevSecOps Task API",
        "aud": "DevSecOps Task API",
        "jti": "test-no-sub-jti",
    }
    token = _jwt.encode(payload, "test-secret-key-for-testing-only-not-production", algorithm="HS256")
    resp = client.get("/tasks/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_token_none_algorithm_rejected(client):
    """JWT with 'none' algorithm should be rejected."""
    import jwt as _jwt
    from datetime import datetime, timedelta, timezone

    payload = {
        "sub": "testuser",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
        "iat": datetime.now(timezone.utc),
        "iss": "DevSecOps Task API",
        "aud": "DevSecOps Task API",
        "jti": "test-none-alg-jti",
    }
    # PyJWT won't encode with algorithm="none" without explicitly allowing it
    # So we manually construct an unsigned token
    import base64
    import json
    header = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).rstrip(b"=").decode()
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload, default=str).encode()).rstrip(b"=").decode()
    token = f"{header}.{payload_b64}."
    resp = client.get("/tasks/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


# --- Response Leakage Security Tests ---

def test_register_response_no_password_leak(client):
    """Registration response should not contain hashed_password."""
    resp = client.post(
        "/auth/register",
        json={"username": "noleak", "password": "SecurePass123!"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "hashed_password" not in data
    assert "password" not in data


# --- Malformed Input Tests ---

def test_malformed_json_body(client):
    """Malformed JSON should return 422, not 500."""
    resp = client.post(
        "/auth/register",
        content=b"not-valid-json{{{",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 422


def test_register_missing_fields(client):
    """Missing required fields should return 422."""
    resp = client.post("/auth/register", json={})
    assert resp.status_code == 422

    resp = client.post("/auth/register", json={"username": "onlyuser"})
    assert resp.status_code == 422

    resp = client.post("/auth/register", json={"password": "SecurePass123!"})
    assert resp.status_code == 422


def test_register_oversized_username(client):
    """Username exceeding max length should return 422."""
    resp = client.post(
        "/auth/register",
        json={"username": "a" * 100, "password": "SecurePass123!"},
    )
    assert resp.status_code == 422


def test_register_oversized_password(client):
    """Password exceeding max length should return 422."""
    resp = client.post(
        "/auth/register",
        json={"username": "bigpw", "password": "A1!" + "a" * 200},
    )
    assert resp.status_code == 422


def test_lockout_expires(client):
    """Account should unlock after the lockout period expires."""
    from datetime import datetime, timedelta, timezone

    client.post(
        "/auth/register",
        json={"username": "lockexpiry", "password": "SecurePass123!"},
    )

    # Trigger lockout with 5 failed attempts
    for _ in range(5):
        client.post(
            "/auth/login",
            json={"username": "lockexpiry", "password": "wrong"},
        )

    # Verify locked
    resp = client.post(
        "/auth/login",
        json={"username": "lockexpiry", "password": "SecurePass123!"},
    )
    assert resp.status_code == 401

    # Directly manipulate locked_until in DB to simulate time passage
    from sqlalchemy.orm import Session
    from app.models import User
    from app.database import get_db

    # Get the db session through the override
    db_gen = client.app.dependency_overrides[get_db]()
    db = next(db_gen)
    try:
        user = db.query(User).filter(User.username == "lockexpiry").first()
        user.locked_until = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=1)
        user.failed_login_attempts = 0
        db.commit()
    finally:
        db.close()

    # Should be able to login now
    resp = client.post(
        "/auth/login",
        json={"username": "lockexpiry", "password": "SecurePass123!"},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_change_password_reuse_rejected(client, auth_header):
    """Changing password to the same password should be rejected."""
    resp = client.post(
        "/auth/change-password",
        json={"current_password": "SecurePass123!", "new_password": "SecurePass123!"},
        headers=auth_header,
    )
    assert resp.status_code == 400
    assert "different" in resp.json()["detail"].lower()


def test_register_duplicate_generic_message(client):
    """Duplicate registration should not leak 'already registered' details."""
    client.post(
        "/auth/register",
        json={"username": "enumtest", "password": "SecurePass123!"},
    )
    resp = client.post(
        "/auth/register",
        json={"username": "enumtest", "password": "SecurePass123!"},
    )
    assert resp.status_code == 409
    assert "already registered" not in resp.json()["detail"].lower()
