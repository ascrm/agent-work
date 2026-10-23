import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import AppError

logger = logging.getLogger("app.error")


def _error_body(request: Request, code: str, message: str) -> dict:
    """所有错误响应统一成这个结构，前端只需要写一套解析逻辑。"""
    return {
        "error": {
            "code": code,
            "message": message,
            "request_id": getattr(request.state, "request_id", None),
        }
    }


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(request, exc.code, str(exc)),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        body = _error_body(request, "validation_error", "请求参数校验失败")
        body["error"]["details"] = exc.errors()
        return JSONResponse(status_code=422, content=body)

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        # 未预期的异常：记录完整堆栈，但不把内部细节返回给调用方
        logger.exception("unhandled error rid=%s", getattr(request.state, "request_id", None))
        return JSONResponse(
            status_code=500,
            content=_error_body(request, "internal_error", "服务器内部错误"),
        )
