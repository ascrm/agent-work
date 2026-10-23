async def test_liveness(client):
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_readiness(client):
    response = await client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


async def test_response_has_request_id(client):
    response = await client.get("/health")

    assert response.headers["X-Request-ID"]
