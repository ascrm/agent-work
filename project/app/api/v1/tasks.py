from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import TaskServiceDep
from app.schemas.common import Page
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
async def create_task(payload: TaskCreate, service: TaskServiceDep) -> TaskRead:
    task = await service.create(payload)
    return TaskRead.model_validate(task)


@router.get("", response_model=Page[TaskRead])
async def list_tasks(
    service: TaskServiceDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[TaskRead]:
    return await service.list(limit, offset)


@router.get("/{task_id}", response_model=TaskRead)
async def get_task(task_id: int, service: TaskServiceDep) -> TaskRead:
    task = await service.get(task_id)
    return TaskRead.model_validate(task)


@router.patch("/{task_id}", response_model=TaskRead)
async def update_task(task_id: int, payload: TaskUpdate, service: TaskServiceDep) -> TaskRead:
    task = await service.update(task_id, payload)
    return TaskRead.model_validate(task)
