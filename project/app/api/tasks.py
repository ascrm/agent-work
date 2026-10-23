from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.models.task import Task, TaskCreate, TaskUpdate
from app.repositories.task_repository import TaskRepository, get_task_repository

router = APIRouter(prefix="/tasks", tags=["tasks"])

TaskRepo = Annotated[TaskRepository, Depends(get_task_repository)]


@router.post("", response_model=Task, status_code=status.HTTP_201_CREATED)
async def create_task(payload: TaskCreate, repo: TaskRepo) -> Task:
    task = Task.new(title=payload.title, goal=payload.goal)
    return repo.add(task)


@router.get("", response_model=list[Task])
async def list_tasks(repo: TaskRepo) -> list[Task]:
    return repo.list()


@router.get("/{task_id}", response_model=Task)
async def get_task(task_id: UUID, repo: TaskRepo) -> Task:
    task = repo.get(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    return task


@router.patch("/{task_id}", response_model=Task)
async def update_task(task_id: UUID, payload: TaskUpdate, repo: TaskRepo) -> Task:
    task = repo.get(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    if payload.status is not None and payload.status != task.status:
        if not task.can_transition_to(payload.status):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"非法状态流转：{task.status} -> {payload.status}",
            )
        task.status = payload.status

    if payload.title is not None:
        task.title = payload.title
    if payload.result is not None:
        task.result = payload.result
    if payload.error is not None:
        task.error = payload.error

    task.touch()
    return repo.save(task)
