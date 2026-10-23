import logging
import time
from uuid import uuid4

from fastapi import Request

logger = logging.getLogger("app.access")


async def request_context_middleware(request: Request, call_next):
    """给每个请求分配 request_id，并记录耗时。

    request_id 有三处用途：
    1. 写进响应头，前端报错时可以带着它来查日志
    2. 写进错误响应体
    3. 写进访问日志，串起同一次请求的所有日志
    """
    request_id = request.headers.get("X-Request-ID") or uuid4().hex[:12]
    request.state.request_id = request_id

    started = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - started) * 1000

    response.headers["X-Request-ID"] = request_id
    logger.info(
        "%s %s -> %d %.1fms rid=%s",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
        request_id,
    )
    return response
