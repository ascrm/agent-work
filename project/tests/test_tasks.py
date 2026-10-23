async def create_task(client, **overrides):
    payload = {"title": "整理季度报告", "goal": "汇总 Q3 数据并生成结论", **overrides}
    return await client.post("/api/v1/tasks", json=payload)


async def test_create_task(client):
    response = await create_task(client)

    assert response.status_code == 201
    body = response.json()
    assert body["id"] > 0
    assert body["title"] == "整理季度报告"
    assert body["status"] == "pending"


async def test_create_task_rejects_empty_title(client):
    response = await create_task(client, title="")

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert error["request_id"]


async def test_get_task(client):
    task_id = (await create_task(client)).json()["id"]

    response = await client.get(f"/api/v1/tasks/{task_id}")

    assert response.status_code == 200
    assert response.json()["id"] == task_id


async def test_get_missing_task_returns_404(client):
    response = await client.get("/api/v1/tasks/999")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


async def test_list_tasks_is_paginated(client):
    for index in range(3):
        await create_task(client, title=f"任务 {index}")

    response = await client.get("/api/v1/tasks", params={"limit": 2, "offset": 0})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert body["limit"] == 2
    assert len(body["items"]) == 2


async def test_list_tasks_rejects_invalid_limit(client):
    response = await client.get("/api/v1/tasks", params={"limit": 0})

    assert response.status_code == 422


async def test_update_status_follows_state_machine(client):
    task_id = (await create_task(client)).json()["id"]

    response = await client.patch(f"/api/v1/tasks/{task_id}", json={"status": "running"})

    assert response.status_code == 200
    assert response.json()["status"] == "running"


async def test_illegal_transition_returns_409(client):
    task_id = (await create_task(client)).json()["id"]

    # pending -> done 不在白名单里
    response = await client.patch(f"/api/v1/tasks/{task_id}", json={"status": "done"})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


async def test_cannot_leave_terminal_state(client):
    task_id = (await create_task(client)).json()["id"]
    await client.patch(f"/api/v1/tasks/{task_id}", json={"status": "running"})
    await client.patch(f"/api/v1/tasks/{task_id}", json={"status": "done"})

    response = await client.patch(f"/api/v1/tasks/{task_id}", json={"status": "running"})

    assert response.status_code == 409


async def test_partial_update_keeps_other_fields(client):
    task_id = (await create_task(client)).json()["id"]

    response = await client.patch(f"/api/v1/tasks/{task_id}", json={"title": "新标题"})

    body = response.json()
    assert body["title"] == "新标题"
    assert body["goal"] == "汇总 Q3 数据并生成结论"
