# Intent 与 Router 联合 + Chat History 设计

## 1. 联合方式：Router 先读 Intent 的输出

目标：让 router 的「chat / quote」二分类**基于** intent 模块的多意图结果，而不是单独再调 LLM 或另一套分类器。

### 1.1 数据流

```
用户消息（当前句，或当前句 + 历史）
    → Intent Pipeline（run_intent_pipeline）
    → IntentPipelineOutput（primary_intent, intents, tasks, ...）
    → 映射层：primary_intent / intents → "chat" | "quote"
    → Router 使用该结果作为 state.intent，不再调 chat_completion 做意图
```

### 1.2 映射规则（业务约定）

| Intent 多意图（primary） | Router 路由 |
|-------------------------|-------------|
| 价格咨询、产品推荐      | quote（走报价流程） |
| 产品咨询、公司介绍、其他 | chat（不报价，可走闲聊/知识问答） |

多意图时：若命中「价格咨询」或「产品推荐」任一项，可定为 quote；否则 chat。具体规则可按产品再细调。

### 1.3 是否「必须先存 Chat History」？

**不必然。** 分两种用法：

- **只根据当前句判意图**  
  - Router 当前就是用 `state["messages"]` 里**最后一条用户消息**做意图。  
  - 联合 intent 时：对「最后一条用户消息」跑 `run_intent_pipeline`，再把结果映射成 chat/quote，作为 `intent_classifier` 的返回值即可。  
  - 此时 **不需要** 额外的「user chat history 存储」：只要调用方 invoke 时把本轮的 `messages` 传进来（可以只含当前一条，也可以含历史），router 照旧只取最后一条给 intent。历史是否持久化，取决于你是否要做多轮对话（见下）。

- **希望 Intent 利用多轮上下文**（例如「再报一个」「换成 3x2」）  
  - 这时需要给 intent 的输入不仅是当前句，而是「当前句 + 最近几轮」。  
  - 消息来源只能是：**(a)** 调用方在请求里带上完整/近期 `messages`（历史在客户端或网关），**(b)** 或服务端按 `session_id` 从存储里取出历史再拼进 `state["messages"]`。  
  - 这时就需要**服务端存 user chat history**（见第 2 节）。

结论：**联合 intent 与 router 本身不强制要求先做 chat history 存储**；只有当你希望「多轮上下文参与意图判断」或「多轮对话状态可恢复」时，才需要实现 history 存储。

---

## 2. Chat History 如何实现

当需要「服务端记住会话、多轮可恢复」时，需要持久化每轮的 `messages`（或至少 user/assistant 的对话内容）。下面给出接口与几种实现方式。

### 2.1 抽象接口：SessionStore

职责：按会话 ID 读写「当前会话的消息列表」，供 API 在 invoke 前加载、invoke 后回写。

```python
# packages/memory/session_store.py（或 apps/api/session_store.py）

from typing import Any, Protocol

class SessionStore(Protocol):
    """会话消息存储抽象。"""

    def get_messages(self, session_id: str) -> list[dict[str, Any]]:
        """返回该会话当前消息列表，无则返回 []。"""
        ...

    def append_message(self, session_id: str, role: str, content: str) -> None:
        """追加一条消息并持久化。"""
        ...

    def set_messages(self, session_id: str, messages: list[dict[str, Any]]) -> None:
        """整体覆盖该会话消息（例如 invoke 后把完整 state["messages"] 写回）。"""
        ...
```

- 若只做「按 session 存整份 messages」：实现 `get_messages` + `set_messages` 即可。  
- 若希望「每次只追加一条」、减少读整份再写回：可加上 `append_message`，由 API 在收到新 user message 时 append，invoke 前 `get_messages` 得到完整列表塞进 `state["messages"]`。

### 2.2 实现方式一：内存（单机、开发/测试）

```python
from typing import Any

class InMemorySessionStore:
    def __init__(self, max_sessions: int = 10_000):
        self._store: dict[str, list[dict[str, Any]]] = {}
        self._max = max_sessions

    def get_messages(self, session_id: str) -> list[dict[str, Any]]:
        return list(self._store.get(session_id, []))

    def append_message(self, session_id: str, role: str, content: str) -> None:
        if session_id not in self._store:
            self._store[session_id] = []
        self._store[session_id].append({"role": role, "content": content})

    def set_messages(self, session_id: str, messages: list[dict[str, Any]]) -> None:
        if len(self._store) >= self._max and session_id not in self._store:
            # 简单淘汰：可改为 LRU
            self._store.pop(next(iter(self._store)))
        self._store[session_id] = list(messages)
```

- 优点：无依赖、实现快。  
- 缺点：重启丢失、多实例不共享；仅适合开发或单机。

### 2.3 实现方式二：Redis

- Key：`session:{session_id}`，Value：JSON 序列化的 `list[dict]`，或使用 Redis List 逐条 RPUSH。  
- 可选 TTL：`EXPIRE session:{session_id} 3600`（例如 1 小时无新消息则过期）。  
- 接口同上：`get_messages` 反序列化；`set_messages` / `append_message` 序列化后 SET 或 RPUSH。

### 2.4 实现方式三：数据库（PostgreSQL / MySQL）

- 表：`session_messages(session_id, seq, role, content, created_at)`。  
- `get_messages`：按 `session_id` 按 `seq` 排序 SELECT，拼成 `[{"role","content"}, ...]`。  
- `append_message`：INSERT 新行。  
- 若不需要逐条而只存整份 JSON：可单表 `sessions(session_id, messages_json, updated_at)`，则与内存版类似，只是读写改为 DB。

### 2.5 与 API / Graph 的衔接

- 请求体示例：`{"session_id": "xxx", "message": "我想报价"}`
- 流程：
  1. 从 SessionStore 用 `session_id` 取 `messages = store.get_messages(session_id)`。
  2. 追加当前用户消息：`messages.append({"role": "user", "content": message})`（或调用 `store.append_message(session_id, "user", message)` 再 `get_messages`）。
  3. 构造 `initial_state = { "messages": messages, "session_id": session_id, ... }`，调用 `graph.invoke(initial_state)`。
  4. 用返回的 `state["messages"]` 回写：`store.set_messages(session_id, state["messages"])`。
- 这样，下一次同一 session 的请求就会带上完整历史；若 intent 或后续节点要「看最近 N 条」，可以从 `state["messages"]` 里取。

### 2.6 可选：LangGraph Checkpoint

若使用 LangGraph 的 checkpoint（如 `MemorySaver` 或 Redis checkpointer），图状态（含 `messages`）会按 `thread_id`（可等价于 `session_id`）持久化，每次 `invoke` 会先恢复再执行。此时：

- 「Chat history」等价于 checkpoint 里的 `state["messages"]`。
- 你仍可**不**单独做 SessionStore，而由 LangGraph 负责状态持久化；但若希望 API 层在 invoke 前/后做额外逻辑（如限流、审计、单独存一份到 DB），仍可再包一层 SessionStore 或与 checkpoint 并存。

---

## 3. 落地顺序建议

1. **先做「Router 读 Intent 输出」**（不依赖 history 存储）  
   - 写一个 `intent_to_route(user_message: str) -> "chat"|"quote"`：内部调 `run_intent_pipeline(user_message)`，按 `primary_intent`（或 `intents`）映射到 chat/quote。  
   - `build_quote_graph(..., intent_classifier=intent_to_route)`，这样 router 就完全基于 intent 模块输出。

2. **再按需加 Chat History**  
   - 若当前只做「单轮」或「历史由前端带」：可暂不实现 SessionStore。  
   - 若要做「服务端多轮、同一 session 连续对话」：实现 SessionStore（先内存或 Redis），再在 API 里按上面 2.5 的流程接好。

3. **若未来要让 Intent 显式用多轮**  
   - 可扩展 `run_intent_pipeline` 为接受 `(current_message, recent_messages)` 或 `full_messages`，在预处理里把最近几轮拼成上下文再规则/模型分类；  
   - 此时 `intent_classifier` 的签名可改为接收 `state` 或 `messages`，在 router 里把 `state["messages"]` 传入。

这样就把「intent 与 router 联合」和「chat history 是否要存、怎么存」拆开，先联合、再按需加存储。
