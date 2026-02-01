"""产品咨询节点：直接用 RAG 查询，再让模型基于检索结果回答。"""
from typing import Any, Callable

from packages.agent.state import AgentState


def _last_user_message(state: AgentState) -> str:
    messages = state.get("messages") or []
    for m in reversed(messages):
        if m.get("role") == "user":
            return m.get("content") or ""
    return ""


def _build_rag_prompt(user_message: str, rag_context: list[str]) -> str:
    rag_text = "\n".join(rag_context) if rag_context else "（无相关检索结果）"
    return f"""基于以下参考资料回答用户问题，回答要简洁、准确。若资料中无相关内容，可说明并给出一般性建议。

参考资料：
{rag_text}

用户问题：
{user_message}
"""


def rag_query(
    state: AgentState,
    *,
    retrieve: Callable[[str], list[str]],
    chat_completion: Callable[..., str],
) -> dict[str, Any]:
    """
    产品咨询：用最后一条用户消息做 retrieve，再拼成带上下文的 prompt 交给 chat_completion，回复追加到 messages。
    """
    messages = list(state.get("messages") or [])
    user_message = _last_user_message(state)
    query = user_message.strip() or "窗户 型材 产品"
    chunks = retrieve(query)
    rag_context = chunks if chunks and isinstance(chunks[0], str) else [c.get("content", str(c)) for c in (chunks or [])]
    prompt = _build_rag_prompt(user_message, rag_context)
    llm_messages = [{"role": "user", "content": prompt}]
    response = chat_completion(llm_messages)
    messages.append({"role": "assistant", "content": response})
    return {
        "step": "rag_query",
        "messages": messages,
        "rag_context": rag_context,
    }


def create_rag_query_node(
    retrieve: Callable[[str], list[str]],
    chat_completion: Callable[..., str],
):
    """返回供 LangGraph 使用的单参节点函数 (state) -> partial_state。"""
    return lambda state: rag_query(state, retrieve=retrieve, chat_completion=chat_completion)
