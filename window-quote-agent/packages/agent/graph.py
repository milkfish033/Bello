"""LangGraph 工作流：intent → router(planner) → 闲聊/产品推荐/产品咨询/价格咨询 四条分支。"""
from typing import Any, Callable

from langgraph.graph import END, START, StateGraph

from packages.agent.state import AgentState
from packages.agent.nodes.chat_node import create_chat_node
from packages.agent.nodes.collect_recommend_params import create_collect_recommend_params_node
from packages.agent.nodes.collect_requirements import create_collect_requirements_node
from packages.agent.nodes.check_node import create_check_node
from packages.agent.nodes.generate_quote import generate_quote
from packages.agent.nodes.intent_node import create_intent_node
from packages.agent.nodes.price_quote import create_price_quote_node
from packages.agent.nodes.recommend import create_recommend_node
from packages.agent.nodes.router import create_router_planner_node
from packages.agent.tools import create_rag_tool

# router 只做 planner：输出下一节点；是否 END 由 check 节点决定
ROUTER_NEXT_NODES = (
    "chat",
    "collect_recommend_params",
    "collect_requirements",
    "recommend",
    "price_quote",
    "generate_quote",
)


def _route_after_check(state: AgentState) -> str:
    """check 之后：若 should_end 则 END，否则交给 router（planner）决定下一步。"""
    if state.get("should_end"):
        return "END"
    return "router"


def _route_after_router(state: AgentState) -> str:
    """router 之后：按 planner 输出的 next_node 分支；若无则按 last_step 与 intent 做 fallback。"""
    next_node = (state.get("next_node") or "").strip()
    if next_node in ROUTER_NEXT_NODES:
        return next_node
    last_step = state.get("step") or ""
    intent = state.get("current_intent") or "其他"
    if last_step == "price_quote":
        return "generate_quote"
    if last_step == "recommend" and intent == "价格咨询":
        return "price_quote"
    if last_step == "recommend":
        return "chat"  # fallback 不结束，由 check 决定
    if last_step == "collect_requirements":
        return "recommend"
    if last_step == "collect_recommend_params" and state.get("recommend_params_ready"):
        return "recommend"
    if last_step == "collect_recommend_params":
        return "chat"  # fallback
    if last_step in ("chat", "intent", "router", "check", ""):
        if intent in ("其他", "公司介绍", "产品咨询"):
            return "chat"
        if intent == "产品推荐":
            return "collect_recommend_params"
        if intent == "价格咨询":
            return "collect_requirements"
    return "chat"


def build_quote_graph(
    retrieve: Callable[[str], list[str]],
    list_series: Callable[[], list[dict[str, Any]]],
    calculate_price: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]],
    *,
    chat_completion: Callable[..., str] | None = None,
    chat_completions: dict[str, Callable[..., str]] | None = None,
    run_intent_pipeline: Callable[[str], Any] | None = None,
    stale_threshold: int = 3,
    router_llm: Any = None,
):
    """
    构建工作流图：intent（pipeline + intent_check）→ router(planner) → 四条分支。
    - router 接受 intent_node 输出，使用 GPT-4o 作为 planner，根据当前意图和用户信息决定是否拆分任务并分配 next_node。
    - 其他/公司介绍：闲聊；产品推荐：问参再 RAG；产品咨询：RAG；价格咨询：采集需求 → 推荐 → 报价 → 生成报价单。

    模型注入：
    - router_llm：可选，传给 router 的 LangChain ChatOpenAI 实例；未传时在节点内用 OPENAI_API_KEY 创建 gpt-4o。
    - chat_completions / chat_completion：同上，用于 chat/collect_recommend_params/collect_requirements/recommend。
    """
    from packages.intent.pipeline import run_intent_pipeline as _run_intent_pipeline

    intent_fn = run_intent_pipeline or _run_intent_pipeline

    def _chat(node_name: str) -> Callable[..., str]:
        if chat_completions and node_name in chat_completions:
            return chat_completions[node_name]
        if chat_completion is not None:
            return chat_completion
        from packages.llm.model_config import get_chat_completion_for_node
        return get_chat_completion_for_node(node_name)

    builder = StateGraph(AgentState)

    rag_tool = create_rag_tool(retrieve)
    chat_tools = [rag_tool] if router_llm is not None else None
    builder.add_node("intent", create_intent_node(intent_fn, stale_threshold=stale_threshold))
    builder.add_node("router", create_router_planner_node(llm=router_llm))
    builder.add_node("check", create_check_node(llm=router_llm))
    builder.add_node(
        "chat",
        create_chat_node(_chat("chat"), tools=chat_tools, llm=router_llm),
    )
    builder.add_node("collect_recommend_params", create_collect_recommend_params_node(_chat("collect_recommend_params")))
    builder.add_node("collect_requirements", create_collect_requirements_node(_chat("collect_requirements")))
    builder.add_node("recommend", create_recommend_node(retrieve, list_series, _chat("recommend")))
    builder.add_node("price_quote", create_price_quote_node(calculate_price))
    builder.add_node("generate_quote", generate_quote)

    builder.add_edge(START, "intent")
    builder.add_edge("intent", "router")
    builder.add_conditional_edges(
        "router",
        _route_after_router,
        {
            "chat": "chat",
            "collect_recommend_params": "collect_recommend_params",
            "collect_requirements": "collect_requirements",
            "recommend": "recommend",
            "price_quote": "price_quote",
            "generate_quote": "generate_quote",
        },
    )
    # 除 intent 外所有节点都回到 check；check 决定是否 END，不 END 则交给 router（planner）决定下一步
    builder.add_edge("chat", "check")
    builder.add_edge("collect_recommend_params", "check")
    builder.add_edge("collect_requirements", "check")
    builder.add_edge("recommend", "check")
    builder.add_edge("price_quote", "check")
    builder.add_edge("generate_quote", "check")
    builder.add_conditional_edges(
        "check",
        _route_after_check,
        {"router": "router", "END": END},
    )

    return builder.compile()


def get_graph_topology(builder_or_compiled) -> dict[str, Any]:
    """返回图的拓扑信息，用于验证与调试。兼容 CompiledStateGraph.get_graph() 返回的图。"""
    try:
        g = builder_or_compiled.get_graph() if hasattr(builder_or_compiled, "get_graph") else builder_or_compiled
    except Exception:
        g = builder_or_compiled
    if hasattr(g, "nodes") and callable(getattr(g, "nodes")):
        nodes = list(g.nodes())
    else:
        nodes = list(g.nodes) if hasattr(g, "nodes") else []
    if hasattr(g, "edges") and callable(getattr(g, "edges")):
        edges = list(g.edges())
    else:
        edges = list(g.edges) if hasattr(g, "edges") else []
    return {"nodes": nodes, "edges": edges}


