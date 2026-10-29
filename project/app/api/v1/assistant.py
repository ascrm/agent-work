import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.api.deps import AssistantServiceDep
from app.schemas.assistant import ChatRequest, ChatResponse

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, service: AssistantServiceDep) -> ChatResponse:
    """带工具调用的问答。返回最终回答 + 工具调用轨迹 + token 用量。"""
    return await service.chat(payload.message, payload.history)


@router.post("/chat/stream")
async def chat_stream(payload: ChatRequest, service: AssistantServiceDep) -> StreamingResponse:
    """SSE 流式版本。

    每行一个事件：
        data: {"type": "tool",  "name": ..., "arguments": ..., "result": ...}
        data: {"type": "token", "content": "..."}
        data: {"type": "done",  "steps": 2}
        data: [DONE]
    """

    async def event_source():
        async for event in service.chat_stream(payload.message, payload.history):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
