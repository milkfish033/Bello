"""Agent 状态定义：LangGraph 工作流共享状态。"""
from typing import Any, TypedDict

# 单意图集合（与 intent.schemas.INTENTS 一致，暂不考虑多意图）
CURRENT_INTENTS = ("产品咨询", "产品推荐", "价格咨询", "公司介绍", "其他")


class AgentState(TypedDict, total=False):
    """LangGraph 图内共享状态。"""

    messages: list[dict[str, Any]]
    requirements: dict[str, Any]
    selection: dict[str, Any]
    price_result: dict[str, Any]
    quote_md: str  # 生成的报价单 Markdown，由 generate_quote 写入
    rag_context: list[str]  # 推荐依据片段，由 recommend 写入
    step: str
    intent: str  # 兼容旧路由 "chat" | "quote"，新流程用 current_intent
    current_intent: str  # 当前意图：产品咨询 | 产品推荐 | 价格咨询 | 公司介绍 | 其他
    turns_with_same_intent: int  # 连续相同意图的轮数，用于「长时间不变」软校验
    missing_fields: list[str]
    trace_id: str
    session_id: str
    # 产品推荐分支：先询问 参数、使用场景、特殊需求、价格预算
    recommend_params: dict[str, Any]  # 使用场景、特殊需求、价格预算、参数 等
    recommend_params_ready: bool  # 是否已收集到至少一项，用于路由到 recommend
