# Agent 开发转型工作区

Java / Spring Boot 后端 → Python AI 应用 → Agent 开发工程师，8 周计划的工作区。

配套方案：`docs/Agent开发工程师_8周转型方案.docx`

## 目录约定

| 目录 | 放什么 | 判断标准 |
|---|---|---|
| `project/` | **唯一持续演进的主项目** | 这段代码第 5 周还会用到吗？会 → 放这里 |
| `labs/` | 一次性实验、语法练习、playground | 只是试试看 → 放这里，可以随时删 |
| `notes/` | 每周学习笔记 | 概念、踩坑、结论 |
| `docs/` | 方案文档等长期资料 | |
| `journal.md` | 每日 10 分钟记录 | 完成 / 问题 / 方案 / 下一步 |

**重要**：没有"按周复制的项目目录"。主项目只有 `project/` 一份，每周在它上面加能力。
每周结束时打 tag 冻结进度：

```bash
git tag w01
```

## 快速开始

```bash
cd project
python -m uv sync
python -m uv run pytest
python -m uv run uvicorn app.main:app --reload
```

打开 http://127.0.0.1:8000/docs 看自动生成的接口文档。

## 8 周进度

- [ ] W1 Python 后端基础 —— 任务 API + 测试
- [ ] W2 大模型应用开发 —— 模型调用 / 结构化输出 / Tool Calling / SSE
- [ ] W3 Agent 核心机制 —— LangGraph 状态图
- [ ] W4 RAG、记忆与持久化
- [ ] W5 项目主体开发
- [ ] W6 可靠性、评估与部署
- [ ] W7 作品集打磨
- [ ] W8 岗位匹配与求职准备
