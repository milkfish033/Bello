"""需求采集节点：从用户消息中提取尺寸、地点等，更新 state.requirements。

主路径：LLM 返回结构化 JSON（见 collect_requirements.md），解析后作为提取结果。
规则仅作兜底：当 LLM 未解析出某字段（如 opening_count）时，才用规则从原文补全，避免重复索要。
"""
import json
import re
from pathlib import Path
from typing import Any, Callable

from packages.agent.state import AgentState, append_thinking_step, next_step_count

COLLECT_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "collect_requirements.md"


def _load_prompt() -> str:
    return COLLECT_PROMPT_PATH.read_text(encoding="utf-8")


REQUIREMENT_KEYS = ("w", "h", "location", "opening_count")


def _has_any_requirement(requirements: dict[str, Any]) -> bool:
    """是否有任意一项需求（宽、高、地点、开扇数）。"""
    for k in REQUIREMENT_KEYS:
        v = requirements.get(k)
        if v is not None and (not isinstance(v, str) or v.strip()):
            return True
    return False


def _ask_message() -> str:
    return "请提供窗户的尺寸（宽、高，单位米）、安装地点或城市、以及开扇数量等，以便为您报价。可简要描述即可。"


def _confirm_message(merged: dict[str, Any]) -> str:
    """已采集到至少一项参数时，返回简短确认，保证用户始终看到回复。"""
    return "已记录您的需求，正在为您推荐合适产品。"


def _off_topic_in_flow_message() -> str:
    """用户输入无法解析为报价参数时（如闲聊/换话题），在报价流程内仍须有回复，避免空响应。"""
    return "当前正在为您报价，请先补充尺寸（宽、高）或安装地点；若想换其他话题可以直接说。"


def _extract_w_h_from_text(text: str) -> tuple[float | None, float | None]:
    """兜底：仅当 LLM 未返回 w/h 时，从用户原文规则抽取宽高（米）。主路径仍依赖 LLM 结构化 JSON。"""
    if not (text or text.strip()):
        return (None, None)
    t = text.strip()
    w, h = None, None
    # 宽度为1 / 宽1 / 宽 1.5米（单位由 LLM 处理，此处仅抽数字）
    m = re.search(r"宽\s*度?\s*为?\s*(\d+(?:\.\d+)?)", t, re.IGNORECASE)
    if m:
        try:
            w = float(m.group(1))
        except (ValueError, TypeError):
            pass
    m = re.search(r"高\s*度?\s*为?\s*(\d+(?:\.\d+)?)", t, re.IGNORECASE)
    if m:
        try:
            h = float(m.group(1))
        except (ValueError, TypeError):
            pass
    return (w, h)


def _extract_opening_count_from_text(text: str) -> int | None:
    """兜底：仅当 LLM 未返回 opening_count 时，从用户原文规则抽取开扇数。主路径仍依赖 LLM 结构化 JSON。"""
    if not (text or text.strip()):
        return None
    t = text.strip()
    # 开扇数量1 / 开扇数量 2 / 开扇数量为3 / 开扇1 / 1扇 / 单扇
    m = re.search(r"开扇数量\s*为?\s*(\d+)", t, re.IGNORECASE)
    if m:
        try:
            return int(m.group(1))
        except (ValueError, TypeError):
            pass
    m = re.search(r"开扇\s*(\d+)", t)
    if m:
        try:
            return int(m.group(1))
        except (ValueError, TypeError):
            pass
    m = re.search(r"(\d+)\s*扇", t)
    if m:
        try:
            return int(m.group(1))
        except (ValueError, TypeError):
            pass
    if "单扇" in t or "一扇" in t:
        return 1
    return None


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
    若合并后仍无任何一项（宽、高、地点、开扇数），则追加一条「请提供…」的 assistant 消息并返回，
    由上层路由到 check 后 END 或再进 router；若有任一项，则更新 requirements，由上层路由进入 recommend。
    chat_completion(messages: list[dict]) -> str。
    """
    messages = list(state.get("messages") or [])
    user_message = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            user_message = m.get("content") or ""
            break
    prompt = _load_prompt().replace("{{user_message}}", user_message)
    llm_messages = [{"role": "user", "content": prompt}]
    response = chat_completion(llm_messages)
    extracted = _parse_requirements_from_response(response)
    # 以 LLM 结构化 JSON 为准；仅当 LLM 未解析出某字段时用规则兜底，保证「宽度为1」等能推进状态
    if extracted.get("opening_count") is None:
        n = _extract_opening_count_from_text(user_message)
        if n is not None:
            extracted["opening_count"] = n
    if extracted.get("w") is None or extracted.get("h") is None:
        rw, rh = _extract_w_h_from_text(user_message)
        if rw is not None:
            extracted["w"] = rw
        if rh is not None:
            extracted["h"] = rh
    existing = dict(state.get("requirements") or {})
    merged = {**existing, **extracted}

    if not _has_any_requirement(merged):
        messages.append({"role": "assistant", "content": _ask_message()})
        return {
            "step": "collect_requirements",
            "step_count": next_step_count(state),
            "messages": messages,
            "requirements": merged,
            "requirements_ready": False,
            "flow_stage": "collect_requirements",
            "thinking_steps": append_thinking_step(state, "收集报价需求（尺寸/地点/开扇等）"),
        }
    # 有至少一项参数：必须产出至少一条助手回复，避免 flow_stage 锁定下出现空响应
    if extracted:
        content = _confirm_message(merged)
    else:
        content = _off_topic_in_flow_message()
    messages.append({"role": "assistant", "content": content})
    return {
        "step": "collect_requirements",
        "step_count": next_step_count(state),
        "messages": messages,
        "requirements": merged,
        "requirements_ready": True,
        "flow_stage": "collect_requirements",
        "thinking_steps": append_thinking_step(state, "收集报价需求（尺寸/地点/开扇等）"),
    }


def create_collect_requirements_node(chat_completion: Callable[..., str]):
    """返回供 LangGraph 使用的单参节点函数 (state) -> partial_state。"""
    return lambda state: collect_requirements(state, chat_completion)
