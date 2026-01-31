"""Task 4.4：推荐节点测试。"""
import pytest

from packages.agent.nodes.recommend import recommend, create_recommend_node
from packages.agent.state import AgentState


def _mock_retrieve(_query):
    return ["断桥铝 65 系列适合家用，隔音保温较好。"]


def _mock_list_series():
    return [{"id": "65", "name": "65系列"}, {"id": "70", "name": "70系列"}]


def _mock_chat(_messages):
    return '{"series_id": "65"}'


def test_recommend_outputs_selection_and_rag_context():
    state: AgentState = {
        "messages": [{"role": "user", "content": "我要做窗户"}],
        "requirements": {"w": 3.0, "h": 2.0},
    }
    out = recommend(state, _mock_retrieve, _mock_list_series, _mock_chat)
    assert "selection" in out
    assert out["selection"].get("series_id") == "65"
    assert "rag_context" in out
    assert any("65" in c or "断桥铝" in c for c in out["rag_context"])
    assert out["step"] == "recommend"


def test_create_recommend_node():
    node = create_recommend_node(_mock_retrieve, _mock_list_series, _mock_chat)
    state: AgentState = {"requirements": {"w": 2, "h": 1.5}}
    out = node(state)
    assert out["selection"].get("series_id") == "65"
    assert len(out.get("rag_context", [])) >= 0
