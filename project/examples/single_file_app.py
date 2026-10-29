"""单文件版：和分层项目功能完全相同，但全部写在一个文件里。

运行：cd project && python -m uv run python examples/single_file_app.py
然后打开 http://127.0.0.1:8001/docs

阅读顺序就是下面的 1 → 5 五段。
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import DateTime, String, Text, func, select
from sqlalchemy import Enum as SAEnum
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

logging.basicConfig(level=logging.INFO)


# ---------- 1. 数据库表结构（对应分层版的 app/models/task.py）----------
class Base(DeclarativeBase):
    pass


class TaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


def now() -> datetime:
    return datetime.now(UTC)


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    goal: Mapped[str] = mapped_column(Text)
    status: Mapped[TaskStatus] = mapped_column(
        SAEnum(
            TaskStatus, native_enum=False, values_callable=lambda e: [m.value for m in e], length=32
        ),
        default=TaskStatus.PENDING,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


# ---------- 2. 请求 / 响应模型（对应 app/schemas/）----------
class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    goal: str = Field(min_length=1, max_length=5000)


class TaskUpdate(BaseModel):
    title: str | None = None
    status: TaskStatus | None = None


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    goal: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime


class Page(BaseModel):
    items: list[TaskRead]
    total: int
    limit: int
    offset: int


# ---------- 3. 业务规则（对应 app/services/task_service.py）----------
ALLOWED_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.PENDING: {TaskStatus.RUNNING, TaskStatus.CANCELLED},
    TaskStatus.RUNNING: {
        TaskStatus.WAITING_APPROVAL,
        TaskStatus.DONE,
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
    },
    TaskStatus.WAITING_APPROVAL: {TaskStatus.RUNNING, TaskStatus.FAILED, TaskStatus.CANCELLED},
    TaskStatus.DONE: set(),
    TaskStatus.FAILED: set(),
    TaskStatus.CANCELLED: set(),
}


# ---------- 4. 数据库连接（对应 app/database.py + app/config.py）----------
engine = create_async_engine("sqlite+aiosqlite:///./single_file.db")
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


# ---------- 5. 接口（对应 app/api/v1/tasks.py）----------
app = FastAPI(title="单文件版", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/tasks", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
async def create_task(payload: TaskCreate, session: SessionDep) -> Task:
    task = Task(title=payload.title, goal=payload.goal)
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


@app.get("/api/v1/tasks", response_model=Page)
async def list_tasks(
    session: SessionDep,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> Page:
    total = await session.scalar(select(func.count()).select_from(Task))
    result = await session.scalars(
        select(Task).order_by(Task.id.desc()).limit(limit).offset(offset)
    )
    return Page(items=list(result), total=total or 0, limit=limit, offset=offset)


@app.get("/api/v1/tasks/{task_id}", response_model=TaskRead)
async def get_task(task_id: int, session: SessionDep) -> Task:
    task = await session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@app.patch("/api/v1/tasks/{task_id}", response_model=TaskRead)
async def update_task(task_id: int, payload: TaskUpdate, session: SessionDep) -> Task:
    task = await session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")

    if payload.status is not None and payload.status != task.status:
        if payload.status not in ALLOWED_TRANSITIONS[task.status]:
            raise HTTPException(
                status_code=409, detail=f"非法状态流转：{task.status} -> {payload.status}"
            )
        task.status = payload.status

    if payload.title is not None:
        task.title = payload.title

    await session.commit()
    await session.refresh(task)
    return task


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)
