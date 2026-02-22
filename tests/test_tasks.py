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
