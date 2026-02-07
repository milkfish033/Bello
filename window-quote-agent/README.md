# Window Quote Agent

智能报价与选品顾问 Agent。

## 开发环境

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

## 使用 uv 或 poetry

```bash
uv sync
# 或
poetry install
```

## 如何跑起来

1. **安装依赖**（二选一）  
   - 最小：`pip install -e .`（非 GPT 节点需设 `LLM_BACKEND=openai` 并用 OpenAI 兼容接口）  
   - 本地 HF 模型：`pip install -e ".[chat-hf]"`（默认 `LLM_BACKEND=huggingface`，用 `MODEL_ID` 指定模型）  
   - 规则未命中时用零样本意图分类：`pip install -e ".[intent-model]"`

2. **环境变量**（见 `.env.example`）  
   - 非 GPT 节点：`LLM_BACKEND=huggingface`、`MODEL_ID=Milkfish033/deepseek-r1-1.5b-merged`（或 `LLM_BACKEND=openai` + `MODEL_BASE_URL`/`MODEL_NAME`/`API_KEY`）  
   - Router/Check（GPT-4o）：`OPENAI_API_KEY`；未设置时 router/check 会走无 LLM 的 fallback

3. **构建图并调用**（必传 `retrieve` 与 `list_series`）  
   ```python
   from packages.agent.graph import build_quote_graph
   from packages.agent.tools import bm25_retrieve  # 或自定义 retrieve
   from packages.llm import get_all_node_chat_completions

   graph = build_quote_graph(
       retrieve=bm25_retrieve,  # 不传则默认 bm25_retrieve（依赖 packages/rag/brochure 数据）
       list_series=lambda: [{"id": "65", "name": "65系列"}],  # 必传：产品系列列表
       chat_completions=get_all_node_chat_completions(),
   )
   state = graph.invoke({"messages": [{"role": "user", "content": "我想装窗户"}]})
   ```

4. **RAG**：默认使用 `packages/rag/brochure/product_cards_merged.json`；文件存在且已安装 `langchain-community` 时 BM25 检索可用。

### FastAPI Demo 测试

```bash
# 启动（端口 8001，避免与 vLLM 等冲突）
cd window-quote-agent
uvicorn apps.api.main:app --reload --port 8001
# 或
python scripts/run_demo.py
```

- 接口文档：http://localhost:8001/docs  
- 测试：`curl -X POST http://localhost:8001/chat -H "Content-Type: application/json" -d '{"message": "我想装窗户"}'`

## 配置 Chat 模型（接入实际使用的模型）

Agent 各节点通过 OpenAI 兼容接口调用大模型。

### 按 intent/节点 使用不同模型（推荐）

**定义位置**：`packages/llm/model_config.py`  
- **NODE_TO_MODEL_KEY**：节点名 → 模型档位（chat / collect / qa），同一档位共用一组 base_url/model/api_key。  
- **MODEL_KEY_DEFAULTS**：各档位未在环境变量中设置时的默认值。  
- 环境变量：`MODEL_<档位>_BASE_URL`、`MODEL_<档位>_NAME`、`MODEL_<档位>_API_KEY`（如 `MODEL_CHAT_*`、`MODEL_QA_*`、`MODEL_COLLECT_*`），未设置时回退到全局 `MODEL_BASE_URL` / `MODEL_NAME` / `API_KEY`。

构建图时可不传模型，直接按环境变量/档位使用：

```python
from packages.agent.graph import build_quote_graph
from packages.llm import get_all_node_chat_completions

# 从 .env 按档位生成各节点 chat_completion
graph = build_quote_graph(
    retrieve=...,
    list_series=...,
    calculate_price=...,
    chat_completions=get_all_node_chat_completions(),
)
```

### 所有节点共用同一模型

1. **环境变量**：在 `.env` 中设置 `MODEL_BASE_URL`、`MODEL_NAME`、`API_KEY`。  
2. **代码**：`build_quote_graph(..., chat_completion=get_chat_completion(), ...)` 或 `chat_completion=create_chat_completion_from_config(get_settings())`。
