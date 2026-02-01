# Window Quote Agent — MVP 构建分步计划

这个计划将 `architecture.md` 拆解为 6 个阶段，共 25 个微任务。请按顺序执行。

- 按 tasks.md 中的顺序，**一次只完成一个任务**。
- 每完成一个任务就停下，由你进行测试；测试通过并提交到 GitHub 后，再继续下一个任务。

### CODING PROTOCOL ###
开发守则：
- 严格用最少的代码完成当前任务
- 不进行大规模改动
- 不做无关编辑，专注于你正在开发的任务
- 代码必须精确、模块化、可测试
- 不破坏现有功能
- 如果需要我做任何配置（例如 Supabase/AWS），请明确告诉我

---

## 第一阶段：骨架与基础设施 (Project Skeleton)
**目标**：建立项目结构，配置依赖，确保环境可用。

- [x] **Task 1.1: 初始化项目结构与依赖**
    - **操作**：创建 `window-quote-agent` 根目录。按照 `architecture.md` 第 4 节创建所有一级和二级文件夹（空文件夹即可）。初始化 `pyproject.toml`，添加 `fastapi`, `uvicorn`, `pydantic`, `langgraph`, `langchain`, `openai` (或兼容库), `pytest` 依赖。
    - **验证**：运行 `poetry install` (或 `uv sync`) 无报错。
    - **文件**：`pyproject.toml`, 目录结构。

- [ ] **Task 1.2: 环境变量与配置加载**
    - **操作**：创建 `.env.example` 和 `apps/api/config.py`。使用 Pydantic `BaseSettings` 实现配置加载。定义 MVP 必需变量：`APP_ENV`, `MODEL_BASE_URL`, `MODEL_NAME`。
    - **验证**：编写一个简单的脚本打印配置项，确认能读取 `.env` 文件。
    - **文件**：`.env.example`, `apps/api/config.py`。

- [ ] **Task 1.3: 基础日志系统**
    - **操作**：实现 `packages/observability/logger.py`。配置结构化 JSON 日志，确保输出包含 timestamp 和 level。
    - **验证**：运行脚本调用 logger，检查 stdout 是否输出符合格式的 JSON。
    - **文件**：`packages/observability/logger.py`。

---

## 第二阶段：核心领域逻辑 (Core Domain - Tools & Catalog)
**目标**：实现“不可协商”的确定性逻辑，即商品数据和价格计算。**此阶段不涉及 LLM。**

- [ ] **Task 2.1: 商品数据模型 (Catalog Models)**
    - **操作**：在 `packages/catalog/models.py` 中定义 Pydantic 模型：`Series` (系列), `Glass` (玻璃), `Hardware` (五金)。
    - **验证**：编写测试，实例化几个模型对象，确保字段类型校验生效。
    - **文件**：`packages/catalog/models.py`。

- [ ] **Task 2.2: 静态数据源 (Catalog Data)**
    - **操作**：在 `packages/catalog/data/` 下创建 `series.json`, `glass.json`, `hardware.json`。填入 2-3 条真实的测试数据（例如：65/70系列，双层钢化玻璃）。
    - **验证**：JSON 格式合法且符合 Task 2.1 的 Schema。
    - **文件**：`packages/catalog/data/*.json`。

- [ ] **Task 2.3: Catalog Repository**
    - **操作**：实现 `packages/catalog/repository.py`。实现简单的 `load_data()` 和 `get_series_by_id()` 方法。
    - **验证**：编写 `tests/test_catalog.py`，确认能从 JSON 读取数据并返回对象。
    - **文件**：`packages/catalog/repository.py`。

- [ ] **Task 2.4: 单位解析工具 (Unit Parsing)**
    - **操作**：实现 `packages/tools/utils/unit_parse.py`。编写函数将 "1.2m", "1200mm", "1米2" 等统一转换为 float (米)。
    - **验证**：编写单元测试覆盖 5 种以上常见输入情况。
    - **文件**：`packages/tools/utils/unit_parse.py`。

- [ ] **Task 2.5: 核心定价逻辑 (Pricing Logic)**
    - **操作**：实现 `packages/tools/pricing/calculate_price.py` 和 `pricing_rules.py`。编写函数接受 `width`, `height`, `series_id` 等，计算总价。包含简单的“最小面积”规则（如不足 1.5平米按 1.5平米算）。
    - **验证**：编写 `packages/tools/pricing/tests/test_calc.py`，输入固定参数，断言计算结果准确无误。
    - **文件**：`packages/tools/pricing/*`。

- [ ] **Task 2.6: 工具层封装 (Tool Schema)**
    - **操作**：定义 `packages/tools/base.py` (ToolResult) 和 `packages/tools/registry.py`。将定价逻辑封装为一个标准 Tool 函数，供 Agent 调用。
    - **验证**：编写脚本通过 registry 调用工具，检查返回结构是否为 `ToolResult`。
    - **文件**：`packages/tools/base.py`, `packages/tools/registry.py`。

---

## 第三阶段：LLM 与 知识检索 (LLM & RAG)
**目标**：建立与大模型的连接，并实现最基础的知识检索。

- [ ] **Task 3.1: LLM Client 适配**
    - **操作**：实现 `packages/llm/client.py`。封装 OpenAI 兼容的客户端。实现一个 `chat_completion` 方法。
    - **验证**：配置 `.env` 指向真实 API 或 Mock 服务，运行脚本确认能收到 "Hello"。
    - **文件**：`packages/llm/client.py`。

- [ ] **Task 3.2: 向量库基础 (Vector Store)**
    - **操作**：实现 `packages/rag/vectorstore.py`。使用 `FAISS` 或 `Chroma` (本地版) 初始化一个简单的存储。
    - **验证**：编写测试，插入一条文本，再检索这条文本，确认能搜到。
    - **文件**：`packages/rag/vectorstore.py`。

- [ ] **Task 3.3: 基础 RAG 检索器**
    - **操作**：实现 `packages/rag/retriever.py`。创建一个简单的 `retrieve(query)` 函数。
    - **验证**：集成测试：Indexing 一段关于“断桥铝”的文本，Query "断桥铝是什么"，确认返回结果包含该文本。
    - **文件**：`packages/rag/retriever.py`。

---

## 第四阶段：Agent 工作流 (LangGraph Workflow)
**目标**：这是最复杂的部分。我们将根据 `architecture.md` 逐步构建图节点。

- [x] **Task 4.1: 定义 Agent State**
    - **操作**：实现 `packages/agent/state.py`。定义 `AgentState` TypedDict，包含 `messages`, `requirements`, `selection`, `price_result`, `step`。
    - **验证**：无逻辑验证，代码静态检查通过即可。
    - **文件**：`packages/agent/state.py`。

- [x] **Task 4.2: 节点开发 - Router**
    - **操作**：实现 `packages/agent/nodes/router.py`。编写 Prompt 让 LLM 判断用户是“闲聊/咨询”还是“想要报价”。
    - **验证**：编写测试，输入 "我想装窗户"，断言输出意图为 "quote"。
    - **文件**：`packages/agent/nodes/router.py`。

- [x] **Task 4.3: 节点开发 - Requirement Collection**
    - **操作**：实现 `packages/agent/nodes/collect_requirements.py`。该节点负责调用 LLM 提取用户意图中的尺寸、地点等，并更新 `state.requirements`。
    - **验证**：输入 "我家窗户高2米宽3米"，断言 state 中提取出 `{"h": 2.0, "w": 3.0}`。
    - **文件**：`packages/agent/nodes/collect_requirements.py`。

- [x] **Task 4.4: 节点开发 - Recommendation (RAG Integration)**
    - **操作**：实现 `packages/agent/nodes/recommend.py`。调用 Task 3.3 的检索器，结合 Catalog 数据，让 LLM 推荐一个系列。
    - **验证**：模拟输入，检查节点输出是否包含检索到的 Context 和推荐的 Series ID。
    - **文件**：`packages/agent/nodes/recommend.py`。

- [x] **Task 4.5: 节点开发 - Pricing (Tool Integration)**
    - **操作**：实现 `packages/agent/nodes/price_quote.py`。读取 `state.requirements` 和 `state.selection`，调用 Task 2.6 的定价工具，将结果写入 `state.price_result`。
    - **验证**：单元测试：构造完整的 state 输入，断言 state 更新了正确的价格数据。
    - **文件**：`packages/agent/nodes/price_quote.py`。

- [x] **Task 4.6: 节点开发 - Generate Quote**
    - **操作**：实现 `packages/agent/nodes/generate_quote.py`。根据 `price_result` 生成 Markdown 格式的报价单。
    - **验证**：检查生成的 Markdown 是否包含“总价”和“明细表格”。
    - **文件**：`packages/agent/nodes/generate_quote.py`。

- [x] **Task 4.7: 构建 LangGraph 图**
    - **操作**：在 `packages/agent/graph.py` 中将上述节点连接起来。定义 `workflow.add_edge` 和 `conditional_edges`。
    - **验证**：使用 `langgraph` 的绘图功能（如果可用）或打印 graph 结构，确保拓扑正确。
    - **文件**：`packages/agent/graph.py`。

---

## 第五阶段：API 服务层 (API Layer)
**目标**：通过 HTTP 暴露服务。

- [ ] **Task 5.1: 定义 API Schema**
    - **操作**：实现 `apps/api/schemas/chat.py` 和 `quote.py`。定义请求和响应的 JSON 结构。
    - **验证**：无逻辑验证，代码静态检查。
    - **文件**：`apps/api/schemas/*.py`。

- [ ] **Task 5.2: Chat 接口实现**
    - **操作**：实现 `apps/api/routers/chat.py`。初始化 LangGraph 的 runner，处理 POST 请求，管理简单的内存 Session。
    - **验证**：使用 `curl` 发送 POST 请求，确认能收到 API 的 200 OK 响应。
    - **文件**：`apps/api/routers/chat.py`。

- [ ] **Task 5.3: FastAPI Main 入口**
    - **操作**：完善 `apps/api/main.py`，挂载路由，处理 CORS。
    - **验证**：启动 `uvicorn apps.api.main:app`，访问 `/docs` 查看 Swagger UI。
    - **文件**：`apps/api/main.py`。

---

## 第六阶段：集成与测试 (Integration & Cleanup)
**目标**：端到端验证 MVP 是否工作。

- [ ] **Task 6.1: 基础集成测试**
    - **操作**：编写 `tests/test_quote_flow.py`。模拟一个完整的用户流程：用户说“我要做窗户” -> 机器人问尺寸 -> 用户给尺寸 -> 机器人出报价。
    - **验证**：测试通过，且中间没有 Crash。
    - **文件**：`tests/test_quote_flow.py`。

- [ ] **Task 6.2: 隐私脱敏 (PII)**
    - **操作**：实现 `apps/api/middleware/pii_redaction.py`。在日志输出前正则替换手机号。
    - **验证**：发送包含手机号的请求，检查日志中是否显示为 `***`。
    - **文件**：`apps/api/middleware/pii_redaction.py`。

- [ ] **Task 6.3: Docker 化 (Optional for MVP Local)**
    - **操作**：编写 `apps/api/Dockerfile` 和根目录的 `docker-compose.yml`。
    - **验证**：`docker-compose up` 能成功启动服务并可访问。
    - **文件**：`Dockerfile`, `docker-compose.yml`。