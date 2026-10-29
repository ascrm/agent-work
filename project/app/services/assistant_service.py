"""工具调用循环。

整个 W2 的核心就是这一个循环：

    用户消息 + 工具列表 → 模型
         ↑                  ↓
         └── 工具结果 ←── tool_calls

模型不会执行任何东西，它只说"我要调用 query_task_status，参数是 {task_id: 1}"。
"""

import logging
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import AssistantLoopError
from app.llm.client import Completion, LLMClient, Usage
from app.schemas.assistant import ChatMessage, ChatResponse, ToolCallTrace, UsageInfo
from app.tools.task_tools import TOOL_SCHEMAS, execute_tool

logger = logging.getLogger("app.assistant")

SYSTEM_PROMPT = """你是一个企业任务助手。
你可以调用工具查询任务信息。

规则：
1. 用户询问任务状态时，必须调用 query_task_status 工具，不要编造。
2. 工具返回错误时，如实告诉用户，不要猜测。
3. 回答简洁，使用中文。"""


def _assistant_tool_message(completion: Completion) -> dict[str, Any]:
    """把模型的 tool_calls 原样放回对话历史，模型下一轮才能对应上结果。"""
    return {
        "role": "assistant",
        "content": completion.content,
        "tool_calls": [
            {
                "id": call.id,
                "type": "function",
                "function": {"name": call.name, "arguments": call.arguments},
            }
            for call in completion.tool_calls
        ],
    }


class AssistantService:
    def __init__(
        self,
        llm: LLMClient,
        session: AsyncSession,
        max_steps: int | None = None,
    ) -> None:
        self.llm = llm
        self.session = session
        self.max_steps = max_steps or settings.assistant_max_steps

    def _build_messages(self, message: str, history: list[ChatMessage]) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend({"role": item.role, "content": item.content} for item in history)
        messages.append({"role": "user", "content": message})
        return messages

    async def _run_tool_calls(
        self, completion: Completion, messages: list[dict[str, Any]]
    ) -> list[ToolCallTrace]:
        """执行本轮所有工具，并把结果追加进对话。"""
        messages.append(_assistant_tool_message(completion))

        traces: list[ToolCallTrace] = []
        for call in completion.tool_calls:
            output = await execute_tool(call.name, call.arguments, self.session)
            traces.append(ToolCallTrace(name=call.name, arguments=call.arguments, result=output))
            messages.append({"role": "tool", "tool_call_id": call.id, "content": output})
        return traces

    async def chat(self, message: str, history: list[ChatMessage]) -> ChatResponse:
        messages = self._build_messages(message, history)
        traces: list[ToolCallTrace] = []
        total_usage = Usage()

        for step in range(1, self.max_steps + 1):
            completion = await self.llm.chat(messages, tools=TOOL_SCHEMAS)
            total_usage = total_usage + completion.usage

            if not completion.tool_calls:
                return ChatResponse(
                    content=completion.content or "",
                    tool_calls=traces,
                    steps=step,
                    usage=UsageInfo(
                        prompt_tokens=total_usage.prompt_tokens,
                        completion_tokens=total_usage.completion_tokens,
                        total_tokens=total_usage.total_tokens,
                    ),
                )

            traces.extend(await self._run_tool_calls(completion, messages))

        raise AssistantLoopError(f"超过最大执行轮数 {self.max_steps}")

    async def chat_stream(
        self, message: str, history: list[ChatMessage]
    ) -> AsyncIterator[dict[str, Any]]:
        """SSE 版本。

        为了代码简单，这里先用非流式调用把工具跑完；
        确认不再需要工具后，再用流式调用生成最终回答。
        代价是多一次模型调用 —— 生产实现应该在流里边解析 tool_calls 边判断。
        """
        messages = self._build_messages(message, history)

        for step in range(1, self.max_steps + 1):
            completion = await self.llm.chat(messages, tools=TOOL_SCHEMAS)

            if not completion.tool_calls:
                async for token in self.llm.stream(messages):
                    yield {"type": "token", "content": token}
                yield {"type": "done", "steps": step}
                return

            for trace in await self._run_tool_calls(completion, messages):
                yield {
                    "type": "tool",
                    "name": trace.name,
                    "arguments": trace.arguments,
                    "result": trace.result,
                }

        raise AssistantLoopError(f"超过最大执行轮数 {self.max_steps}")
