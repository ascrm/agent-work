from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.llm.client import LLMClient
from app.repositories.task_repository import TaskRepository
from app.services.assistant_service import AssistantService
from app.services.task_service import TaskService

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_task_repository(session: SessionDep) -> TaskRepository:
    return TaskRepository(session)


def get_task_service(
    repository: Annotated[TaskRepository, Depends(get_task_repository)],
) -> TaskService:
    return TaskService(repository)


TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]


# 模型客户端全进程共用一个即可（内部维护连接池）
_llm_client = LLMClient()


def get_llm_client() -> LLMClient:
    return _llm_client


LLMClientDep = Annotated[LLMClient, Depends(get_llm_client)]


def get_assistant_service(session: SessionDep, llm: LLMClientDep) -> AssistantService:
    return AssistantService(llm, session)


AssistantServiceDep = Annotated[AssistantService, Depends(get_assistant_service)]
