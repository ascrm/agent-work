from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.repositories.task_repository import TaskRepository
from app.services.task_service import TaskService

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_task_repository(session: SessionDep) -> TaskRepository:
    return TaskRepository(session)


def get_task_service(
    repository: Annotated[TaskRepository, Depends(get_task_repository)],
) -> TaskService:
    return TaskService(repository)


TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
