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


def test_change_password_rate_limit(client_with_rate_limit):
    """Change-password endpoint should return 429 after exceeding 3 requests/minute."""
    from app.rate_limit import limiter
    limiter.reset()
    client = client_with_rate_limit

    # Register and login
    client.post(
        "/auth/register",
        json={"username": "ratelimitpw", "password": "SecurePass123!"},
    )
    resp = client.post(
        "/auth/login",
        json={"username": "ratelimitpw", "password": "SecurePass123!"},
    )
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Send 3 change-password attempts (limit is 3/minute)
    # These will fail with 401 (wrong current password) but still count against rate limit
    for i in range(3):
        client.post(
            "/auth/change-password",
            json={"current_password": "WrongPass123!", "new_password": f"NewSecure{i}23!"},
            headers=headers,
        )

    # 4th request should be rate limited
    resp = client.post(
        "/auth/change-password",
        json={"current_password": "WrongPass123!", "new_password": "NewSecure999!"},
        headers=headers,
    )
    assert resp.status_code == 429


def test_task_create_rate_limit(client_with_rate_limit):
    """Task create endpoint should return 429 after exceeding 10 requests/minute."""
    from app.rate_limit import limiter
    limiter.reset()
    client = client_with_rate_limit

    # Register and login
    client.post(
        "/auth/register",
        json={"username": "taskrateuser", "password": "SecurePass123!"},
    )
    resp = client.post(
        "/auth/login",
        json={"username": "taskrateuser", "password": "SecurePass123!"},
    )
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Send 10 task creation requests (limit is 10/minute)
    for i in range(10):
        client.post(
            "/tasks/",
            json={"title": f"Rate limit task {i}"},
            headers=headers,
        )

    # 11th request should be rate limited
    resp = client.post(
        "/tasks/",
        json={"title": "One too many"},
        headers=headers,
    )
    assert resp.status_code == 429


def test_task_list_rate_limit(client_with_rate_limit):
    """Task list endpoint should return 429 after exceeding 30 requests/minute."""
    from app.rate_limit import limiter
    limiter.reset()
    client = client_with_rate_limit

    # Register and login
    client.post(
        "/auth/register",
        json={"username": "listrateuser", "password": "SecurePass123!"},
    )
    resp = client.post(
        "/auth/login",
        json={"username": "listrateuser", "password": "SecurePass123!"},
    )
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Send 30 list requests (limit is 30/minute)
    for i in range(30):
        client.get("/tasks/", headers=headers)

    # 31st request should be rate limited
    resp = client.get("/tasks/", headers=headers)
    assert resp.status_code == 429


def test_task_get_rate_limit(client_with_rate_limit):
    """Task get endpoint should return 429 after exceeding 30 requests/minute."""
    from app.rate_limit import limiter
    limiter.reset()
    client = client_with_rate_limit

    # Register and login
    client.post(
        "/auth/register",
        json={"username": "getrateuser", "password": "SecurePass123!"},
    )
    resp = client.post(
        "/auth/login",
        json={"username": "getrateuser", "password": "SecurePass123!"},
    )
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create a task to fetch
    resp = client.post(
        "/tasks/",
        json={"title": "Rate limit get task"},
        headers=headers,
    )
    task_id = resp.json()["id"]

    # Send 30 get requests (limit is 30/minute)
    for i in range(30):
        client.get(f"/tasks/{task_id}", headers=headers)

    # 31st request should be rate limited
    resp = client.get(f"/tasks/{task_id}", headers=headers)
    assert resp.status_code == 429


def test_task_update_rate_limit(client_with_rate_limit):
    """Task update endpoint should return 429 after exceeding 20 requests/minute."""
    from app.rate_limit import limiter
    limiter.reset()
    client = client_with_rate_limit

    # Register and login
    client.post(
        "/auth/register",
        json={"username": "updaterateuser", "password": "SecurePass123!"},
    )
    resp = client.post(
        "/auth/login",
        json={"username": "updaterateuser", "password": "SecurePass123!"},
    )
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create a task to update
    resp = client.post(
        "/tasks/",
        json={"title": "Rate limit update task"},
        headers=headers,
    )
    task_id = resp.json()["id"]

    # Send 20 update requests (limit is 20/minute)
    for i in range(20):
        client.patch(
            f"/tasks/{task_id}",
            json={"title": f"Updated title {i}"},
            headers=headers,
        )

    # 21st request should be rate limited
    resp = client.patch(
        f"/tasks/{task_id}",
        json={"title": "One too many updates"},
        headers=headers,
    )
    assert resp.status_code == 429


def test_task_delete_rate_limit(client_with_rate_limit):
    """Task delete endpoint should return 429 after exceeding 10 requests/minute."""
    from app.rate_limit import limiter
    limiter.reset()
    client = client_with_rate_limit

    # Register and login
    client.post(
        "/auth/register",
        json={"username": "deleterateuser", "password": "SecurePass123!"},
    )
    resp = client.post(
        "/auth/login",
        json={"username": "deleterateuser", "password": "SecurePass123!"},
    )
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create one task
    resp = client.post(
        "/tasks/",
        json={"title": "Delete rate task"},
        headers=headers,
    )
    task_id = resp.json()["id"]

    # Send 10 delete requests to the same path (first deletes, rest get 404,
    # but all count against the rate limit since the limiter fires before the handler)
    for i in range(10):
        client.delete(f"/tasks/{task_id}", headers=headers)

    # 11th request should be rate limited
    resp = client.delete(f"/tasks/{task_id}", headers=headers)
    assert resp.status_code == 429


def test_rate_limit_returns_retry_after_header(client_with_rate_limit):
    """429 responses should include a Retry-After header."""
    from app.rate_limit import limiter
    limiter.reset()
    client = client_with_rate_limit

    # Register a user
    client.post(
        "/auth/register",
        json={"username": "retryafteruser", "password": "SecurePass123!"},
    )

    # Exceed login rate limit (5/minute)
    for i in range(5):
        client.post(
            "/auth/login",
            json={"username": "retryafteruser", "password": "WrongPass123!"},
        )

    resp = client.post(
        "/auth/login",
        json={"username": "retryafteruser", "password": "WrongPass123!"},
    )
    assert resp.status_code == 429
    assert "Retry-After" in resp.headers
    assert resp.headers["Retry-After"] == "60"
