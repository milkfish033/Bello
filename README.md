
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