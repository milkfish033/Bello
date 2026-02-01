"""Router 节点：判断用户意图为「闲聊/咨询」或「报价」。支持外部小模型意图分类。"""
import json
import re
from pathlib import Path
from typing import Any, Callable

from packages.agent.state import AgentState

ROUTER_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "router.md"


def _load_prompt() -> str:
    return ROUTER_PROMPT_PATH.read_text(encoding="utf-8")


def _parse_intent_from_response(response: str) -> str:
    """从 LLM 回复中解析 intent，默认 quote。"""
    text = response.strip()
    if "```json" in text:
        text = re.sub(r"^.*?```json\s*", "", text)
    if "```" in text:
        text = re.sub(r"\s*```.*$", "", text)
    try:
        data = json.loads(text)
        intent = data.get("intent", "quote")
        return intent if intent in ("chat", "quote") else "quote"
    except (json.JSONDecodeError, TypeError):
        return "quote"


def _last_user_message(state: AgentState) -> str:
    """从 state.messages 取最后一条用户消息。"""
    messages = state.get("messages") or []
    for m in reversed(messages):
        if m.get("role") == "user":
            return m.get("content") or ""
    return ""


def router(
    state: AgentState,
    *,
    intent_classifier: Callable[[str], str] | None = None,
    chat_completion: Callable[..., str] | None = None,
) -> dict[str, Any]:
    """
    根据 messages 中最后一条用户消息判断意图，更新 state.intent。
    - 若提供 intent_classifier(user_message) -> "chat"|"quote"：优先使用（预留外部小模型入口）。
    - 否则使用 chat_completion(messages) -> str，再解析 JSON 得到 intent。
    """
    user_message = _last_user_message(state)
    if intent_classifier is not None:
        intent = intent_classifier(user_message)
    elif chat_completion is not None:
        prompt = _load_prompt().replace("{{user_message}}", user_message)
        llm_messages = [{"role": "user", "content": prompt}]
        response = chat_completion(llm_messages)
        intent = _parse_intent_from_response(response)
    else:
        intent = "quote"
    return {"step": "router", "intent": intent}


def create_router_node(
    chat_completion: Callable[..., str] | None = None,
    intent_classifier: Callable[[str], str] | None = None,
):
    """
    返回供 LangGraph 使用的单参节点函数 (state) -> partial_state。
    优先使用 intent_classifier（外部小模型）；未提供时使用 chat_completion。
    """
    return lambda state: router(
        state,
        intent_classifier=intent_classifier,
        chat_completion=chat_completion,
    )


def router_by_current_intent(state: AgentState) -> dict[str, Any]:
    """
    按 state.current_intent 做路由时的「透传」节点：不修改 state，仅用于图上占位，
    实际分支由 conditional_edges 根据 state.current_intent 决定。
    """
    return {"step": "router"}
