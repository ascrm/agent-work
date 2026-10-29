from functools import lru_cache
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置。所有配置集中在这里，不散落在业务代码中。

    环境变量优先级高于 .env 文件，变量名带 APP_ 前缀，
    例如 APP_DATABASE_URL 覆盖 database_url。
    """

    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_", extra="ignore")

    env: str = "local"
    database_url: str = "sqlite+aiosqlite:///./app.db"
    log_level: str = "INFO"
    # NoDecode：让下面的 validator 拿到原始字符串，而不是先按 JSON 解析。
    # 否则 APP_CORS_ORIGINS= 这种空值会直接报 SettingsError。
    cors_origins: Annotated[list[str], NoDecode] = []

    # ---- 大模型（W2）----
    # 默认 MiniMax（OpenAI 兼容）；换厂商改 base_url 和 model 即可
    llm_api_key: str = ""
    llm_base_url: str = "https://api.minimax.chat/v1"
    llm_model: str = "MiniMax-M3.1"
    llm_timeout: float = 30.0
    llm_max_retries: int = 2
    # MiniMax 专用：关闭思考链，否则 <think> 内容会混进回答。
    # 换成别家时如果接口不认这个参数，把它设为 false。
    llm_disable_thinking: bool = True
    # 工具调用循环的最大轮数，防止模型无限调用工具
    assistant_max_steps: int = 5

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
