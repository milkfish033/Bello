"""
FastAPI Demo：供测试 Agent 的聊天接口。

启动：cd window-quote-agent && uvicorn apps.api.main:app --reload --port 8001

请求示例：
  curl -X POST http://localhost:8001/chat -H "Content-Type: application/json" -d '{"message": "我想装窗户"}'

max_step：通过环境变量 MAX_STEP 设置（整数），超过该步数自动结束；不设则不限制。
"""
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


def _get_max_step() -> int | None:
    """从环境变量 MAX_STEP 读取最大步数，未设置或无效则返回 None（不限制）。"""
    raw = os.environ.get("MAX_STEP", "").strip()
    if not raw:
        return None
    try:
        n = int(raw)
        return n if n > 0 else None
    except ValueError:
        return None


def _build_graph():
    """懒加载图，首次请求时构建。"""
    from packages.agent.graph import build_quote_graph
    from packages.agent.tools import bm25_retrieve
    from packages.llm import get_all_node_chat_completions

    return build_quote_graph(
        retrieve=bm25_retrieve,
        list_series=lambda: [
            {"id": "65", "name": "65系列"},
            {"id": "70", "name": "70系列"},
            {"id": "80", "name": "80系列"},
        ],
        chat_completions=get_all_node_chat_completions(),
    )


_graph: Any = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = _build_graph()
    return _graph


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # shutdown 如有需要可在此清理


app = FastAPI(
    title="Window Quote Agent Demo",
    description="智能报价与选品顾问 Agent 测试接口",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    quote_md: str | None = None
    current_intent: str | None = None


@app.get("/")
def root():
    return {"status": "ok", "docs": "/docs", "chat": "POST /chat"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """发送一条消息，获取 Agent 回复。"""
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="message 不能为空")

    try:
        graph = get_graph()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"图构建失败，请检查依赖与环境变量: {e}",
        ) from e

    initial: dict[str, Any] = {
        "messages": [{"role": "user", "content": request.message.strip()}],
    }
    if (max_step := _get_max_step()) is not None:
        initial["max_step"] = max_step

    try:
        result = graph.invoke(initial)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    messages = result.get("messages") or []
    reply = ""
    for m in reversed(messages):
        if m.get("role") == "assistant" and m.get("content"):
            reply = m.get("content", "")
            break

    return ChatResponse(
        reply=reply,
        quote_md=result.get("quote_md"),
        current_intent=result.get("current_intent"),
    )
# @app.post("/chat")
# def chat(req: ChatRequest):
#     print("1️⃣ start", flush=True)

#     msg = req.message
#     print("2️⃣ message ok", flush=True)

#     # 临时绕过 agent
#     return {"reply": msg}
