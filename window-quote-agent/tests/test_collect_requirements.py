"""Task 4.3：需求采集节点测试。"""
import pytest

from packages.agent.nodes.collect_requirements import (
    collect_requirements,
    create_collect_requirements_node,
)
from packages.agent.state import AgentState


def _mock_chat_h2w3(_messages):
    return '{"w": 3.0, "h": 2.0}'


def test_collect_requirements_extracts_h_w():
    state: AgentState = {
        "messages": [{"role": "user", "content": "我家窗户高2米宽3米"}],
    }
    out = collect_requirements(state, _mock_chat_h2w3)
    assert out["requirements"]["h"] == 2.0
    assert out["requirements"]["w"] == 3.0
    assert out["step"] == "collect_requirements"


def test_collect_requirements_merges_with_existing():
    state: AgentState = {
        "messages": [{"role": "user", "content": "高1.5米"}],
        "requirements": {"w": 2.0},
    }
    mock = lambda _: '{"h": 1.5}'
    out = collect_requirements(state, mock)
    assert out["requirements"]["w"] == 2.0
    assert out["requirements"]["h"] == 1.5


def test_create_collect_requirements_node():
    node = create_collect_requirements_node(_mock_chat_h2w3)
    state: AgentState = {"messages": [{"role": "user", "content": "高2米宽3米"}]}
    out = node(state)
    assert out["requirements"].get("h") == 2.0
    assert out["requirements"].get("w") == 3.0
