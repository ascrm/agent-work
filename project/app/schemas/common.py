from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """统一分页响应。items 的类型由调用方指定。"""

    items: list[T]
    total: int
    limit: int
    offset: int
