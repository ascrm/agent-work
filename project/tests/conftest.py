import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import Base, get_session
from app.main import create_app


@pytest.fixture
async def app(tmp_path):
    """每个测试用独立的临时数据库，测试之间完全隔离。

    注意：ASGITransport 不会触发 lifespan，所以这里手动建表，
    并覆盖 get_session 依赖指向测试库。
    """
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_session():
        async with session_factory() as session:
            yield session

    test_app = create_app()
    test_app.dependency_overrides[get_session] = override_get_session

    yield test_app

    await engine.dispose()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client
