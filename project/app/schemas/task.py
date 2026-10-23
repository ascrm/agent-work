from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.task import TaskStatus


class TaskCreate(BaseModel):
    """创建任务的请求体：字段必填，长度受限。"""

    title: str = Field(min_length=1, max_length=200)
    goal: str = Field(min_length=1, max_length=5000)


class TaskUpdate(BaseModel):
    """更新任务的请求体：全部可选，只更新传入的字段。"""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    status: TaskStatus | None = None
    result: str | None = Field(default=None, max_length=20000)
    error: str | None = Field(default=None, max_length=5000)


class TaskRead(BaseModel):
    """响应体。from_attributes=True 允许直接从 ORM 对象转换。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    goal: str
    status: TaskStatus
    result: str | None
    error: str | None
    created_at: datetime
    updated_at: datetime
