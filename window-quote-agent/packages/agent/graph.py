"""LangGraph 工作流：intent → router → 闲聊/产品推荐/产品咨询/价格咨询 四条分支。"""
from typing import Any, Callable

from langgraph.graph import END, START, StateGraph

from packages.agent.state import AgentState
from packages.agent.nodes.chat_node import create_chat_node
from packages.agent.nodes.collect_recommend_params import create_collect_recommend_params_node
from packages.agent.nodes.collect_requirements import create_collect_requirements_node
from packages.agent.nodes.generate_quote import generate_quote
from packages.agent.nodes.intent_node import create_intent_node
from packages.agent.nodes.price_quote import create_price_quote_node
from packages.agent.nodes.rag_query_node import create_rag_query_node
from packages.agent.nodes.recommend import create_recommend_node
from packages.agent.nodes.router import router_by_current_intent


def _route_after_router(state: AgentState) -> str:
    """router 之后：按 current_intent 分支。其他/公司介绍→闲聊；产品推荐→问参再RAG；产品咨询→RAG；价格咨询→报价。"""
    intent = state.get("current_intent") or "其他"
    if intent in ("其他", "公司介绍"):
        return "chat"
    if intent == "产品推荐":
        return "collect_recommend_params"
    if intent == "产品咨询":
        return "rag_query"
    if intent == "价格咨询":
        return "collect_requirements"
    return "chat"


def _route_after_collect_recommend_params(state: AgentState) -> str:
    """collect_recommend_params 之后：若已收集到至少一项参数则 recommend，否则 END（已追加「请提供…」消息）。"""
    if state.get("recommend_params_ready"):
        return "recommend"
    return "END"


def _route_after_recommend(state: AgentState) -> str:
    """recommend 之后：仅当 current_intent 为价格咨询时走 price_quote；产品推荐只做 RAG 推荐后结束。"""
    if state.get("current_intent") == "价格咨询":
        return "price_quote"
    return "END"


def build_quote_graph(
    chat_completion: Callable[..., str],
    retrieve: Callable[[str], list[str]],
    list_series: Callable[[], list[dict[str, Any]]],
    calculate_price: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]],
    *,
    run_intent_pipeline: Callable[[str], Any] | None = None,
    stale_threshold: int = 3,
):
    """
    构建工作流图：intent（pipeline + intent_check）→ router → 四条分支。
    - 其他/公司介绍：闲聊，直接模型输出。
    - 产品推荐：先询问参数/使用场景/特殊需求/价格预算，再 RAG 推荐。
    - 产品咨询：直接 RAG 查询后模型回答。
    - 价格咨询：采集需求 → 推荐 → 报价 → 生成报价单。
    依赖由调用方注入；run_intent_pipeline 默认 packages.intent.pipeline.run_intent_pipeline。
    """
    from packages.intent.pipeline import run_intent_pipeline as _run_intent_pipeline

    intent_fn = run_intent_pipeline or _run_intent_pipeline

    builder = StateGraph(AgentState)

    builder.add_node("intent", create_intent_node(intent_fn, stale_threshold=stale_threshold))
    builder.add_node("router", router_by_current_intent)
    builder.add_node("chat", create_chat_node(chat_completion))
    builder.add_node("collect_recommend_params", create_collect_recommend_params_node(chat_completion))
    builder.add_node("rag_query", create_rag_query_node(retrieve, chat_completion))
    builder.add_node("collect_requirements", create_collect_requirements_node(chat_completion))
    builder.add_node("recommend", create_recommend_node(retrieve, list_series, chat_completion))
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
            "rag_query": "rag_query",
            "collect_requirements": "collect_requirements",
        },
    )
    builder.add_edge("chat", END)
    builder.add_conditional_edges(
        "collect_recommend_params",
        _route_after_collect_recommend_params,
        {"recommend": "recommend", "END": END},
    )
    builder.add_edge("rag_query", END)
    builder.add_edge("collect_requirements", "recommend")
    builder.add_conditional_edges(
        "recommend",
        _route_after_recommend,
        {"price_quote": "price_quote", "END": END},
    )
    builder.add_edge("price_quote", "generate_quote")
    builder.add_edge("generate_quote", END)

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


