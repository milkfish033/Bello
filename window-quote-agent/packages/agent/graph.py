"""LangGraph 工作流：将 router / collect_requirements / recommend / price_quote / generate_quote 连接成图。"""
from typing import Any, Callable

from langgraph.graph import END, START, StateGraph

from packages.agent.state import AgentState
from packages.agent.nodes.collect_requirements import create_collect_requirements_node
from packages.agent.nodes.generate_quote import generate_quote
from packages.agent.nodes.price_quote import create_price_quote_node
from packages.agent.nodes.recommend import create_recommend_node
from packages.agent.nodes.router import create_router_node


def _route_after_router(state: AgentState) -> str:
    """router 之后：根据 intent 进入报价流程或结束。返回下一节点名或 "END"。"""
    intent = state.get("intent") or "quote"
    if intent == "quote":
        return "collect_requirements"
    return "END"


def build_quote_graph(
    chat_completion: Callable[..., str],
    retrieve: Callable[[str], list[str]],
    list_series: Callable[[], list[dict[str, Any]]],
    calculate_price: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]],
    *,
    intent_classifier: Callable[[str], str] | None = None,
):
    """
    构建报价工作流图。依赖由调用方注入：
    - chat_completion(messages) -> str
    - retrieve(query) -> list[str]
    - list_series() -> list[{"id", "name"}, ...]
    - calculate_price(requirements, selection) -> price_result
    - intent_classifier(user_message) -> "chat"|"quote"（可选）：若提供则用外部小模型做意图分类，否则用 chat_completion
    """
    builder = StateGraph(AgentState)

    builder.add_node(
        "router",
        create_router_node(chat_completion=chat_completion, intent_classifier=intent_classifier),
    )
    builder.add_node("collect_requirements", create_collect_requirements_node(chat_completion))
    builder.add_node("recommend", create_recommend_node(retrieve, list_series, chat_completion))
    builder.add_node("price_quote", create_price_quote_node(calculate_price))
    builder.add_node("generate_quote", generate_quote)

    builder.add_edge(START, "router")
    builder.add_conditional_edges(
        "router",
        _route_after_router,
        {"collect_requirements": "collect_requirements", "END": END},
    )
    builder.add_edge("collect_requirements", "recommend")
    builder.add_edge("recommend", "price_quote")
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
