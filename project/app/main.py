import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import assistant, health, tasks
from app.config import settings
from app.core.handlers import register_exception_handlers
from app.core.logging import setup_logging
from app.core.middleware import request_context_middleware
from app.database import close_db, init_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """应用生命周期：启动时建表、关闭时释放连接池。"""
    setup_logging()
    await init_db()
    logger.info("应用启动 env=%s", settings.env)
    yield
    await close_db()
    logger.info("应用关闭")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Agent Workbench",
        version="0.2.0",
        description="最小但完整的 Web 后端模板",
        lifespan=lifespan,
    )

    app.middleware("http")(request_context_middleware)

    # 最后注册的 middleware 在最外层，所以 CORS 会包裹住其他中间件
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    register_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(tasks.router, prefix="/api/v1")
    app.include_router(assistant.router, prefix="/api/v1")

    return app


app = create_app()
