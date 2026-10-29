"""模型适配层。

这一层是唯一知道"用的是哪家模型"的地方。业务代码只认识
Completion / ToolCall / Usage 三个类型，换厂商时只改这个文件。
"""

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from typing import Any, TypeVar

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    RateLimitError,
)

from app.config import settings
from app.core.exceptions import LLMUnavailableError

logger = logging.getLogger("app.llm")

# 这些异常重试有意义；400/401/403 这类重试也不会好
RETRYABLE = (APITimeoutError, APIConnectionError, RateLimitError)

T = TypeVar("T")


@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def __add__(self, other: "Usage") -> "Usage":
        return Usage(
            self.prompt_tokens + other.prompt_tokens,
            self.completion_tokens + other.completion_tokens,
            self.total_tokens + other.total_tokens,
        )


@dataclass
class ToolCall:
    """模型要求调用某个工具。注意：模型只给出名字和参数，执行永远是你的代码。"""

    id: str
    name: str
    arguments: str  # JSON 字符串，需要自己 json.loads


@dataclass
class Completion:
    content: str | None
    tool_calls: list[ToolCall]
    usage: Usage


def _to_usage(usage: Any) -> Usage:
    if usage is None:
        return Usage()
    return Usage(usage.prompt_tokens, usage.completion_tokens, usage.total_tokens)


class LLMClient:
    def __init__(self) -> None:
        self._client: AsyncOpenAI | None = None

    def _get_client(self) -> AsyncOpenAI | None:
        # 延迟创建：没配 key 时应用依然能启动，只有真正调用模型才报错
        if self._client is None:
            if not settings.llm_api_key:
                raise LLMUnavailableError("未配置 APP_LLM_API_KEY，无法调用模型")
            self._client = AsyncOpenAI(
                api_key=settings.llm_api_key,
                base_url=settings.llm_base_url,
                timeout=settings.llm_timeout,
                max_retries=0,  # 重试统一放在 _call 里，便于记录日志
            )
        return self._client

    async def _call(self, factory: Callable[[], Awaitable[T]]) -> T:
        """带指数退避的调用。只重试超时、连接失败、限流。"""
        last_error: Exception | None = None
        for attempt in range(settings.llm_max_retries + 1):
            try:
                return await factory()
            except RETRYABLE as exc:
                last_error = exc
                if attempt >= settings.llm_max_retries:
                    break
                delay = 2**attempt
                logger.warning("模型调用失败（%s），%ss 后重试", exc, delay)
                await asyncio.sleep(delay)
            except APIStatusError as exc:
                logger.error("模型返回错误状态 %s：%s", exc.status_code, exc.message)
                raise LLMUnavailableError(f"模型调用失败（HTTP {exc.status_code}）") from exc

        raise LLMUnavailableError("模型服务暂时不可用，请稍后重试") from last_error

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> Completion:
        params: dict[str, Any] = {
            "model": settings.llm_model,
            "messages": messages,
            "temperature": 0,
        }
        if settings.llm_disable_thinking:
            # OpenAI SDK 会拒绝未知参数，厂商私有参数必须走 extra_body
            params["extra_body"] = {"thinking": {"type": "disabled"}}
        if tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"

        response = await self._call(lambda: self._get_client().chat.completions.create(**params))
        message = response.choices[0].message

        return Completion(
            content=message.content,
            tool_calls=[
                ToolCall(id=call.id, name=call.function.name, arguments=call.function.arguments)
                for call in (message.tool_calls or [])
            ],
            usage=_to_usage(response.usage),
        )

    async def stream(self, messages: list[dict[str, Any]]) -> AsyncIterator[str]:
        """流式返回文本增量。注意：流式接口不统计 token 用量。"""
        params: dict[str, Any] = {
            "model": settings.llm_model,
            "messages": messages,
            "temperature": 0,
            "stream": True,
        }
        if settings.llm_disable_thinking:
            params["extra_body"] = {"thinking": {"type": "disabled"}}

        response = await self._call(lambda: self._get_client().chat.completions.create(**params))
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
