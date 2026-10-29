"""工具层。

工具由两部分组成：
1. schema —— 告诉模型"有哪些工具、参数是什么"（JSON Schema）
2. 执行函数 —— 真正干活的那段代码

模型只会输出"我要调用谁、参数是什么"，执行永远发生在这里。
"""

import json
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task

logger = logging.getLogger("app.tools")

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "query_task_status",
            "description": (
                "根据任务 ID 查询任务的状态、执行结果和失败原因。用户询问某个任务的进展时使用。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "integer",
                        "description": "任务 ID，整数",
                    }
                },
                "required": ["task_id"],
            },
        },
    }
]


async def _query_task_status(args: dict[str, Any], session: AsyncSession) -> dict[str, Any]:
    task_id = args.get("task_id")
    if not isinstance(task_id, int):
        return {"error": "task_id 必须是整数"}

    task = await session.get(Task, task_id)
    if task is None:
        return {"error": f"任务 {task_id} 不存在"}

    return {
        "id": task.id,
        "title": task.title,
        "status": task.status.value,
        "result": task.result,
        "error": task.error,
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat(),
    }


_HANDLERS = {
    "query_task_status": _query_task_status,
}


async def execute_tool(name: str, arguments: str, session: AsyncSession) -> str:
    """执行工具，永远返回字符串。

    注意：工具失败时**不抛异常**，而是把错误作为结果返回给模型。
    这样模型能自己看到"任务不存在"，然后决定怎么回复用户；
    如果直接抛异常，这一轮对话就中断了。
    """
    try:
        args = json.loads(arguments or "{}")
    except json.JSONDecodeError:
        return json.dumps({"error": "工具参数不是合法 JSON"}, ensure_ascii=False)

    handler = _HANDLERS.get(name)
    if handler is None:
        return json.dumps({"error": f"未知工具：{name}"}, ensure_ascii=False)

    try:
        result = await handler(args, session)
    except Exception as exc:  # noqa: BLE001  工具层必须兜住所有异常
        logger.exception("工具执行失败 name=%s", name)
        return json.dumps({"error": f"工具执行失败：{exc}"}, ensure_ascii=False)

    return json.dumps(result, ensure_ascii=False)
