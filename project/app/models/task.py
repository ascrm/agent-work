from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import DateTime, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Task(Base):
    """任务表。这是数据库结构，不是接口结构（接口结构在 schemas/task.py）。"""

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200))
    goal: Mapped[str] = mapped_column(Text)
    status: Mapped[TaskStatus] = mapped_column(
        # native_enum=False：用 VARCHAR 存字符串，SQLite 和 PostgreSQL 都能跑
        SAEnum(
            TaskStatus,
            native_enum=False,
            values_callable=lambda enum: [member.value for member in enum],
            length=32,
        ),
        default=TaskStatus.PENDING,
        index=True,
    )
    result: Mapped[str | None] = mapped_column(Text, default=None)
    error: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )
