"""意图节点：跑 intent pipeline 或 intent_check，输出 current_intent 作为**参考**，不强控路由。"""
from typing import Any, Callable

from packages.agent.state import AgentState, append_thinking_step, next_step_count
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
    每轮均做意图识别，输出 current_intent、turns_with_same_intent 作为**参考**；
    路由由 router 综合意图、flow_stage、对话等自由判断，不在此强制锁定。
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
            "step_count": next_step_count(state),
            "current_intent": primary,
            "turns_with_same_intent": 1,
            "rag_context": [],  # 新轮开始时清空，供 chat→router 时写入本轮 RAG 结果
            "thinking_steps": append_thinking_step(state, f"识别用户意图：{primary}"),
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
        "step_count": next_step_count(state),
        "current_intent": new_intent,
        "turns_with_same_intent": new_turns,
        "rag_context": [],  # 新轮开始时清空
        "thinking_steps": append_thinking_step(state, f"识别用户意图：{new_intent}"),
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
