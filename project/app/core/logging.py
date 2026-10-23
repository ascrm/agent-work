import logging
import sys

from app.config import settings


def setup_logging() -> None:
    """一次性配置根日志器。force=True 让重复调用（如测试）也能生效。"""
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)-8s %(name)s | %(message)s",
        stream=sys.stdout,
        force=True,
    )
