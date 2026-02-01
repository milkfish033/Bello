"""闲聊节点：其他/公司介绍 → 直接用模型返回输出。"""
from typing import Any, Callable

from packages.agent.state import AgentState


def _last_user_message(state: AgentState) -> str:
    messages = state.get("messages") or []
    for m in reversed(messages):
        if m.get("role") == "user":
            return m.get("content") or ""
    return ""


def chat(
    state: AgentState,
    *,
    chat_completion: Callable[..., str],
) -> dict[str, Any]:
    """
    闲聊模式：将当前 messages 交给 chat_completion，把回复追加到 messages。
    """
    messages = list(state.get("messages") or [])
    response = chat_completion(messages)
    messages.append({"role": "assistant", "content": response})
    return {"step": "chat", "messages": messages}


def create_chat_node(chat_completion: Callable[..., str]):
    """返回供 LangGraph 使用的单参节点函数 (state) -> partial_state。"""
    return lambda state: chat(state, chat_completion=chat_completion)
