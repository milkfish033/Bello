"""闲聊节点：其他/公司介绍/产品咨询 → 直接用模型返回；可选 RAG 等工具由模型按需调用。"""
from typing import Any, Callable

from packages.agent.state import AgentState, next_step_count


def _last_user_message(state: AgentState) -> str:
    messages = state.get("messages") or []
    for m in reversed(messages):
        if m.get("role") == "user":
            return m.get("content") or ""
    return ""


def _dict_to_langchain_messages(messages: list[dict[str, Any]]) -> list:
    """将 state.messages (list[dict]) 转为 LangChain BaseMessage 列表。"""
    from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

    out = []
    for m in messages:
        role = m.get("role") or "user"
        content = m.get("content") or ""
        if role == "user":
            out.append(HumanMessage(content=content))
        elif role == "assistant":
            tool_calls = m.get("tool_calls")
            out.append(AIMessage(content=content, tool_calls=tool_calls))
        elif role == "tool":
            out.append(ToolMessage(content=content, tool_call_id=m.get("tool_call_id", "")))
    return out


def _get_tool_call_info(tc: Any) -> tuple[str, dict, str]:
    """从 LangChain tool_call 中取 name, args, id。"""
    if isinstance(tc, dict):
        name = tc.get("name", "")
        args = tc.get("args") if isinstance(tc.get("args"), dict) else {}
        tid = tc.get("id", "")
        return name, args, tid
    name = getattr(tc, "name", "") or (tc.get("name") if callable(getattr(tc, "get", None)) else "")
    args = getattr(tc, "args", None) or (tc.get("args") if callable(getattr(tc, "get", None)) else {})
    if not isinstance(args, dict):
        args = {}
    tid = getattr(tc, "id", "") or (tc.get("id") if callable(getattr(tc, "get", None)) else "")
    return name, args, tid


# RAG 工具名，用于收集返还结果供 router 读取
RAG_TOOL_NAME = "product_knowledge_search"


def _chat_with_tools(
    state: AgentState,
    *,
    llm: Any,
    tools: list[Any],
    max_tool_rounds: int = 5,
) -> dict[str, Any]:
    """带工具调用的对话：LLM 可请求调用 RAG 等工具，循环直到无 tool_calls 或达上限。将 RAG 返还结果写入 rag_context 供 router 读取。"""
    from langchain_core.messages import ToolMessage

    messages = list(state.get("messages") or [])
    lc_messages = _dict_to_langchain_messages(messages)
    bound = llm.bind_tools(tools)
    response = None
    rag_context: list[str] = []  # 本轮 RAG 工具返还结果，供 router 决定是否结束

    for _ in range(max_tool_rounds):
        response = bound.invoke(lc_messages)
        if not getattr(response, "tool_calls", None):
            break
        lc_messages.append(response)
        for tc in response.tool_calls:
            name, args, tid = _get_tool_call_info(tc)
            tool_by_name = {t.name: t for t in tools}
            func = tool_by_name.get(name)
            if func:
                result = func.invoke(args) if hasattr(func, "invoke") else func(args)
            else:
                result = "（工具未找到）"
            if name == RAG_TOOL_NAME:
                rag_context.append(str(result))
            lc_messages.append(ToolMessage(content=str(result), tool_call_id=tid))

    if response is None:
        messages.append({"role": "assistant", "content": ""})
        return {"step": "chat", "step_count": next_step_count(state), "messages": messages, "rag_context": rag_context}
    final_content = getattr(response, "content", None) or str(response)
    if isinstance(final_content, list):
        parts = [
            c.get("text", str(c)) if isinstance(c, dict) else (c if isinstance(c, str) else getattr(c, "content", str(c)))
            for c in final_content
        ]
        final_content = "\n".join(parts)
    messages.append({"role": "assistant", "content": final_content})
    return {"step": "chat", "step_count": next_step_count(state), "messages": messages, "rag_context": rag_context}


def chat(
    state: AgentState,
    *,
    chat_completion: Callable[..., str],
    tools: list[Any] | None = None,
    llm: Any = None,
) -> dict[str, Any]:
    """
    闲聊/产品咨询：将当前 messages 交给模型，把回复追加到 messages。
    - 若提供 tools 且 llm 支持 bind_tools：模型可调用 RAG 等工具，再基于结果回答。
    - 否则：直接 chat_completion(messages) 返回文本。
    """
    if tools and llm is not None:
        return _chat_with_tools(state, llm=llm, tools=tools)
    messages = list(state.get("messages") or [])
    response = chat_completion(messages)
    messages.append({"role": "assistant", "content": response})
    return {"step": "chat", "step_count": next_step_count(state), "messages": messages}


def create_chat_node(
    chat_completion: Callable[..., str],
    tools: list[Any] | None = None,
    llm: Any = None,
):
    """返回供 LangGraph 使用的单参节点函数 (state) -> partial_state。支持可选 tools + llm。"""
    return lambda state: chat(
        state,
        chat_completion=chat_completion,
        tools=tools,
        llm=llm,
    )
