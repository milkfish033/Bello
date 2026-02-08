"""产品推荐参数采集：先询问 参数、使用场景、特殊需求、价格预算，再走 RAG 推荐。"""
import json
import re
from pathlib import Path
from typing import Any, Callable

from packages.agent.state import AgentState, append_thinking_step, next_step_count

COLLECT_RECOMMEND_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "collect_recommend_params.md"

RECOMMEND_PARAM_KEYS = ("使用场景", "特殊需求", "价格预算", "参数")


def _load_prompt() -> str:
    return COLLECT_RECOMMEND_PROMPT_PATH.read_text(encoding="utf-8")


def _parse_recommend_params(response: str) -> dict[str, Any]:
    text = response.strip()
    if "```json" in text:
        text = re.sub(r"^.*?```json\s*", "", text)
    if "```" in text:
        text = re.sub(r"\s*```.*$", "", text)
    try:
        data = json.loads(text)
        if not isinstance(data, dict):
            return {}
        return {k: str(data[k]).strip() for k in RECOMMEND_PARAM_KEYS if k in data and data[k] is not None and str(data[k]).strip()}
    except (json.JSONDecodeError, TypeError):
        return {}


def _has_any_param(params: dict[str, Any]) -> bool:
    return any(params.get(k) for k in RECOMMEND_PARAM_KEYS)


def _ask_message() -> str:
    return "请提供以下信息以便为您推荐合适产品：参数（如尺寸/型材）、使用场景、特殊需求、价格预算。可简要描述即可。"


def collect_recommend_params(
    state: AgentState,
    *,
    chat_completion: Callable[..., str],
) -> dict[str, Any]:
    """
    从最后一条用户消息中提取推荐参数，与 state.recommend_params 合并。
    若合并后仍无任何一项，则追加一条「请提供…」的 assistant 消息并返回（由上层路由 END）；
    若有任一项，则更新 recommend_params，由上层路由进入 recommend。
    """
    messages = list(state.get("messages") or [])
    user_message = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            user_message = m.get("content") or ""
            break
    existing = dict(state.get("recommend_params") or {})
    prompt = _load_prompt().replace("{{user_message}}", user_message)
    llm_messages = [{"role": "user", "content": prompt}]
    response = chat_completion(llm_messages)
    extracted = _parse_recommend_params(response)
    merged = {**existing, **extracted}

    if not _has_any_param(merged):
        messages.append({"role": "assistant", "content": _ask_message()})
        return {
            "step": "collect_recommend_params",
            "step_count": next_step_count(state),
            "messages": messages,
            "recommend_params": merged,
            "recommend_params_ready": False,
            "thinking_steps": append_thinking_step(state, "收集推荐参数（场景/需求/预算等）"),
        }
    return {
        "step": "collect_recommend_params",
        "step_count": next_step_count(state),
        "recommend_params": merged,
        "recommend_params_ready": True,
        "thinking_steps": append_thinking_step(state, "收集推荐参数（场景/需求/预算等）"),
    }


def create_collect_recommend_params_node(chat_completion: Callable[..., str]):
    """返回供 LangGraph 使用的单参节点函数 (state) -> partial_state。"""
    return lambda state: collect_recommend_params(state, chat_completion=chat_completion)
