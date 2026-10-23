# Agent Workbench

企业智能任务执行 Agent 的主项目。按周演进，每一周结束时它都是一个能跑起来的完整服务。

## 运行

```bash
python -m uv sync
python -m uv run pytest
python -m uv run uvicorn app.main:app --reload
```

接口文档：http://127.0.0.1:8000/docs

## 目录

```
app/
├── main.py          # 应用入口（工厂函数 create_app）
├── api/             # HTTP 路由
├── models/          # Pydantic 模型 = DTO + 领域状态
├── repositories/    # 数据访问（现在是内存，W4 换 PostgreSQL）
├── llm/             # W2 模型适配层（超时 / 重试 / 成本）
├── tools/           # W2 Tool Calling
├── graph/           # W3 LangGraph 状态图
├── rag/             # W4 检索
└── observability/   # W6 日志 / 指标
tests/
```

## 当前进度

W1：任务 CRUD + 状态机 + 测试。

## 设计说明

**为什么先做内存仓库？**
W1 的目标是打通 HTTP 链路和测试习惯，不是持久化。`TaskRepository` 是一个 Protocol，
W4 加 PostgreSQL 时只需要新增一个实现，路由层不用改。

**为什么状态流转要白名单？**
Agent 的任务会由程序自动推进状态，非法流转一旦发生就是数据一致性问题。
把规则写在 `ALLOWED_TRANSITIONS` 里，比散落在各个接口里可靠。
