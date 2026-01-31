"""Task 4.2：Router 节点测试。"""
import pytest

from packages.agent.nodes.router import router, create_router_node
from packages.agent.state import AgentState


def _mock_chat_quote(_messages):
    return '{"intent": "quote"}'


def _mock_chat_chat(_messages):
    return '{"intent": "chat"}'


def test_router_outputs_quote_intent():
    state: AgentState = {
        "messages": [{"role": "user", "content": "我想装窗户"}],
    }
    out = router(state, chat_completion=_mock_chat_quote)
    assert out["intent"] == "quote"
    assert out["step"] == "router"


def test_router_outputs_chat_intent():
    state: AgentState = {
        "messages": [{"role": "user", "content": "断桥铝是什么"}],
    }
    out = router(state, chat_completion=_mock_chat_chat)
    assert out["intent"] == "chat"


def test_router_uses_intent_classifier_when_provided():
    """当提供 intent_classifier 时，走外部小模型路径，不调用 chat_completion。"""
    def classifier(msg: str) -> str:
        return "chat" if "是什么" in msg else "quote"
    state_chat: AgentState = {"messages": [{"role": "user", "content": "断桥铝是什么"}]}
    out = router(state_chat, intent_classifier=classifier)
    assert out["intent"] == "chat"
    state_quote: AgentState = {"messages": [{"role": "user", "content": "我想装窗户"}]}
    out2 = router(state_quote, intent_classifier=classifier)
    assert out2["intent"] == "quote"


def test_create_router_node():
    node = create_router_node(chat_completion=_mock_chat_quote)
    state: AgentState = {"messages": [{"role": "user", "content": "我想装窗户"}]}
    out = node(state)
    assert out["intent"] == "quote"
