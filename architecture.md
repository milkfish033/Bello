# Window Quote Agent — 完整架构设计（LoRA DeepSeek R1 + LangGraph + RAG + 定价工具）

> 目标：构建一个“智能报价与选品顾问 Agent”，能引导用户完成需求采集 → 选品推荐 → 精确定价 → 结构化报价单输出。  
> 强约束：**数值不出错**、**流程不乱序**、**可追溯可回放**、**隐私最小化**。

---

## 1. 总体架构概览

### 1.1 模块边界（系统组件）
- **apps/api**：对外提供 HTTP API（FastAPI），接入前端/企业微信/钉钉/CRM。
- **packages/agent**：LangGraph 工作流引擎（节点、状态定义、prompt）。
- **packages/tools**：工具层（定价、HTTP、单位解析），确保数值正确与可验证。
- **packages/rag**：知识检索（向量库构建与检索），只用于“推荐依据”，不参与数值。
- **packages/catalog**：结构化产品数据（型材/玻璃/五金），对工具与推荐提供“事实源”。
- **packages/llm**：LLM 访问层（vLLM/OpenAI 兼容），隐藏具体 provider 细节。
- **packages/memory**：短期记忆与（可选）长期偏好记忆。
- **packages/safety**：PII 脱敏与权限策略。
- **packages/observability**：trace/log/metrics + 可回放能力。
- **apps/worker（可选）**：异步任务（构建向量索引、刷新 catalog、定期清理）。

### 1.2 数据与状态的“单一事实源”
- **对话状态（AgentState）**：存于 API 进程内存 + 可选持久化（Redis/DB），每次请求带 `session_id` 拉取/更新。
- **定价规则**：代码内（tools/pricing/pricing_rules.py）为准，版本号写入报价结果。
- **结构化产品数据**：packages/catalog/data（本地 JSON）或升级为 DB。
- **RAG 向量索引**：本地磁盘（FAISS）或外部向量库（Chroma/pgvector），由 worker 构建并供 api 读取。

---

## 2. 服务之间如何连接（连接拓扑）

### 2.1 请求链路（在线推理）
1. Client（Web/CRM） → `apps/api`（FastAPI）
2. API：
   - 加载 `AgentState`（从内存/Redis）
   - 通过 `packages/agent/graph` 运行 LangGraph
3. LangGraph 节点内部调用：
   - `packages/llm/client`：访问 vLLM（DeepSeek R1 LoRA）
   - `packages/rag/retriever`：检索知识片段（向量库）
   - `packages/tools/pricing/calculate_price`：精确定价（Python）
   - `packages/catalog/repository`：读取型材/玻璃/五金数据（结构化）
4. `packages/observability`：记录 trace/log/metrics
5. API 返回最终 `QuoteResponse` 或 `ChatResponse`

### 2.2 离线链路（索引与数据更新）
- `apps/worker` 定期运行：
  - `build_index.py`：从 `docs/` 构建向量索引至 `rag` 后端（本地/外部）
  - `refresh_catalog.py`：同步最新 SKU/价格配置到 `packages/catalog/data/`（或 DB）

---

## 3. 状态存储位置（State Storage）

### 3.1 必选（MVP）
- **Session 状态**：API 内存字典（key=session_id），适合单实例与开发阶段。
- **日志/trace**：stdout/JSON log（可被 docker 收集）。

### 3.2 推荐（上线）
- **Session 状态**：Redis（key=session_id → AgentState JSON）
- **向量索引**：
  - 小规模：本地磁盘（`./data/vectorstore/`）
  - 中大规模：pgvector / Milvus / Chroma Server（外部服务）
- **结构化 catalog**：
  - 初期：本地 JSON（`packages/catalog/data/*.json`）
  - 规模化：PostgreSQL（products/pricing_config 表）
- **可回放数据**：Postgres（traces 表）或对象存储（S3）+ 索引

> 注意：**PII 不落日志，不写入长期记忆**；报价复盘只保留脱敏后字段。

---

## 4. 完整文件结构（不遗漏任何一个文件）

> 说明：以下结构为“推荐工程骨架”。  
> 每个文件都包含“职责说明”。你可以按此逐个实现。

```
window-quote-agent/
├─ README.md
├─ .gitignore
├─ .env.example
├─ pyproject.toml                 # poetry/uv 管理依赖（推荐）
├─ docker-compose.yml
├─ Makefile                       # 常用命令：dev/test/lint
│
├─ apps/
│  ├─ api/                        # FastAPI 服务（主入口）
│  │  ├─ Dockerfile
│  │  ├─ main.py                  # FastAPI app + 路由挂载
│  │  ├─ routers/
│  │  │  ├─ chat.py               # /chat (agent对话)
│  │  │  ├─ quote.py              # /quote (一步到位报价)
│  │  │  ├─ health.py             # /health, /ready
│  │  │  └─ admin.py              # 内部：规则版本、数据刷新（可选）
│  │  ├─ deps.py                  # 依赖注入：LLM client / vector store / db
│  │  ├─ schemas/                 # Pydantic 请求/响应 schema（对外）
│  │  │  ├─ chat.py
│  │  │  ├─ quote.py
│  │  │  ├─ tool_io.py
│  │  │  └─ errors.py
│  │  ├─ middleware/
│  │  │  ├─ tracing.py            # trace_id 注入
│  │  │  ├─ rate_limit.py         # 简易限流（可选）
│  │  │  └─ pii_redaction.py      # 日志脱敏
│  │  └─ config.py                # 环境变量配置（Pydantic Settings）
│  │
│  └─ worker/                     # 可选：异步任务（构建索引/定期更新）
│     ├─ Dockerfile
│     └─ jobs/
│        ├─ build_index.py
│        └─ refresh_catalog.py
│
├─ packages/
│  ├─ agent/                      # LangGraph 核心：状态机+节点
│  │  ├─ __init__.py
│  │  ├─ state.py                 # AgentState 定义（requirements/selection/price/trace）
│  │  ├─ graph.py                 # LangGraph 构建入口
│  │  ├─ nodes/
│  │  │  ├─ router.py             # 判断：咨询 vs 进入报价流程
│  │  │  ├─ collect_requirements.py  # 追问尺寸/地点/噪音等，填 requirements
│  │  │  ├─ recommend.py          # 调用 RAG，产出推荐（series/glass/hardware）
│  │  │  ├─ validate_inputs.py    # 强校验：缺字段/非法值 -> missing_fields
│  │  │  ├─ price_quote.py        # 调用定价工具，拿到 price_result
│  │  │  ├─ generate_quote.py     # 生成结构化报价单（Markdown/JSON）
│  │  │  ├─ fallback.py           # 工具失败/超时/无检索结果的降级策略
│  │  │  └─ finalize.py           # 最终输出格式化、附 trace_id
│  │  ├─ prompts/
│  │  │  ├─ system.md
│  │  │  ├─ router.md
│  │  │  ├─ planner.md            # 如果你用 plan-and-execute
│  │  │  └─ quote_writer.md
│  │  └─ policies/
│  │     ├─ tool_permissions.py   # 工具权限/二次确认（以后接下单用）
│  │     └─ safety_rules.md       # 注入防护、拒答策略
│  │
│  ├─ tools/                      # 工具层：统一接口 + 具体工具实现
│  │  ├─ base.py                  # Tool 抽象、统一返回格式 ToolResult
│  │  ├─ registry.py              # tools 注册与查找
│  │  ├─ validators.py            # schema 校验 + auto-repair（可选）
│  │  ├─ pricing/
│  │  │  ├─ calculate_price.py    # ✅核心：面积/五金/开扇/规则实现
│  │  │  ├─ pricing_rules.py      # 规则表（最小面积、转角、损耗等）
│  │  │  ├─ schemas.py            # Pydantic：PriceInput/PriceOutput
│  │  │  └─ tests/
│  │  │     ├─ test_min_area.py
│  │  │     └─ test_corner_post.py
│  │  ├─ http/
│  │  │  ├─ get.py                # 通用 GET（只读）
│  │  │  └─ post.py               # 通用 POST（写操作：预留）
│  │  └─ utils/
│  │     ├─ unit_parse.py         # “1米多/1200mm/1.2m” 解析成 float(m)
│  │     └─ currency.py
│  │
│  ├─ rag/                        # RAG：索引/检索/融合/引用
│  │  ├─ embeddings.py            # embedding client
│  │  ├─ vectorstore.py           # FAISS/Chroma 适配
│  │  ├─ retriever.py             # query 构造 + topk
│  │  ├─ rerank.py                # 可选：重排
│  │  ├─ prompt_injection.py      # 文档指令剥离/过滤（基础版）
│  │  └─ indexing/
│  │     ├─ build.py              # 从 docs/ 构建索引
│  │     ├─ chunking.py           # 切分策略
│  │     └─ sources.py            # 数据源：产品手册/FAQ/规则说明
│  │
│  ├─ catalog/                    # 结构化产品数据（series/glass/hardware）
│  │  ├─ models.py                # Pydantic：Series/Glass/Hardware
│  │  ├─ repository.py            # 读取本地json/数据库
│  │  └─ data/
│  │     ├─ series.json
│  │     ├─ glass.json
│  │     └─ hardware.json
│  │
│  ├─ llm/                        # LLM 访问层（vLLM/OpenAI兼容）
│  │  ├─ client.py                # chat/completions/function calling 适配
│  │  ├─ models.py                # model config（base/lora）
│  │  └─ formatting.py            # JSON 输出约束/修复（轻量）
│  │
│  ├─ memory/                     # 记忆：先短期，长期可后加
│  │  ├─ short_term.py            # 对话窗口 + summary
│  │  ├─ long_term.py             # 可选：向量记忆（偏好）
│  │  └─ write_policy.py          # 白名单写入策略（只写用户确认）
│  │
│  ├─ safety/                     # 隐私与安全
│  │  ├─ pii.py                   # 脱敏/检测
│  │  ├─ permissions.py           # 操作权限（预留）
│  │  └─ redteam_cases.md         # 对抗样例（后续评估用）
│  │
│  ├─ observability/              # 日志/追踪/指标
│  │  ├─ tracing.py               # trace_id、span
│  │  ├─ logger.py                # 结构化日志（json）
│  │  ├─ metrics.py               # latency、tool_success_rate
│  │  └─ replay.py                # 依据 trace_id 回放（后续可做）
│  │
│  └─ utils/
│     ├─ errors.py
│     ├─ time.py
│     └─ text.py
│
├─ docs/                          # 你的知识库原料（用于RAG）
│  ├─ product_manuals/
│  ├─ faq/
│  ├─ pricing_notes/              # 非代码规则说明（便于维护）
│  └─ examples/                   # 示例对话/报价样例
│
├─ eval/                          # 评测（先基础版）
│  ├─ datasets/
│  │  ├─ quote_cases.jsonl        # 各类尺寸/场景/边界case
│  │  └─ adversarial.jsonl
│  ├─ run_eval.py
│  └─ metrics.py
│
├─ scripts/
│  ├─ dev_server.sh
│  ├─ build_index.sh
│  └─ seed_catalog.sh
│
└─ tests/                         # 集成测试（API/Graph）
   ├─ test_quote_flow.py
   ├─ test_tool_validation.py
   └─ test_pii_redaction.py
```


---

## 5. 每个部分的作用（逐文件说明）

> 下面按“目录 → 文件”逐个说明职责，确保不遗漏。

### 5.1 根目录文件

- `README.md`
  - 项目简介、启动方式、API 示例、架构图链接、规则版本策略。
- `.gitignore`
  - 忽略 `.env`、`__pycache__`、`data/vectorstore`、日志等。
- `.env.example`
  - 示例环境变量：MODEL_URL、REDIS_URL、VECTORSTORE_PATH、LOG_LEVEL 等。
- `pyproject.toml`
  - Python 依赖与打包配置（FastAPI、LangGraph、Pydantic、FAISS/Chroma、httpx 等）。
- `docker-compose.yml`
  - 本地一键启动：api、redis（可选）、vectorstore（可选）、vllm（可选）。
- `Makefile`
  - `make dev` / `make test` / `make lint` / `make build-index`

---

### 5.2 apps/api（对外服务层）

- `apps/api/Dockerfile`
  - 构建 API 镜像，安装依赖并启动 uvicorn。
- `apps/api/main.py`
  - FastAPI app 初始化，挂载路由，注册 middleware。
- `apps/api/deps.py`
  - 依赖注入：LLM client、vectorstore、catalog repo、redis session store、logger。
- `apps/api/config.py`
  - Pydantic Settings：读取 env，配置模型地址、索引路径、限流参数等。
- `apps/api/routers/chat.py`
  - `/chat`：面向多轮对话，维护 session_id 与 AgentState。
- `apps/api/routers/quote.py`
  - `/quote`：一步到位报价（适合表单已齐全的调用方）。
- `apps/api/routers/health.py`
  - `/health`、`/ready`：健康检查（模型可达性、向量库加载等）。
- `apps/api/routers/admin.py`（可选）
  - 内部接口：刷新索引、切换规则版本、查看工具统计。
- `apps/api/schemas/chat.py`
  - `ChatRequest/ChatResponse`：对外请求响应结构。
- `apps/api/schemas/quote.py`
  - `QuoteRequest/QuoteResponse`：报价结果结构（含 breakdown）。
- `apps/api/schemas/tool_io.py`
  - 工具调用的公共 schema（ToolCall、ToolResult）。
- `apps/api/schemas/errors.py`
  - 统一错误码：VALIDATION_ERROR、TOOL_TIMEOUT、RAG_EMPTY 等。
- `apps/api/middleware/tracing.py`
  - 生成/传递 trace_id，写入 response header。
- `apps/api/middleware/rate_limit.py`（可选）
  - 简单限流：按 ip/session/user；防止滥用。
- `apps/api/middleware/pii_redaction.py`
  - 在日志写出前做脱敏（手机号、地址、邮箱等）。

---

### 5.3 apps/worker（离线任务，可选）

- `apps/worker/Dockerfile`
  - worker 镜像（可与 api 共用基础镜像）。
- `apps/worker/jobs/build_index.py`
  - 从 `docs/` 扫描文件 → chunk → embed → 写入向量库。
- `apps/worker/jobs/refresh_catalog.py`
  - 同步最新商品/规则配置（从 CSV/ERP/CRM/DB）到 `catalog/data` 或 DB。

---

### 5.4 packages/agent（LangGraph 工作流）

- `packages/agent/state.py`
  - 定义 `AgentState`：
    - messages（对话）
    - requirements（尺寸/地点/噪音/风压）
    - selection（型材/玻璃/五金）
    - price_result（定价结果）
    - missing_fields（缺失字段列表）
    - trace_id/session_id
- `packages/agent/graph.py`
  - 构建 LangGraph：
    - router → collect_requirements → validate_inputs → recommend → price_quote → generate_quote → finalize
    - 任一失败 → fallback
- `packages/agent/nodes/router.py`
  - 判断用户意图：咨询解释 vs 进入报价流程；更新 state.step。
- `packages/agent/nodes/collect_requirements.py`
  - 追问并解析用户输入（尺寸、地点、噪音描述等）。
- `packages/agent/nodes/recommend.py`
  - 调用 RAG + catalog，给出系列/玻璃/五金建议与依据。
- `packages/agent/nodes/validate_inputs.py`
  - 强校验：缺字段、非法尺寸、单位解析失败 → 填 missing_fields。
- `packages/agent/nodes/price_quote.py`
  - 组装工具输入（series_id、width/height、opening_count 等），调用定价工具。
- `packages/agent/nodes/generate_quote.py`
  - 生成结构化报价单（Markdown + JSON breakdown）。
- `packages/agent/nodes/fallback.py`
  - 工具失败/无检索：降级回答（区间、人工确认、补充信息）。
- `packages/agent/nodes/finalize.py`
  - 输出包装：附 trace_id，清理敏感信息，统一返回格式。
- `packages/agent/prompts/system.md`
  - 系统指令：外部内容不可信、禁止编造数值、只用工具算价。
- `packages/agent/prompts/router.md`
  - 路由 prompt：输出结构化决策（tool_needed / flow_type）。
- `packages/agent/prompts/planner.md`
  - 如采用 plan-and-execute：产出结构化计划。
- `packages/agent/prompts/quote_writer.md`
  - 报价单写作模板（固定字段：产品、规格、数量、单价、总价、备注）。
- `packages/agent/policies/tool_permissions.py`
  - 工具权限策略：读/写/支付（预留）。
- `packages/agent/policies/safety_rules.md`
  - 安全策略与拒答：注入防护、PII 处理原则。

---

### 5.5 packages/tools（工具层：数值正确性）

- `packages/tools/base.py`
  - Tool 抽象与统一返回 `ToolResult(ok, data, error, meta)`。
- `packages/tools/registry.py`
  - 工具注册表：name → Tool instance；供 agent 调用。
- `packages/tools/validators.py`
  - schema 校验与（可选）auto-repair；参数修正策略。
- `packages/tools/pricing/schemas.py`
  - `PriceInput/PriceOutput`（Pydantic），保证输入输出严格。
- `packages/tools/pricing/pricing_rules.py`
  - 定价规则：最小计价面积、损耗、转角立柱、五金计数策略等。
- `packages/tools/pricing/calculate_price.py`
  - 核心工具：根据输入与规则计算 breakdown。
- `packages/tools/pricing/tests/*`
  - 单元测试：边界规则正确性（最小面积、转角、特殊开扇）。
- `packages/tools/http/get.py`
  - 通用只读 API 调用（未来接 CRM 查询、地区风压数据等）。
- `packages/tools/http/post.py`
  - 写操作 API（预留：下单/提交线索），必须权限控制。
- `packages/tools/utils/unit_parse.py`
  - “1米多/1200mm/1.2m/120厘米” 解析与归一（m）。
- `packages/tools/utils/currency.py`
  - 金额格式化、四舍五入、币种处理（CNY）。

---

### 5.6 packages/rag（推荐依据检索）

- `packages/rag/embeddings.py`
  - embedding client（本地或外部），与模型服务解耦。
- `packages/rag/vectorstore.py`
  - 向量库适配（FAISS/Chroma/pgvector）。
- `packages/rag/retriever.py`
  - query 构造、top-k 检索、返回片段与来源。
- `packages/rag/rerank.py`（可选）
  - 重排（cross-encoder 或简单规则）。
- `packages/rag/prompt_injection.py`
  - 文档指令剥离/过滤：只作为“引用”，不允许改变系统行为。
- `packages/rag/indexing/chunking.py`
  - 切分策略：按标题/段落/窗口，保留 source 元信息。
- `packages/rag/indexing/sources.py`
  - 数据源加载：`docs/` 下不同类型文档（产品手册/FAQ/规则）。
- `packages/rag/indexing/build.py`
  - 构建索引流程：load → chunk → embed → upsert。

---

### 5.7 packages/catalog（结构化商品事实）

- `packages/catalog/models.py`
  - Pydantic 模型：Series/Glass/Hardware（含 id、参数范围、适用场景）。
- `packages/catalog/repository.py`
  - 读取 JSON 或 DB；提供查询接口（by_id、filter_by_scene）。
- `packages/catalog/data/*.json`
  - 初期落地的 SKU 数据（后期可替换为 DB）。

---

### 5.8 packages/llm（模型访问层）

- `packages/llm/client.py`
  - LLM 调用统一接口（OpenAI-compatible/vLLM），支持 function calling。
- `packages/llm/models.py`
  - 模型配置：base 模型、lora 模型、temperature、max_tokens。
- `packages/llm/formatting.py`
  - JSON 输出约束、修复（轻量）：用于 router/planner 的结构化输出。

---

### 5.9 packages/memory（记忆）

- `packages/memory/short_term.py`
  - 对话窗口、summary 压缩策略（避免 token 爆）。
- `packages/memory/long_term.py`（可选）
  - 用户偏好向量记忆（仅保存用户确认偏好，不存尺寸/价格）。
- `packages/memory/write_policy.py`
  - 白名单写入策略：明确哪些字段允许入长期记忆。

---

### 5.10 packages/safety（隐私与权限）

- `packages/safety/pii.py`
  - PII 检测与脱敏（手机号、地址、邮箱），供 middleware 与 agent 使用。
- `packages/safety/permissions.py`
  - 操作权限控制（预留：下单、写 CRM、支付）。
- `packages/safety/redteam_cases.md`
  - 对抗用例：注入、越权、诱导泄露、虚假报价等。

---

### 5.11 packages/observability（可观测与回放）

- `packages/observability/tracing.py`
  - trace_id、span、上下文传播（API → graph → tool）。
- `packages/observability/logger.py`
  - 结构化日志（JSON），统一字段（trace_id、session_id、node、tool、latency）。
- `packages/observability/metrics.py`
  - 指标：P95 latency、tool_success_rate、rag_empty_rate。
- `packages/observability/replay.py`
  - 按 trace_id 重放：输出当时的 plan、tool call、结果（不含 PII）。

---

### 5.12 packages/utils（通用工具）

- `packages/utils/errors.py`
  - 自定义异常：ValidationError、ToolError、RAGEmpty 等。
- `packages/utils/time.py`
  - 时间戳、耗时测量、时区处理。
- `packages/utils/text.py`
  - 文本清洗、normalize、截断。

---

### 5.13 docs（知识库原料）

- `docs/product_manuals/`
  - 型材/玻璃/工艺手册文档（用于检索）。
- `docs/faq/`
  - 常见问题（断桥铝、65/70 系列等）。
- `docs/pricing_notes/`
  - 非代码规则说明（便于业务人员 review）。
- `docs/examples/`
  - 示例对话、报价样本（用于 eval）。

---

### 5.14 eval（评测）

- `eval/datasets/quote_cases.jsonl`
  - 各类典型 & 边界报价案例（尺寸、开扇、转角等）。
- `eval/datasets/adversarial.jsonl`
  - 对抗：注入、诱导算价、缺字段跳步等。
- `eval/run_eval.py`
  - 批量跑 graph，统计成功率与错误类型。
- `eval/metrics.py`
  - 计算指标：成功率、格式正确率、工具失败率、平均延迟。

---

### 5.15 scripts（脚本）

- `scripts/dev_server.sh`
  - 本地启动（加载 env、uvicorn、热重载）。
- `scripts/build_index.sh`
  - 调 worker 或直接运行 indexing build。
- `scripts/seed_catalog.sh`
  - 初始化 catalog 数据（拷贝默认 JSON 或导入 DB）。

---

### 5.16 tests（集成测试）

- `tests/test_quote_flow.py`
  - 端到端：需求采集 → 推荐 → 报价 → 输出结构。
- `tests/test_tool_validation.py`
  - 工具输入校验：非法尺寸/单位/枚举处理。
- `tests/test_pii_redaction.py`
  - PII 不可出现在日志/输出中。

---

## 6. 运行时关键路径（LangGraph 工作流）

### 6.1 标准报价流程（推荐）
1. **router**：判断咨询/报价（进入 flow_type=quote）
2. **collect_requirements**：
   - 提取/追问：房型、位置、噪音、尺寸（宽高）、开扇
   - 尺寸可来自自然语言，通过 `unit_parse`
3. **validate_inputs**：
   - 缺字段 → `missing_fields` → 交还 collect_requirements 继续问
   - 非法值 → 明确指出并要求纠正
4. **recommend**：
   - RAG 检索推荐依据
   - 结合 catalog 给出 series/glass/hardware 建议
5. **price_quote**：
   - 用 selection + requirements 调用 `calculate_price`
   - 返回 breakdown（面积、五金、玻璃、加工、运输等）
6. **generate_quote**：
   - 输出 Markdown 报价单 + JSON（机器可读）
7. **finalize**：
   - 附 trace_id、规则版本
   - 移除 PII / 脱敏

### 6.2 失败路径（fallback）
- tool timeout / exception → fallback：建议人工确认 or 区间报价（可选）
- rag empty → fallback：使用 catalog 最基础推荐 + 让用户补充信息

---

## 7. 部署建议（MVP 与上线）

### 7.1 MVP（单机）
- API + 本地向量索引 + 本地 catalog JSON
- session_state 存内存

### 7.2 上线（推荐）
- API（多副本） + Redis（session_state） + vLLM（模型） + 向量库（外部）
- observability 接入：Prometheus + Loki/ELK（可选）

---

## 8. 环境变量（.env.example 推荐字段）

- `APP_ENV=dev|prod`
- `API_HOST=0.0.0.0`
- `API_PORT=8000`
- `MODEL_BASE_URL=http://vllm:8000/v1`
- `MODEL_NAME=deepseek-r1-lora`
- `EMBEDDING_PROVIDER=local|openai|xxx`
- `VECTORSTORE_BACKEND=faiss|chroma|pgvector`
- `VECTORSTORE_PATH=./data/vectorstore`
- `REDIS_URL=redis://redis:6379/0`
- `LOG_LEVEL=INFO`

---

## 9. 输出格式（报价单建议标准）

### 9.1 机器可读（JSON）
- quote_id
- rule_version
- items[]
- subtotal
- tax
- shipping
- total
- assumptions[]
- trace_id

### 9.2 人可读（Markdown）
- 标题：报价单
- 表格：规格、尺寸、数量、单价、总价
- 备注：适用场景、注意事项、有效期

---

## 10. 扩展点（未来可加）

- 多窗型（推拉/平开/内倒）与开扇策略工具化
- 地理位置 → 风压/噪音等级：接外部 API 工具
- 线索转化：CRM 写入工具（必须权限 + 二次确认）
- 价格版本管理：rules version + AB test

---

> 该文档覆盖：  
> ✅ 文件与文件夹结构（完整）  
> ✅ 每个部分作用（逐文件说明）  
> ✅ 状态存储位置（MVP/上线）  
> ✅ 服务之间连接方式（在线/离线链路）
