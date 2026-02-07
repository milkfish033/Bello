"""Check 节点：用 GPT-4o 根据 state（上一节点、对话、RAG 等）决定是否结束；若不结束则交给 router（planner）决定下一步。"""
import json
import os
import re
from pathlib import Path
from typing import Any

from packages.agent.state import AgentState, next_step_count

CHECK_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "check.md"


def _load_prompt() -> str:
    return CHECK_PROMPT_PATH.read_text(encoding="utf-8")


def _last_user_message(state: AgentState) -> str:
    messages = state.get("messages") or []
    for m in reversed(messages):
        if m.get("role") == "user":
            return m.get("content") or ""
    return ""


def _recent_messages_summary(state: AgentState, max_turns: int = 3) -> str:
    messages = state.get("messages") or []
    if not messages:
        return "（无历史）"
    recent = messages[-max_turns * 2 :]
    parts = []
    for m in recent:
        role = m.get("role", "")
        content = (m.get("content") or "")[:200]
        if content:
            parts.append(f"{role}: {content}")
    return "\n".join(parts) if parts else "（无）"


def _rag_context_summary(state: AgentState) -> str:
    rag = state.get("rag_context") or []
    if not rag:
        return "（无）"
    parts = []
    for i, block in enumerate(rag[:3], 1):
        s = (block[:300] + "…") if len(block) > 300 else block
        parts.append(f"[{i}] {s}")
    return "\n".join(parts)


def _state_summary(state: AgentState) -> str:
    """简要摘要供 check 参考。"""
    parts = []
    if state.get("recommend_params_ready"):
        parts.append("已收集到推荐参数")
    if state.get("requirements"):
        parts.append("已采集报价需求")
    if state.get("selection"):
        parts.append("已选择系列/规格")
    if state.get("selection_ready"):
        parts.append("已有具体产品型号可报价")
    if state.get("price_result"):
        parts.append("已计算价格")
    return "；".join(parts) if parts else "（无）"


def _parse_check_response(response: str) -> bool:
    text = response.strip()
    if "```json" in text:
        text = re.sub(r"^.*?```json\s*", "", text)
    if "```" in text:
        text = re.sub(r"\s*```.*$", "", text)
    try:
        data = json.loads(text)
        return bool(data.get("should_end", False))
    except (json.JSONDecodeError, TypeError):
        return False


def check_node(state: AgentState, *, llm: Any = None) -> dict[str, Any]:
    """
    根据 state（上一节点、对话、RAG、报价单等）用 GPT-4o 决定是否结束。
    返回 { should_end }。不覆盖 state.step，以便 router 仍能读到上一节点。
    """
    last_step = state.get("step") or "（未知）"
    current_intent = state.get("current_intent") or "（未知）"
    user_message = _last_user_message(state)
    recent = _recent_messages_summary(state)
    rag_summary = _rag_context_summary(state)
    has_quote = "是" if (state.get("quote_md") or "").strip() else "否"
    state_summary = _state_summary(state)

    if llm is None:
        api_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
        if api_key:
            try:
                from langchain_openai import ChatOpenAI
                llm = ChatOpenAI(
                    model="gpt-4o",
                    api_key=api_key,
                    temperature=0.1,
                )
            except Exception:
                llm = None
        # 无有效 API key 时直接用 fallback，避免发请求卡住（如本地跑测）

    if llm is None:
        # fallback：generate_quote 后结束，其余不结束
        should_end = (last_step == "generate_quote")
        return {"step_count": next_step_count(state), "should_end": should_end}

    prompt_tpl = _load_prompt()
    prompt = (
        prompt_tpl.replace("{{last_step}}", last_step)
        .replace("{{current_intent}}", current_intent)
        .replace("{{user_message}}", user_message or "（无）")
        .replace("{{recent_messages}}", recent)
        .replace("{{rag_context}}", rag_summary)
        .replace("{{has_quote}}", has_quote)
        .replace("{{state_summary}}", state_summary)
    )

    try:
        from langchain_core.messages import HumanMessage
        response = llm.invoke([HumanMessage(content=prompt)])
        response_text = getattr(response, "content", None) or str(response)
    except Exception:
        response_text = ""
    should_end = _parse_check_response(response_text)
    return {"step_count": next_step_count(state), "should_end": should_end}


def create_check_node(llm: Any = None):
    """返回供 LangGraph 使用的单参节点函数 (state) -> partial_state。"""
    return lambda state: check_node(state, llm=llm)
