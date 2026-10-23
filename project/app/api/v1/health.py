from fastapi import APIRouter
from sqlalchemy import text

from app.api.deps import SessionDep

router = APIRouter(prefix="/health", tags=["system"])


@router.get("")
async def liveness() -> dict[str, str]:
    """存活探针：进程还在就算健康。"""
    return {"status": "ok"}


@router.get("/ready")
async def readiness(session: SessionDep) -> dict[str, str]:
    """就绪探针：数据库连得上才算就绪。"""
    await session.execute(text("SELECT 1"))
    return {"status": "ready"}
