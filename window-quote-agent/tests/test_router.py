"""Task 4.2：Router 节点测试。"""
import pytest

from packages.agent.nodes.router import (
    router,
    create_router_node,
    create_router_planner_node,
    router_planner,
    router_by_current_intent,
)
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


# ----- Router planner（接受 intent_node 输出，GPT-4o 决策）-----


def test_router_planner_fallback_without_llm():
    """无 LLM 时按 current_intent 映射到 next_node。"""
    state: AgentState = {
        "messages": [{"role": "user", "content": "我想装窗户"}],
        "current_intent": "价格咨询",
        "turns_with_same_intent": 1,
    }
    out = router_planner(state, llm=None)
    assert out["step"] == "router"
    assert out["next_node"] == "collect_requirements"
    assert out.get("task_split") is False
    assert out.get("plan_tasks") == []


def test_router_planner_fallback_intent_to_node():
    """各意图应映射到正确 next_node。"""
    for intent, expected_node in [
        ("其他", "chat"),
        ("公司介绍", "chat"),
        ("产品推荐", "collect_recommend_params"),
        ("产品咨询", "chat"),  # RAG 作为 chat 的 tool
        ("价格咨询", "collect_requirements"),
    ]:
        state: AgentState = {
            "messages": [{"role": "user", "content": "test"}],
            "current_intent": intent,
            "turns_with_same_intent": 1,
        }
        out = router_planner(state, llm=None)
        assert out["next_node"] == expected_node, intent


def test_router_planner_with_mock_llm():
    """提供 mock LLM 时使用其返回的 next_node 与 plan_tasks。"""
    class MockMessage:
        content = '{"next_node": "chat", "task_split": true, "plan_tasks": [{"intent": "产品咨询", "node": "chat"}]}'
    class MockLLM:
        def invoke(self, messages):
            return MockMessage()
    state: AgentState = {
        "messages": [{"role": "user", "content": "断桥铝和塑钢有什么区别"}],
        "current_intent": "产品咨询",
        "turns_with_same_intent": 1,
    }
    out = router_planner(state, llm=MockLLM())
    assert out["step"] == "router"
    assert out["next_node"] == "chat"
    assert out["task_split"] is True
    assert len(out["plan_tasks"]) == 1
    assert out["plan_tasks"][0].get("node") == "chat"


def test_create_router_planner_node():
    """create_router_planner_node 返回的节点应写入 next_node。"""
    node = create_router_planner_node(llm=None)
    state: AgentState = {
        "messages": [{"role": "user", "content": "推荐一款"}],
        "current_intent": "产品推荐",
        "turns_with_same_intent": 1,
    }
    out = node(state)
    assert out["next_node"] == "collect_recommend_params"


def test_router_by_current_intent():
    """router_by_current_intent 透传时写入 next_node。"""
    state: AgentState = {"current_intent": "价格咨询"}
    out = router_by_current_intent(state)
    assert out["step"] == "router"
    assert out["next_node"] == "collect_requirements"
