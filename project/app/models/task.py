from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class TaskStatus(StrEnum):
    """任务状态。Agent 在第 5 周会由程序自动推进这些状态。"""

    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"  # 高风险操作等待人工确认
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


# 状态流转白名单。不在表里的流转一律拒绝，避免程序把任务推进到矛盾状态。
ALLOWED_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.PENDING: {TaskStatus.RUNNING, TaskStatus.CANCELLED},
    TaskStatus.RUNNING: {
        TaskStatus.WAITING_APPROVAL,
        TaskStatus.DONE,
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
    },
    TaskStatus.WAITING_APPROVAL: {
        TaskStatus.RUNNING,
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
    },
    TaskStatus.DONE: set(),
    TaskStatus.FAILED: set(),
    TaskStatus.CANCELLED: set(),
}


def _utcnow() -> datetime:
    return datetime.now(UTC)


class TaskCreate(BaseModel):
    """创建任务的请求体。所有字段必填，长度受限。"""

    title: str = Field(min_length=1, max_length=200, description="任务标题")
    goal: str = Field(min_length=1, max_length=5000, description="用户提交的目标描述")


class TaskUpdate(BaseModel):
    """更新任务的请求体。全部可选 —— 只更新传入的字段。"""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    status: TaskStatus | None = None
    result: str | None = Field(default=None, max_length=20000, description="执行结果")
    error: str | None = Field(default=None, max_length=5000, description="失败原因")


class Task(BaseModel):
    """任务实体。同时也是接口的响应模型。"""

    id: UUID = Field(default_factory=uuid4)
    title: str
    goal: str
    status: TaskStatus = TaskStatus.PENDING
    result: str | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    @classmethod
    def new(cls, *, title: str, goal: str) -> "Task":
        """新任务的创建入口：保证 created_at 与 updated_at 完全一致。"""
        now = _utcnow()
        return cls(title=title, goal=goal, created_at=now, updated_at=now)

    def can_transition_to(self, new_status: TaskStatus) -> bool:
        return new_status in ALLOWED_TRANSITIONS[self.status]

    def touch(self) -> None:
        self.updated_at = _utcnow()
