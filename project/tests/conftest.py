import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.repositories.task_repository import get_task_repository


@pytest.fixture
def client() -> TestClient:
    """每个测试都拿到干净的内存仓库，测试之间互不影响。"""
    get_task_repository().clear()
    with TestClient(app) as test_client:
        yield test_client
