from app.core.exceptions import ConflictError, NotFoundError
from app.models.task import Task, TaskStatus
from app.repositories.task_repository import TaskRepository
from app.schemas.common import Page
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate

# 状态流转白名单。不在这张表里的流转一律拒绝。
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


class TaskService:
    """业务层：这里放"什么情况下允许做什么"的规则。"""

    def __init__(self, repository: TaskRepository) -> None:
        self.repository = repository

    async def create(self, payload: TaskCreate) -> Task:
        return await self.repository.add(Task(title=payload.title, goal=payload.goal))

    async def get(self, task_id: int) -> Task:
        task = await self.repository.get(task_id)
        if task is None:
            raise NotFoundError(f"任务 {task_id} 不存在")
        return task

    async def list(self, limit: int, offset: int) -> Page[TaskRead]:
        tasks, total = await self.repository.list(limit, offset)
        return Page[TaskRead](
            items=[TaskRead.model_validate(task) for task in tasks],
            total=total,
            limit=limit,
            offset=offset,
        )

    async def update(self, task_id: int, payload: TaskUpdate) -> Task:
        task = await self.get(task_id)

        if payload.status is not None and payload.status != task.status:
            if payload.status not in ALLOWED_TRANSITIONS[task.status]:
                raise ConflictError(f"非法状态流转：{task.status} -> {payload.status}")
            task.status = payload.status

        # 只更新显式传入的字段，没传的保持原值
        for field in ("title", "result", "error"):
            value = getattr(payload, field)
            if value is not None:
                setattr(task, field, value)

        return await self.repository.save(task)
