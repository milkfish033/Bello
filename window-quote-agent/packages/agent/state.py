"""Agent 状态定义：LangGraph 工作流共享状态。"""
from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    """LangGraph 图内共享状态。"""

    messages: list[dict[str, Any]]
    requirements: dict[str, Any]
    selection: dict[str, Any]
    price_result: dict[str, Any]
    quote_md: str  # 生成的报价单 Markdown，由 generate_quote 写入
    rag_context: list[str]  # 推荐依据片段，由 recommend 写入
    step: str
    intent: str  # "chat" | "quote"，由 router 写入
    missing_fields: list[str]
    trace_id: str
    session_id: str
