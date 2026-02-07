"""Task 4.7：LangGraph 图拓扑验证。"""
import pytest

from packages.agent.graph import build_quote_graph, get_graph_topology


def _mock_chat(_messages):
    return ""


def _mock_retrieve(_query):
    return []


def _mock_list_series():
    return [{"id": "65", "name": "65系列"}]


def _mock_calculate_price(_req, _sel):
    return {"total": 0, "breakdown": [], "series_id": ""}


def test_build_quote_graph_compiles():
    graph = build_quote_graph(
        chat_completion=_mock_chat,
        retrieve=_mock_retrieve,
        list_series=_mock_list_series,
        calculate_price=_mock_calculate_price,
    )
    assert graph is not None
    assert hasattr(graph, "invoke") or hasattr(graph, "stream")


def test_graph_topology_contains_expected_nodes():
    graph = build_quote_graph(
        chat_completion=_mock_chat,
        retrieve=_mock_retrieve,
        list_series=_mock_list_series,
        calculate_price=_mock_calculate_price,
    )
    topo = get_graph_topology(graph)
    nodes = topo.get("nodes", [])
    expected = {
        "intent",
        "router",
        "check",
        "chat",
        "collect_recommend_params",
        "collect_requirements",
        "recommend",
        "price_quote",
        "generate_quote",
    }
    assert expected.issubset(set(nodes)), f"Expected nodes {expected}, got {nodes}"


def test_graph_invoke_quote_flow():
    """端到端：current_intent=价格咨询 时走完报价链路，state 含 quote_md。"""
    def mock_chat(messages):
        content = (messages or [{}])[0].get("content", "") if messages else ""
        if "需求" in content or "提取" in content:
            return '{"w": 3.0, "h": 2.0}'
        if "推荐" in content or "系列" in content:
            return '{"series_id": "65"}'
        return "好的"

    def stub_intent_pipeline(_raw: str):
        return {"primary_intent": "价格咨询", "intents": ["价格咨询"], "cleaned_prompt": ""}

    graph = build_quote_graph(
        chat_completion=mock_chat,
        retrieve=lambda q: ["断桥铝 65 系列适合家用"],
        list_series=lambda: [{"id": "65", "name": "65系列"}],
        calculate_price=lambda r, s: {
            "total": (r.get("w", 0) * r.get("h", 0)) * 500,
            "breakdown": [{"item": "窗面积", "qty": r.get("w", 0) * r.get("h", 0), "unit_price": 500, "amount": (r.get("w", 0) * r.get("h", 0)) * 500}],
            "series_id": s.get("series_id", ""),
        },
        run_intent_pipeline=stub_intent_pipeline,
    )
    initial: dict = {
        "messages": [{"role": "user", "content": "我想装窗户，高2米宽3米"}],
    }
    result = graph.invoke(initial)
    assert "quote_md" in result
    assert "总价" in result["quote_md"]
    assert "明细表格" in result["quote_md"]
