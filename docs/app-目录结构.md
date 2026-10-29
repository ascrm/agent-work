# app 目录结构说明

项目路径：`project/app`

这份文档回答一个问题：**每个包负责什么，新代码该放哪里。**

---

## 一、总览

```
project/
├── pyproject.toml              依赖声明（≈ pom.xml）
├── uv.lock                    精确版本锁定
├── .env.example               配置示例
├── README.md                  项目说明与阅读顺序
├── examples/                  教学用单文件示例（不属于正式代码）
│   └── single_file_app.py
├── app/                       ← 应用代码
│   ├── main.py                应用组装入口
│   ├── config.py              配置
│   ├── database.py            数据库连接
│   ├── api/                   HTTP 层
│   │   ├── deps.py            依赖注入链
│   │   └── v1/
│   │       ├── health.py      健康检查
│   │       └── tasks.py       任务接口
│   ├── schemas/               接口数据结构（DTO）
│   │   ├── common.py          通用分页
│   │   └── task.py            任务的请求/响应模型
│   ├── services/              业务规则
│   │   └── task_service.py
│   ├── repositories/          数据访问
│   │   └── task_repository.py
│   ├── models/                数据库表结构（ORM）
│   │   └── task.py
│   └── core/                  横切关注点
│       ├── exceptions.py      业务异常定义
│       ├── handlers.py        异常 → HTTP 响应
│       ├── logging.py         日志配置
│       └── middleware.py      request_id / 耗时
└── tests/                     测试
```

---

## 二、每个包负责什么

### `app/main.py` —— 应用组装

只做一件事：把各个部件装成一个 `FastAPI` 对象。

- 注册中间件（`middleware.py`）
- 注册异常处理器（`handlers.py`）
- 挂载路由（`api/v1/*`）
- 定义生命周期 `lifespan`（启动建表、关闭释放连接池）

**不放**：任何业务逻辑。

> Java 对照：`@SpringBootApplication` 主类 + `WebMvcConfigurer`。

---

### `app/config.py` —— 配置

所有配置集中在一处，从环境变量或 `.env` 读取。

- `database_url`：数据库地址
- `log_level`：日志级别
- `cors_origins`：跨域白名单

**不放**：业务常量（比如状态流转规则，那属于业务）。

> Java 对照：`application.yml` + `@ConfigurationProperties`。

---

### `app/database.py` —— 数据库连接

- `Base`：所有 ORM 模型的基类
- `engine`：连接池，进程级单例
- `SessionLocal`：会话工厂
- `get_session()`：FastAPI 依赖，每个请求一个会话
- `init_db()` / `close_db()`：建表与释放

**不放**：任何具体表的定义、任何 SQL。

> Java 对照：`DataSource` + `SqlSessionFactory`。

---

### `app/models/` —— 数据库表结构（ORM）

每个文件对应一张表。

- `task.py`：`tasks` 表 + `TaskStatus` 枚举

**放**：字段定义、列约束、索引、表间关系。
**不放**：业务规则、请求校验、HTTP 相关的东西。

> Java 对照：JPA 的 `@Entity`。

---

### `app/schemas/` —— 接口数据结构（DTO）

定义"请求长什么样、响应长什么样"。

- `task.py`：`TaskCreate` / `TaskUpdate` / `TaskRead`
- `common.py`：`Page[T]` 通用分页

**放**：字段校验规则（`min_length`、`max_length`）、响应字段裁剪。
**不放**：数据库映射。

**为什么和 models 分开？**
两者会分叉。表里以后可能加 `owner_id` 但接口不返回；接口可能需要 `page` 这种不属于表的字段。
混在一起，改数据库就会被动改接口。

> Java 对照：DTO + Bean Validation。

---

### `app/repositories/` —— 数据访问

只负责和数据库打交道：增删改查、分页、排序。

- `task_repository.py`：`add` / `get` / `list` / `save`

**放**：SQL / ORM 查询。
**不放**：业务判断（"这个状态能不能改"不属于这里）。

**为什么单独一层？**
换数据库、写单元测试时，业务代码不用动。这是"可测试"和"可替换"的前提。

> Java 对照：`@Repository` / MyBatis Mapper。

---

### `app/services/` —— 业务规则

系统里"什么情况下允许做什么"。

- `task_service.py`：状态机白名单、非法流转拒绝、组装分页结果

**放**：业务流程、规则校验、跨 repository 的编排。
**不放**：HTTP 细节（状态码、请求头）、SQL。

> Java 对照：`@Service`。

---

### `app/api/` —— HTTP 层

- `deps.py`：依赖注入链 `session → repository → service`
- `v1/tasks.py`：路由，接收参数、调用 service、返回结果
- `v1/health.py`：存活 / 就绪探针

**放**：路由声明、参数声明、HTTP 状态码、`response_model`。
**不放**：业务判断、SQL。

路由函数应该很薄——超过 10 行通常意味着有逻辑该下沉到 service。

> Java 对照：`@RestController` + `@RequestMapping`。

---

### `app/core/` —— 横切关注点

被各层复用、但不属于任何一层的代码。

| 文件 | 职责 |
|---|---|
| `exceptions.py` | 定义 `NotFoundError`、`ConflictError` 等，业务层直接抛 |
| `handlers.py` | 把异常转成统一 JSON 错误结构 |
| `logging.py` | 日志格式与级别 |
| `middleware.py` | 生成 `request_id`、记录耗时 |

**放**：跨多个模块的通用能力。
**不放**：只服务某一个业务的东西。

> Java 对照：`@ControllerAdvice` + `Filter` / `Interceptor`。

---

### `app/__init__.py`、各子包的 `__init__.py`

标记这是一个包。有些会做统一导出，例如：

```python
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate
```

这样别处可以 `from app.schemas import TaskCreate`，缩短导入路径。
不是必须的，但能减少"这个类到底在哪个文件"的查找成本。

---

## 三、依赖方向（最重要的规则）

```
        api/
         ↓
      services/
         ↓
    repositories/
         ↓
       models/  ←── database.py ←── config.py
         
   schemas/  被 api、services 使用
   core/     被所有层使用
```

规则：

1. **只能向下依赖，不能反向**。`services` 不能 import `api`，`repositories` 不能 import `services`。
2. **同层之间尽量不互相依赖**。需要协作就往下走一层。
3. `main.py` 是唯一允许"什么都知道"的地方，它负责组装。

违反这些规则的典型症状：循环导入（`ImportError: cannot import name ...`）。

---

## 四、一个请求的完整路径

以 `POST /api/v1/tasks` 为例：

```
1. Uvicorn 收到请求
2. main.py 注册的 middleware       生成 request_id，记录开始时间
3. 路由匹配 api/v1/tasks.py        create_task()
4. 依赖注入 api/deps.py            创建 session → repository → service
5. services/task_service.py        create()，业务规则
6. repositories/task_repository.py add()，写库并 commit
7. 回到路由                         response_model 把 ORM 对象转成 JSON
8. middleware                      记录耗时，写 X-Request-ID
9. 返回响应

异常路径：任何一层抛 AppError
   → core/handlers.py 捕获
   → 返回 {"error": {"code", "message", "request_id"}}
```

---

## 五、新代码该放哪？判断表

| 你要写的东西 | 放哪 | 判断依据 |
|---|---|---|
| 新的接口路径 | `api/v1/` | 它处理 HTTP |
| 新的请求/响应格式 | `schemas/` | 它描述接口契约 |
| 新的数据库表 | `models/` | 它描述表结构 |
| 新的一条 SQL | `repositories/` | 它只碰数据库 |
| "什么情况下允许 X" | `services/` | 它是业务规则 |
| 新的错误类型 | `core/exceptions.py` | 跨层使用 |
| 请求日志、鉴权、限流 | `core/` | 横切关注点 |
| 新的配置项 | `config.py` | 配置集中管理 |
| 模型调用、重试、token 统计 | `app/llm/` | 只和模型打交道 |
| 新的 Agent 工具 | `app/tools/` | 给模型调用的能力 |
| 工具调用编排、多步流程 | `app/services/` | 业务编排 |

**一句话判断**：把这段代码拷到另一个项目里还有意义吗？

- 有意义 → `core/`
- 只对这个业务有意义 → 按上表分层

---

## 六、最容易混淆的两组

| | `models/task.py` | `schemas/task.py` |
|---|---|---|
| 描述什么 | 数据库表 | 接口契约 |
| 字段变化影响 | 数据库迁移 | 前端 |
| 典型内容 | 列类型、索引、外键 | 校验规则、必填/可选 |
| Java 对照 | `@Entity` | DTO |

| | `repositories/` | `services/` |
|---|---|---|
| 描述什么 | 怎么存取 | 什么情况下允许 |
| 会不会有 if | 基本没有 | 很多 |
| 换数据库要改吗 | 要 | 不要 |
| Java 对照 | `@Repository` | `@Service` |

---

## 七、W2 新增的模块

```
app/
├── llm/                      模型适配层
│   └── client.py             OpenAI 兼容客户端、超时、重试、Token 统计
├── tools/                    工具层
│   └── task_tools.py         工具 schema + 执行函数
├── schemas/assistant.py      对话的请求/响应模型
├── services/assistant_service.py   工具调用循环（W2 的核心）
└── api/v1/assistant.py       对话接口 /chat 与 /chat/stream
```

### `app/llm/` —— 模型适配层

唯一知道"用的是哪家模型"的地方。

- `LLMClient.chat()`：普通调用，返回 `Completion`（内容 + tool_calls + usage）
- `LLMClient.stream()`：流式调用，逐个吐出文本增量
- 内部处理超时、指数退避重试、异常分类

业务代码只认识 `Completion` / `ToolCall` / `Usage` 三个类型，换厂商只改这个文件。

### `app/tools/` —— 工具层

一个工具由两部分组成：

1. `TOOL_SCHEMAS`：告诉模型有哪些工具、参数是什么（JSON Schema）
2. 执行函数：真正干活的代码

`execute_tool()` 永远不会抛异常——工具失败时把错误作为**结果**返回给模型，
让模型自己决定怎么回复用户。

### `app/services/assistant_service.py` —— 工具调用循环

W2 的全部核心：

```
用户消息 + 工具列表 → 模型
     ↑                  ↓
     └── 工具结果 ←── tool_calls
```

`chat()` 跑完整循环并返回结果；`chat_stream()` 用 SSE 推送事件。

### `app/api/v1/assistant.py` —— 对话接口

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/v1/assistant/chat` | 返回最终回答 + 工具轨迹 + token 用量 |
| POST | `/api/v1/assistant/chat/stream` | SSE 流式版本 |

### 依赖方向没有变

```
api/v1/assistant.py
        ↓
services/assistant_service.py
        ↓                    ↘
tools/task_tools.py          llm/client.py
        ↓
    models/task.py
```

`llm` 和 `tools` 是同层的两个协作方，都不依赖 `api`。
