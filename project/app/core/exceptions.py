class AppError(Exception):
    """所有业务异常的基类。业务代码只管抛，转成 HTTP 由 handler 统一负责。"""

    status_code = 500
    code = "internal_error"

    def __init__(self, message: str = "服务器内部错误") -> None:
        super().__init__(message)


class BadRequestError(AppError):
    status_code = 400
    code = "bad_request"


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class LLMUnavailableError(AppError):
    status_code = 503
    code = "llm_unavailable"


class AssistantLoopError(AppError):
    status_code = 502
    code = "assistant_loop_exceeded"
