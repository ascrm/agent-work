def create_task(client, **overrides):
    payload = {"title": "整理季度报告", "goal": "汇总 Q3 数据并生成结论", **overrides}
    return client.post("/api/v1/tasks", json=payload)


def test_create_task(client):
    response = create_task(client)

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "整理季度报告"
    assert body["status"] == "pending"
    assert body["id"]
    assert body["created_at"] == body["updated_at"]


def test_create_task_rejects_empty_title(client):
    response = create_task(client, title="")

    assert response.status_code == 422


def test_get_task(client):
    task_id = create_task(client).json()["id"]

    response = client.get(f"/api/v1/tasks/{task_id}")

    assert response.status_code == 200
    assert response.json()["id"] == task_id


def test_get_missing_task_returns_404(client):
    response = client.get("/api/v1/tasks/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404


def test_list_tasks_returns_newest_first(client):
    first = create_task(client, title="第一个").json()["id"]
    second = create_task(client, title="第二个").json()["id"]

    response = client.get("/api/v1/tasks")

    assert response.status_code == 200
    ids = [task["id"] for task in response.json()]
    assert ids.index(second) < ids.index(first)


def test_update_status_follows_state_machine(client):
    task_id = create_task(client).json()["id"]

    response = client.patch(f"/api/v1/tasks/{task_id}", json={"status": "running"})

    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_illegal_transition_returns_409(client):
    task_id = create_task(client).json()["id"]

    # pending -> done 不在白名单里
    response = client.patch(f"/api/v1/tasks/{task_id}", json={"status": "done"})

    assert response.status_code == 409
    assert "非法状态流转" in response.json()["detail"]


def test_cannot_leave_terminal_state(client):
    task_id = create_task(client).json()["id"]
    client.patch(f"/api/v1/tasks/{task_id}", json={"status": "running"})
    client.patch(f"/api/v1/tasks/{task_id}", json={"status": "done"})

    response = client.patch(f"/api/v1/tasks/{task_id}", json={"status": "running"})

    assert response.status_code == 409


def test_update_missing_task_returns_404(client):
    response = client.patch(
        "/api/v1/tasks/00000000-0000-0000-0000-000000000000",
        json={"title": "x"},
    )

    assert response.status_code == 404
