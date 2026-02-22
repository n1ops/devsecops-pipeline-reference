def test_register_success(client):
    resp = client.post(
        "/auth/register",
        json={"username": "newuser", "password": "securepassword123"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "newuser"
    assert "id" in data


def test_register_duplicate(client):
    client.post(
        "/auth/register",
        json={"username": "dupuser", "password": "securepassword123"},
    )
    resp = client.post(
        "/auth/register",
        json={"username": "dupuser", "password": "securepassword123"},
    )
    assert resp.status_code == 409


def test_login_success(client):
    client.post(
        "/auth/register",
        json={"username": "loginuser", "password": "securepassword123"},
    )
    resp = client.post(
        "/auth/login",
        json={"username": "loginuser", "password": "securepassword123"},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_wrong_password(client):
    client.post(
        "/auth/register",
        json={"username": "wrongpw", "password": "securepassword123"},
    )
    resp = client.post(
        "/auth/login",
        json={"username": "wrongpw", "password": "wrongpassword"},
    )
    assert resp.status_code == 401
