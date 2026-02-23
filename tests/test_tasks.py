def test_create_task(client, auth_header):
    resp = client.post(
        "/tasks/",
        json={"title": "My Task", "description": "Do something"},
        headers=auth_header,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "My Task"
    assert data["completed"] is False


def test_list_tasks(client, auth_header):
    client.post("/tasks/", json={"title": "Task 1"}, headers=auth_header)
    client.post("/tasks/", json={"title": "Task 2"}, headers=auth_header)
    resp = client.get("/tasks/", headers=auth_header)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_get_task(client, auth_header):
    create_resp = client.post(
        "/tasks/", json={"title": "Specific Task"}, headers=auth_header
    )
    task_id = create_resp.json()["id"]
    resp = client.get(f"/tasks/{task_id}", headers=auth_header)
    assert resp.status_code == 200
    assert resp.json()["title"] == "Specific Task"


def test_update_task(client, auth_header):
    create_resp = client.post(
        "/tasks/", json={"title": "Old Title"}, headers=auth_header
    )
    task_id = create_resp.json()["id"]
    resp = client.patch(
        f"/tasks/{task_id}",
        json={"title": "New Title", "completed": True},
        headers=auth_header,
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "New Title"
    assert resp.json()["completed"] is True


def test_delete_task(client, auth_header):
    create_resp = client.post(
        "/tasks/", json={"title": "To Delete"}, headers=auth_header
    )
    task_id = create_resp.json()["id"]
    resp = client.delete(f"/tasks/{task_id}", headers=auth_header)
    assert resp.status_code == 204
    resp = client.get(f"/tasks/{task_id}", headers=auth_header)
    assert resp.status_code == 404


def test_unauthorized_access(client):
    resp = client.get("/tasks/")
    assert resp.status_code == 401


def test_task_not_found(client, auth_header):
    resp = client.get("/tasks/9999", headers=auth_header)
    assert resp.status_code == 404


# --- IDOR Tests (Cross-User Isolation) ---

def _create_user_and_get_header(client, username, password="SecurePass123!"):
    """Helper to register, login, and return auth header for a user."""
    client.post("/auth/register", json={"username": username, "password": password})
    resp = client.post("/auth/login", json={"username": username, "password": password})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_idor_get_other_users_task(client):
    header_a = _create_user_and_get_header(client, "user_a")
    header_b = _create_user_and_get_header(client, "user_b")

    # User A creates a task
    resp = client.post("/tasks/", json={"title": "A's task"}, headers=header_a)
    task_id = resp.json()["id"]

    # User B tries to get User A's task
    resp = client.get(f"/tasks/{task_id}", headers=header_b)
    assert resp.status_code == 404


def test_idor_update_other_users_task(client):
    header_a = _create_user_and_get_header(client, "user_a2")
    header_b = _create_user_and_get_header(client, "user_b2")

    resp = client.post("/tasks/", json={"title": "A's task"}, headers=header_a)
    task_id = resp.json()["id"]

    resp = client.patch(
        f"/tasks/{task_id}",
        json={"title": "Hacked!"},
        headers=header_b,
    )
    assert resp.status_code == 404


def test_idor_delete_other_users_task(client):
    header_a = _create_user_and_get_header(client, "user_a3")
    header_b = _create_user_and_get_header(client, "user_b3")

    resp = client.post("/tasks/", json={"title": "A's task"}, headers=header_a)
    task_id = resp.json()["id"]

    resp = client.delete(f"/tasks/{task_id}", headers=header_b)
    assert resp.status_code == 404

    # Verify task still exists for User A
    resp = client.get(f"/tasks/{task_id}", headers=header_a)
    assert resp.status_code == 200


def test_idor_list_only_own_tasks(client):
    header_a = _create_user_and_get_header(client, "user_a4")
    header_b = _create_user_and_get_header(client, "user_b4")

    client.post("/tasks/", json={"title": "A's task 1"}, headers=header_a)
    client.post("/tasks/", json={"title": "A's task 2"}, headers=header_a)
    client.post("/tasks/", json={"title": "B's task 1"}, headers=header_b)

    resp = client.get("/tasks/", headers=header_a)
    assert len(resp.json()) == 2
    for task in resp.json():
        assert "A's task" in task["title"]

    resp = client.get("/tasks/", headers=header_b)
    assert len(resp.json()) == 1
    assert resp.json()[0]["title"] == "B's task 1"


# --- Pagination Tests ---

def test_pagination_default(client, auth_header):
    for i in range(5):
        client.post("/tasks/", json={"title": f"Task {i}"}, headers=auth_header)
    resp = client.get("/tasks/", headers=auth_header)
    assert resp.status_code == 200
    assert len(resp.json()) == 5


def test_pagination_limit(client, auth_header):
    for i in range(10):
        client.post("/tasks/", json={"title": f"Task {i}"}, headers=auth_header)
    resp = client.get("/tasks/?limit=3", headers=auth_header)
    assert resp.status_code == 200
    assert len(resp.json()) == 3


def test_pagination_skip(client, auth_header):
    for i in range(5):
        client.post("/tasks/", json={"title": f"Task {i}"}, headers=auth_header)
    resp = client.get("/tasks/?skip=3", headers=auth_header)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_pagination_limit_exceeds_max(client, auth_header):
    resp = client.get("/tasks/?limit=200", headers=auth_header)
    assert resp.status_code == 422  # limit max is 100


# --- Mass Assignment & SQL Injection Security Tests ---

def test_mass_assignment_owner_id_ignored(client):
    """PATCH with owner_id should be ignored (mass assignment protection)."""
    header_a = _create_user_and_get_header(client, "mass_a")
    header_b = _create_user_and_get_header(client, "mass_b")

    # Create a task as user A
    resp = client.post("/tasks/", json={"title": "My Task"}, headers=header_a)
    task_id = resp.json()["id"]
    original_owner = resp.json()["owner_id"]

    # Try to PATCH with owner_id (should be ignored by mass assignment protection)
    resp = client.patch(
        f"/tasks/{task_id}",
        json={"title": "Updated", "owner_id": original_owner + 999},
        headers=header_a,
    )
    assert resp.status_code == 200
    assert resp.json()["owner_id"] == original_owner
    assert resp.json()["title"] == "Updated"


def test_sql_injection_in_task_title(client, auth_header):
    """SQL injection attempt in task title should be stored as plain text, not executed."""
    payload = "'; DROP TABLE tasks; --"
    resp = client.post(
        "/tasks/",
        json={"title": payload, "description": "test"},
        headers=auth_header,
    )
    assert resp.status_code == 201
    task_id = resp.json()["id"]

    # Verify the task was stored safely
    resp = client.get(f"/tasks/{task_id}", headers=auth_header)
    assert resp.status_code == 200
    assert resp.json()["title"] == payload

    # Verify tasks table still works
    resp = client.get("/tasks/", headers=auth_header)
    assert resp.status_code == 200


# --- Malformed Input Tests ---

def test_create_task_empty_title(client, auth_header):
    """Empty task title should be rejected."""
    resp = client.post(
        "/tasks/",
        json={"title": "", "description": "test"},
        headers=auth_header,
    )
    assert resp.status_code == 422


def test_create_task_oversized_title(client, auth_header):
    """Task title exceeding max length should be rejected."""
    resp = client.post(
        "/tasks/",
        json={"title": "x" * 300, "description": "test"},
        headers=auth_header,
    )
    assert resp.status_code == 422
