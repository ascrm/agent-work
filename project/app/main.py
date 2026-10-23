from fastapi import FastAPI

from app.api.tasks import router as tasks_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Agent Workbench",
        version="0.1.0",
        description="企业智能任务执行 Agent —— 从任务 API 逐步演进",
    )
    app.include_router(tasks_router, prefix="/api/v1")

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
