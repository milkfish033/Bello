"""推荐节点：调用 RAG + Catalog，由 LLM 推荐系列，更新 state.selection。"""
import json
import re
from pathlib import Path
from typing import Any, Callable

from packages.agent.state import AgentState

RECOMMEND_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "recommend.md"


def _load_prompt() -> str:
    return RECOMMEND_PROMPT_PATH.read_text(encoding="utf-8")


def _parse_series_id_from_response(response: str) -> str | None:
    """从 LLM 回复中解析 series_id。"""
    text = response.strip()
    if "```json" in text:
        text = re.sub(r"^.*?```json\s*", "", text)
    if "```" in text:
        text = re.sub(r"\s*```.*$", "", text)
    try:
        data = json.loads(text)
        sid = data.get("series_id")
        return str(sid).strip() if sid else None
    except (json.JSONDecodeError, TypeError):
        return None


def recommend(
    state: AgentState,
    retrieve: Callable[[str], list[str]],
    list_series: Callable[[], list[dict[str, Any]]],
    chat_completion: Callable[..., str],
) -> dict[str, Any]:
    """
    根据 state.requirements 或最后一条消息构造 query，检索 RAG，结合 catalog 列表，
    调用 LLM 推荐 series_id，更新 state.selection 和 state.rag_context。
    - retrieve(query) -> list[str] 文本片段
    - list_series() -> list[{"id": str, "name": str}, ...]
    """
    messages = state.get("messages") or []
    requirements = state.get("requirements") or {}
    query = "窗户型材选型 断桥铝 系列推荐"
    if requirements:
        parts = []
        if requirements.get("w") and requirements.get("h"):
            parts.append(f"尺寸宽{requirements['w']}米高{requirements['h']}米")
        if requirements.get("location"):
            parts.append(requirements["location"])
        if parts:
            query = " ".join(parts) + " 型材推荐"
    chunks = retrieve(query)
    if not chunks:
        rag_context = []
    elif isinstance(chunks[0], str):
        rag_context = chunks
    else:
        rag_context = [c.get("content", str(c)) for c in chunks]
    rag_text = "\n".join(rag_context) if rag_context else "（无检索结果）"
    series_list = list_series()
    series_text = "\n".join(f"- id: {s.get('id', '')}, name: {s.get('name', s.get('id', ''))}" for s in series_list)
    prompt = (
        _load_prompt()
        .replace("{{rag_context}}", rag_text)
        .replace("{{series_list}}", series_text)
    )
    llm_messages = [{"role": "user", "content": prompt}]
    response = chat_completion(llm_messages)
    series_id = _parse_series_id_from_response(response)
    if not series_id and series_list:
        series_id = str(series_list[0].get("id", ""))
    selection = dict(state.get("selection") or {})
    selection["series_id"] = series_id or ""
    return {
        "step": "recommend",
        "selection": selection,
        "rag_context": rag_context,
    }


def create_recommend_node(
    retrieve: Callable[[str], list[str]],
    list_series: Callable[[], list[dict[str, Any]]],
    chat_completion: Callable[..., str],
):
    """返回供 LangGraph 使用的单参节点函数 (state) -> partial_state。"""
    return lambda state: recommend(state, retrieve, list_series, chat_completion)
