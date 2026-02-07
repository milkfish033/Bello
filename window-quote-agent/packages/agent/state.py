"""Agent 状态定义：LangGraph 工作流共享状态。"""
from typing import Any, TypedDict

# 单意图集合（与 intent.schemas.INTENTS 一致，暂不考虑多意图）
CURRENT_INTENTS = ("产品咨询", "产品推荐", "价格咨询", "公司介绍", "其他")


def next_step_count(state: "AgentState") -> int:
    """在 state 上执行一步后的 step_count：当前值 + 1。各节点返回时用此函数写入 step_count。"""
    return (state.get("step_count") or 0) + 1


class AgentState(TypedDict, total=False):
    """LangGraph 图内共享状态。"""

    messages: list[dict[str, Any]]
    requirements: dict[str, Any]
    requirements_ready: bool  # 是否已收集到至少一项需求，用于路由到 recommend
    selection: dict[str, Any]
    selection_ready: bool  # 是否有具体产品型号（如 series_id），用于报价前校验，有才可进入 price_quote
    price_result: dict[str, Any]
    quote_md: str  # 生成的报价单 Markdown，由 generate_quote 写入
    rag_context: list[str]  # 推荐依据片段，由 recommend 写入
    step: str
    step_count: int  # 已执行步数，每执行一个节点加一
    max_step: int  # 可选；当 step_count >= max_step 时自动 END
    intent: str  # 兼容旧路由 "chat" | "quote"，新流程用 current_intent
    current_intent: str  # 当前意图：产品咨询 | 产品推荐 | 价格咨询 | 公司介绍 | 其他
    turns_with_same_intent: int  # 连续相同意图的轮数，用于「长时间不变」软校验
    missing_fields: list[str]
    trace_id: str
    session_id: str
    # 产品推荐分支：先询问 参数、使用场景、特殊需求、价格预算
    recommend_params: dict[str, Any]  # 使用场景、特殊需求、价格预算、参数 等
    recommend_params_ready: bool  # 是否已收集到至少一项，用于路由到 recommend
    # Router planner 输出（router 只负责规划下一步节点）
    next_node: str  # 下一节点：chat | collect_recommend_params | collect_requirements | recommend | price_quote | generate_quote
    task_split: bool  # 是否对任务进行了拆分
    plan_tasks: list[dict[str, Any]]  # 拆分后的子任务列表，供下游节点参考
    # Check 节点输出：是否结束本轮（由 check 用 GPT-4o 决定，不结束则交给 router）
    should_end: bool