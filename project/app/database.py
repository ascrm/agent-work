from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。"""


# 引擎 = 连接池，整个进程只创建一次
engine = create_async_engine(settings.database_url, echo=False)

# 会话工厂 = 每次请求创建一次会话（类比 MyBatis 的 SqlSession）
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI 依赖：每个请求一个会话，请求结束自动关闭。"""
    async with SessionLocal() as session:
        yield session


async def init_db() -> None:
    # 教学项目用 create_all 建表；真实项目应使用 Alembic 管理迁移
    from app.models import task as _task  # noqa: F401  导入以注册模型

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    await engine.dispose()
