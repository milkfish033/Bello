"""意图节点：跑 intent pipeline 或 intent_check，更新 state.current_intent 与 state.turns_with_same_intent。"""
from typing import Any, Callable

from packages.agent.state import AgentState
from packages.intent.intent_check import intent_check
from packages.intent.pipeline import run_intent_pipeline
from packages.intent.schemas import INTENTS


def _last_user_message(state: AgentState) -> str:
    messages = state.get("messages") or []
    for m in reversed(messages):
        if m.get("role") == "user":
            return m.get("content") or ""
    return ""


def resolve_intent(
    state: AgentState,
    *,
    run_intent_pipeline_fn: Callable[[str], Any],
    stale_threshold: int = 3,
) -> dict[str, Any]:
    """
    首轮用 run_intent_pipeline 得到 current_intent；后续轮用 intent_check（关键词 + 长时间软校验）。
    返回 { current_intent, turns_with_same_intent, step }。
    """
    user_message = _last_user_message(state)
    current = (state.get("current_intent") or "").strip()
    turns = max(0, state.get("turns_with_same_intent") or 0)

    if not current or current not in INTENTS:
        # 首轮或无效：直接跑 pipeline
        out = run_intent_pipeline_fn(user_message)
        primary = out.get("primary_intent") if isinstance(out, dict) else getattr(out, "primary_intent", "其他")
        if primary not in INTENTS:
            primary = "其他"
        return {
            "step": "intent",
            "current_intent": primary,
            "turns_with_same_intent": 1,
        }

    new_intent, new_turns = intent_check(
        user_message,
        current,
        turns,
        stale_threshold=stale_threshold,
        run_intent_pipeline=run_intent_pipeline_fn,
    )
    return {
        "step": "intent",
        "current_intent": new_intent,
        "turns_with_same_intent": new_turns,
    }


def create_intent_node(
    run_intent_pipeline_fn: Callable[[str], Any] | None = None,
    *,
    stale_threshold: int = 3,
):
    """返回供 LangGraph 使用的单参节点函数 (state) -> partial_state。"""
    fn = run_intent_pipeline_fn or run_intent_pipeline

    def node(state: AgentState) -> dict[str, Any]:
        return resolve_intent(
            state,
            run_intent_pipeline_fn=fn,
            stale_threshold=stale_threshold,
        )

    return node
