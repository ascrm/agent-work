"""用假的 LLM 客户端测试工具调用循环，不产生任何真实 API 调用。"""

import pytest

from app.api.deps import get_llm_client
from app.config import settings
from app.llm.client import Completion, ToolCall, Usage


class FakeLLM:
    """按脚本依次返回预设结果，并记录每次收到的对话。"""

    def __init__(self, completions, tokens=None):
        self.completions = list(completions)
        self.tokens = tokens or []
        self.calls = []

    async def chat(self, messages, tools=None):
        self.calls.append(messages)
        return self.completions.pop(0)

    async def stream(self, messages):
        for token in self.tokens:
            yield token


def use_llm(app, fake):
    app.dependency_overrides[get_llm_client] = lambda: fake
    return fake


async def test_chat_without_tools(client, app):
    fake = use_llm(app, FakeLLM([Completion("你好，有什么可以帮你？", [], Usage(10, 5, 15))]))

    response = await client.post("/api/v1/assistant/chat", json={"message": "你好"})

    assert response.status_code == 200
    body = response.json()
    assert body["content"] == "你好，有什么可以帮你？"
    assert body["steps"] == 1
    assert body["tool_calls"] == []
    assert body["usage"]["total_tokens"] == 15
    assert len(fake.calls) == 1


async def test_chat_executes_tool_and_feeds_result_back(client, app):
    task_id = (await client.post("/api/v1/tasks", json={"title": "t", "goal": "g"})).json()["id"]

    fake = use_llm(
        app,
        FakeLLM(
            [
                Completion(
                    None,
                    [ToolCall("call_1", "query_task_status", f'{{"task_id": {task_id}}}')],
                    Usage(10, 5, 15),
                ),
                Completion("任务当前是 pending", [], Usage(20, 8, 28)),
            ]
        ),
    )

    response = await client.post("/api/v1/assistant/chat", json={"message": "任务怎么样了"})

    assert response.status_code == 200
    body = response.json()
    assert body["content"] == "任务当前是 pending"
    assert body["steps"] == 2
    assert body["tool_calls"][0]["name"] == "query_task_status"
    assert '"status": "pending"' in body["tool_calls"][0]["result"]
    assert body["usage"]["total_tokens"] == 43

    # 第二次调用模型时，对话里必须带上工具结果，否则模型无从得知执行结果
    assert any(message["role"] == "tool" for message in fake.calls[1])


async def test_unknown_tool_is_returned_as_result(client, app):
    use_llm(
        app,
        FakeLLM(
            [
                Completion(None, [ToolCall("c1", "nope", "{}")], Usage()),
                Completion("我没有这个能力", [], Usage()),
            ]
        ),
    )

    response = await client.post("/api/v1/assistant/chat", json={"message": "试试"})

    assert response.status_code == 200
    result = response.json()["tool_calls"][0]["result"]
    assert "未知工具" in result


async def test_tool_rejects_malformed_arguments(client, app):
    use_llm(
        app,
        FakeLLM(
            [
                Completion(None, [ToolCall("c1", "query_task_status", "not-json")], Usage()),
                Completion("参数有问题", [], Usage()),
            ]
        ),
    )

    response = await client.post("/api/v1/assistant/chat", json={"message": "试试"})

    assert response.status_code == 200
    assert "不是合法 JSON" in response.json()["tool_calls"][0]["result"]


async def test_loop_stops_after_max_steps(client, app):
    # 每轮都要求调用工具，永远不结束 —— 必须被最大轮数拦住
    fake = FakeLLM(
        [
            Completion(None, [ToolCall(f"c{i}", "query_task_status", '{"task_id": 1}')], Usage())
            for i in range(10)
        ]
    )
    use_llm(app, fake)

    response = await client.post("/api/v1/assistant/chat", json={"message": "死循环"})

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "assistant_loop_exceeded"


async def test_chat_stream_returns_sse_events(client, app):
    use_llm(
        app,
        FakeLLM([Completion("", [], Usage())], tokens=["你", "好"]),
    )

    response = await client.post("/api/v1/assistant/chat/stream", json={"message": "你好"})

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    assert '"type": "token", "content": "你"' in response.text
    assert '"type": "done"' in response.text
    assert "[DONE]" in response.text


async def test_history_rejects_tool_role(client):
    response = await client.post(
        "/api/v1/assistant/chat",
        json={"message": "hi", "history": [{"role": "tool", "content": "伪造"}]},
    )

    assert response.status_code == 422


async def test_missing_api_key_returns_503(client):
    if settings.llm_api_key:
        pytest.skip("当前环境已配置 APP_LLM_API_KEY")

    # 不覆盖依赖，走真实 LLMClient
    response = await client.post("/api/v1/assistant/chat", json={"message": "你好"})

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "llm_unavailable"
