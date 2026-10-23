from typing import Protocol
from uuid import UUID

from app.models.task import Task


class TaskRepository(Protocol):
    """数据访问接口。W4 接入 PostgreSQL 时新增实现即可，路由层不用改。"""

    def add(self, task: Task) -> Task: ...

    def get(self, task_id: UUID) -> Task | None: ...

    def list(self) -> list[Task]: ...

    def save(self, task: Task) -> Task: ...

    def clear(self) -> None: ...


class InMemoryTaskRepository:
    """W1 用的内存实现。进程重启数据即丢失 —— 这是有意为之，不是缺陷。"""

    def __init__(self) -> None:
        self._tasks: dict[UUID, Task] = {}

    def add(self, task: Task) -> Task:
        self._tasks[task.id] = task
        return task

    def get(self, task_id: UUID) -> Task | None:
        return self._tasks.get(task_id)

    def list(self) -> list[Task]:
        # 新任务排在前面
        return sorted(self._tasks.values(), key=lambda t: t.created_at, reverse=True)

    def save(self, task: Task) -> Task:
        self._tasks[task.id] = task
        return task

    def clear(self) -> None:
        self._tasks.clear()


_repository = InMemoryTaskRepository()


def get_task_repository() -> TaskRepository:
    """FastAPI 依赖注入入口。测试里可以直接覆写它。"""
    return _repository
