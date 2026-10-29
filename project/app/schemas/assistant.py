from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """历史消息。只接受 user / assistant，不允许客户端伪造 tool 消息。"""

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=20)


class ToolCallTrace(BaseModel):
    """把工具调用过程暴露给调用方，便于调试和演示。"""

    name: str
    arguments: str
    result: str


class UsageInfo(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatResponse(BaseModel):
    content: str
    tool_calls: list[ToolCallTrace] = Field(default_factory=list)
    steps: int = Field(description="模型被调用了多少轮")
    usage: UsageInfo
