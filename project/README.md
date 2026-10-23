# Agent Workbench

一个**最小但完整**的 Web 后端模板。目标不是功能多，而是把"一个后端该有的东西"都用最少的代码摆出来，
方便你逐文件读完。

技术栈：Python 3.11+ · FastAPI · Pydantic · SQLAlchemy 2.0 (async) · SQLite · pytest · ruff

## 快速开始

```bash
cp .env.example .env          # 可选，不复制也能跑（有默认值）
python -m uv sync
python -m uv run pytest       # 13 个测试
python -m uv run uvicorn app.main:app --reload
```

- 接口文档：http://127.0.0.1:8000/docs
- 健康检查：`GET /health`、`GET /health/ready`

## 建议阅读顺序

按这个顺序读，每个文件只依赖前面读过的：

| 顺序 | 文件 | 解决什么问题 |
|---|---|---|
| 1 | `app/config.py` | 配置从哪来、为什么要集中管理 |
| 2 | `app/database.py` | 连接池、会话、依赖注入式的事务边界 |
| 3 | `app/models/task.py` | 数据库表长什么样（ORM） |
| 4 | `app/schemas/task.py` | 接口的请求/响应长什么样（DTO） |
| 5 | `app/repositories/task_repository.py` | 只做数据库读写 |
| 6 | `app/services/task_service.py` | 业务规则：状态机能怎么走 |
| 7 | `app/core/exceptions.py` | 业务异常怎么定义 |
| 8 | `app/core/handlers.py` | 异常怎么变成 HTTP 响应 |
| 9 | `app/core/middleware.py` | request_id 和耗时日志 |
| 10 | `app/api/deps.py` | 依赖注入链：session → repo → service |
| 11 | `app/api/v1/tasks.py` | 路由：只做参数接收和结果返回 |
| 12 | `app/main.py` | 把所有东西装起来 |
| 13 | `tests/` | 怎么隔离数据库、怎么测试 |

## 一个请求的完整路径

以 `POST /api/v1/tasks` 为例：

```
请求
 └─ request_context_middleware   生成 request_id，记录开始时间
     └─ 路由函数 tasks.create_task   接收 TaskCreate，参数校验失败直接 422
         └─ Depends                创建 AsyncSession → TaskRepository → TaskService
             └─ service.create     业务规则
                 └─ repository.add  写库 + commit + refresh
                     └─ 返回 ORM 对象
         └─ response_model=TaskRead   ORM 对象 → JSON
     └─ 记录耗时、写 X-Request-ID 响应头
响应
```

任何一层抛 `AppError`，都会被 `handlers.py` 捕获，转成统一结构：

```json
{"error": {"code": "not_found", "message": "任务 999 不存在", "request_id": "a1b2c3d4e5f6"}}
```

## 目录结构

```
app/
├── main.py                 # 应用组装：中间件、异常处理、路由
├── config.py               # 配置（环境变量 / .env）
├── database.py             # 引擎、会话、建表
├── api/
│   ├── deps.py             # 依赖注入链
│   └── v1/
│       ├── health.py       # 存活 / 就绪探针
│       └── tasks.py        # 任务路由
├── models/task.py          # SQLAlchemy ORM 模型
├── schemas/                # Pydantic 请求/响应模型
│   ├── common.py           # 通用分页 Page[T]
│   └── task.py
├── repositories/           # 数据访问
├── services/               # 业务规则
└── core/                   # 横切关注点
    ├── exceptions.py       # 业务异常
    ├── handlers.py         # 异常 → HTTP
    ├── logging.py          # 日志配置
    └── middleware.py       # request_id / 耗时
tests/
├── conftest.py             # 每个测试独立临时数据库
├── test_health.py
└── test_tasks.py
```

## 对照 Spring Boot

| 这里 | Spring Boot | 说明 |
|---|---|---|
| `api/v1/tasks.py` | `@RestController` | 路由只做参数接收和返回 |
| `services/task_service.py` | `@Service` | 业务规则 |
| `repositories/` | `@Repository` / MyBatis Mapper | 数据访问 |
| `models/` | `@Entity` | 数据库结构 |
| `schemas/` | DTO + Bean Validation | 接口结构 |
| `Depends(get_session)` | 事务管理器 + `@Autowired` | 但这里是普通函数调用，没有容器扫描 |
| `handlers.py` | `@ControllerAdvice` | 统一异常处理 |
| `middleware.py` | `Filter` / `Interceptor` | 横切逻辑 |
| `config.py` | `application.yml` + `@ConfigurationProperties` | 配置集中管理 |
| `lifespan` | `@PostConstruct` / 启动钩子 | 启动与关闭 |
| `alembic`（未引入） | Flyway / Liquibase | 真实项目应使用迁移工具 |

## 有意的取舍

这是教学模板，刻意保持小：

- **SQLite 而不是 PostgreSQL**：零安装、零配置。换库只改 `APP_DATABASE_URL` 和驱动依赖。
- **`create_all` 而不是 Alembic**：启动即建表，便于理解。真实项目应加迁移。
- **没有用户认证 / 权限**：会在后续周次加。
- **没有 Redis / 消息队列**：当前用不上，加了只会分散注意力。
- **没有 Docker**：等第 6 周部署时再加。

## 常见问题

**为什么 model 和 schema 要分开？**
`models/task.py` 描述数据库表，`schemas/task.py` 描述接口契约。两者会分叉——
比如表里以后加 `owner_id`，接口未必需要返回；反过来，接口可能需要 `page` 这种不属于表的字段。

**为什么 repository 里直接 commit？**
模板阶段简化成这样。更严谨的做法是 service 控制事务边界（一个业务操作可能跨多个 repository 调用），
到项目变大时会调整。

**为什么测试不用真实数据库？**
每个测试一个临时 SQLite 文件，跑完即删。快、互不影响。集成测试阶段再引入 PostgreSQL 容器。

**为什么返回的时间没有时区（`2026-10-23T06:21:45` 而不是带 `Z`）？**
SQLite 不保存时区信息，即使列定义成 `DateTime(timezone=True)`，取出来也是 naive datetime。
PostgreSQL 没有这个问题。当前阶段不影响使用，接入 PG 后会自动消失。
