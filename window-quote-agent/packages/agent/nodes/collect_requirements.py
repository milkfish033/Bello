"""需求采集节点：从用户消息中提取尺寸、地点等，更新 state.requirements。"""
import json
import re
from pathlib import Path
from typing import Any, Callable

from packages.agent.state import AgentState

COLLECT_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "collect_requirements.md"


def _load_prompt() -> str:
    return COLLECT_PROMPT_PATH.read_text(encoding="utf-8")


def _parse_requirements_from_response(response: str) -> dict[str, Any]:
    """从 LLM 回复中解析 requirements JSON，未解析到时返回空 dict。"""
    text = response.strip()
    if "```json" in text:
        text = re.sub(r"^.*?```json\s*", "", text)
    if "```" in text:
        text = re.sub(r"\s*```.*$", "", text)
    try:
        data = json.loads(text)
        if not isinstance(data, dict):
            return {}
        out = {}
        if "w" in data and data["w"] is not None:
            try:
                out["w"] = float(data["w"])
            except (TypeError, ValueError):
                pass
        if "h" in data and data["h"] is not None:
            try:
                out["h"] = float(data["h"])
            except (TypeError, ValueError):
                pass
        if "location" in data and data["location"] is not None:
            out["location"] = str(data["location"]).strip()
        if "opening_count" in data and data["opening_count"] is not None:
            try:
                out["opening_count"] = int(data["opening_count"])
            except (TypeError, ValueError):
                pass
        return out
    except (json.JSONDecodeError, TypeError):
        return {}


def collect_requirements(
    state: AgentState, chat_completion: Callable[..., str]
) -> dict[str, Any]:
    """
    根据 messages 中最后一条用户消息调用 LLM 提取需求，更新 state.requirements。
    chat_completion(messages: list[dict]) -> str。
    """
    messages = state.get("messages") or []
    user_message = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            user_message = m.get("content") or ""
            break
    prompt = _load_prompt().replace("{{user_message}}", user_message)
    llm_messages = [{"role": "user", "content": prompt}]
    response = chat_completion(llm_messages)
    extracted = _parse_requirements_from_response(response)
    existing = dict(state.get("requirements") or {})
    merged = {**existing, **extracted}
    return {"step": "collect_requirements", "requirements": merged}


def create_collect_requirements_node(chat_completion: Callable[..., str]):
    """返回供 LangGraph 使用的单参节点函数 (state) -> partial_state。"""
    return lambda state: collect_requirements(state, chat_completion)
