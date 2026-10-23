from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task


class TaskRepository:
    """数据访问层：只负责读写数据库，不含业务规则。

    业务规则（比如状态流转是否合法）放在 service 层。
    这样换数据库、写单元测试时，业务逻辑都不用改。
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, task: Task) -> Task:
        self.session.add(task)
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def get(self, task_id: int) -> Task | None:
        return await self.session.get(Task, task_id)

    async def list(self, limit: int, offset: int) -> tuple[list[Task], int]:
        total = await self.session.scalar(select(func.count()).select_from(Task))
        result = await self.session.scalars(
            select(Task).order_by(Task.id.desc()).limit(limit).offset(offset)
        )
        return list(result), total or 0

    async def save(self, task: Task) -> Task:
        await self.session.commit()
        await self.session.refresh(task)
        return task
