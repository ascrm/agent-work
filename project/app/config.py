from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置。所有配置集中在这里，不散落在业务代码中。

    环境变量优先级高于 .env 文件，变量名带 APP_ 前缀，
    例如 APP_DATABASE_URL 覆盖 database_url。
    """

    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_", extra="ignore")

    env: str = "local"
    database_url: str = "sqlite+aiosqlite:///./app.db"
    log_level: str = "INFO"
    cors_origins: list[str] = []

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        # 环境变量只能传字符串，这里把 "a,b" 拆成列表
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    """缓存实例，避免每次调用都重新读取环境变量。"""
    return Settings()


settings = get_settings()
