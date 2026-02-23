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
