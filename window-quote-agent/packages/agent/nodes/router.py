"""Router 节点：接受 intent_node 输出，作为 planner 用 GPT-4o 决策是否拆分任务并分配下一节点。"""
import json
import os
import re
from pathlib import Path
from typing import Any, Callable

from packages.agent.state import AgentState, next_step_count

ROUTER_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "router.md"
ROUTER_PLANNER_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "router_planner.md"

# router 只做 planner：输出下一节点；是否 END 由 check 节点决定
VALID_NEXT_NODES = (
    "chat",
    "collect_recommend_params",
    "collect_requirements",
    "recommend",
    "price_quote",
    "generate_quote",
)
INTENT_TO_NODE = {
    "其他": "chat",
    "公司介绍": "chat",
    "产品推荐": "collect_recommend_params",
    "产品咨询": "chat",  # RAG 作为 chat 的 tool，由模型按需调用
    "价格咨询": "collect_requirements",
}


def _load_prompt(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _last_user_message(state: AgentState) -> str:
    """从 state.messages 取最后一条用户消息。"""
    messages = state.get("messages") or []
    for m in reversed(messages):
        if m.get("role") == "user":
            return m.get("content") or ""
    return ""


def _recent_messages_summary(state: AgentState, max_turns: int = 3) -> str:
    """最近几轮对话的简要摘要，供 planner 参考。"""
    messages = state.get("messages") or []
    if not messages:
        return "（无历史）"
    recent = messages[-max_turns * 2 :]  # 粗略按轮数截断
    parts = []
    for m in recent:
        role = m.get("role", "")
        content = (m.get("content") or "")[:200]
        if content:
            parts.append(f"{role}: {content}")
    return "\n".join(parts) if parts else "（无）"


def _rag_context_summary(state: AgentState) -> str:
    """RAG 工具本轮返还结果摘要，供 planner 决定是否结束。"""
    rag = state.get("rag_context") or []
    if not rag:
        return "（本轮未调用 RAG）"
    parts = []
    for i, block in enumerate(rag[:5], 1):
        s = (block[:500] + "…") if len(block) > 500 else block
        parts.append(f"[RAG-{i}]\n{s}")
    return "\n\n".join(parts)


def _parse_planner_response(response: str) -> dict[str, Any]:
    """从 LLM 回复中解析 planner JSON。next_node 可为 END 表示结束。"""
    text = response.strip()
    if "```json" in text:
        text = re.sub(r"^.*?```json\s*", "", text)
    if "```" in text:
        text = re.sub(r"\s*```.*$", "", text)
    try:
        data = json.loads(text)
        raw = (data.get("next_node") or "").strip()
        if raw in VALID_NEXT_NODES:
            next_node = raw
        else:
            next_node = ""
        task_split = bool(data.get("task_split", False))
        plan_tasks = data.get("plan_tasks")
        if not isinstance(plan_tasks, list):
            plan_tasks = []
        return {"next_node": next_node, "task_split": task_split, "plan_tasks": plan_tasks}
    except (json.JSONDecodeError, TypeError):
        return {"next_node": "", "task_split": False, "plan_tasks": []}


def _fallback_next_node(state: AgentState) -> str:
    """无 LLM 或解析失败时，按 last_step 与 state 推断下一节点（不输出 END，由 check 决定）。"""
    last_step = state.get("step") or ""
    intent = state.get("current_intent") or "其他"
    if last_step == "price_quote":
        return "generate_quote"
    if last_step == "recommend" and intent == "价格咨询":
        return "price_quote"
    if last_step == "recommend":
        return "chat"
    if last_step == "collect_requirements":
        return "recommend"
    if last_step == "collect_recommend_params" and state.get("recommend_params_ready"):
        return "recommend"
    if last_step == "collect_recommend_params":
        return "chat"
    if last_step in ("chat", "intent", "router", "check", ""):
        return INTENT_TO_NODE.get(intent, "chat")
    return "chat"


def router_planner(
    state: AgentState,
    *,
    llm: Any = None,
) -> dict[str, Any]:
    """
    接受 intent_node 的输出（current_intent、turns_with_same_intent），作为 planner：
    使用 GPT-4o 根据当前意图和用户信息决定是否拆分任务，并将结果分配给相应节点。
    返回 { step, next_node, task_split?, plan_tasks? }，供图上的 conditional_edges 使用。
    """
    current_intent = (state.get("current_intent") or "").strip()
    turns = max(0, state.get("turns_with_same_intent") or 0)
    user_message = _last_user_message(state)
    recent = _recent_messages_summary(state)
    rag_summary = _rag_context_summary(state)

    if llm is None:
        api_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
        if api_key:
            try:
                from langchain_openai import ChatOpenAI
                llm = ChatOpenAI(
                    model="gpt-4o",
                    api_key=api_key,
                    temperature=0,
                )
            except Exception:
                llm = None
        # 无有效 API key 时直接用 fallback，避免发请求卡住（如本地跑测）

    if llm is None:
        next_node = _fallback_next_node(state)
        return {
            "step": "router",
            "next_node": next_node,
            "task_split": False,
            "plan_tasks": [],
        }

    last_step = state.get("step") or "（未知）"
    prompt_tpl = _load_prompt(ROUTER_PLANNER_PROMPT_PATH)
    prompt = (
        prompt_tpl.replace("{{current_intent}}", current_intent or "（未知）")
        .replace("{{turns_with_same_intent}}", str(turns))
        .replace("{{user_message}}", user_message or "（无）")
        .replace("{{recent_messages}}", recent)
        .replace("{{rag_context}}", rag_summary)
        .replace("{{last_step}}", last_step)
    )

    try:
        from langchain_core.messages import HumanMessage
        messages = [HumanMessage(content=prompt)]
        response = llm.invoke(messages)
        if hasattr(response, "content"):
            response_text = response.content or ""
        else:
            response_text = str(response)
    except Exception:
        response_text = ""

    parsed = _parse_planner_response(response_text)
    next_node = parsed["next_node"]
    if not next_node:
        next_node = _fallback_next_node(state)
        parsed["next_node"] = next_node

    # 不覆盖 state.step，以便下一节点仍能读到上一业务节点（check 会覆盖 step 吗？check 不返回 step，所以 state.step 仍是上一节点）
    return {
        "step": "router",
        "step_count": next_step_count(state),
        "next_node": next_node,
        "task_split": parsed["task_split"],
        "plan_tasks": parsed["plan_tasks"],
    }


def create_router_planner_node(llm: Any = None):
    """
    返回供 LangGraph 使用的单参节点函数 (state) -> partial_state。
    使用 GPT-4o 作为 planner；若未传入 llm 则从环境变量 OPENAI_API_KEY 创建 ChatOpenAI。
    """
    return lambda state: router_planner(state, llm=llm)


# ----- 兼容旧用法：按 current_intent 透传，不调用 LLM -----


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


def router(
    state: AgentState,
    *,
    intent_classifier: Callable[[str], str] | None = None,
    chat_completion: Callable[..., str] | None = None,
) -> dict[str, Any]:
    """
    旧版：根据 messages 中最后一条用户消息判断意图，更新 state.intent。
    若提供 intent_classifier 或 chat_completion 则用其得到 intent；否则不适用（图已用 intent_node + router_planner）。
    """
    user_message = _last_user_message(state)
    if intent_classifier is not None:
        intent = intent_classifier(user_message)
    elif chat_completion is not None:
        prompt = _load_prompt(ROUTER_PROMPT_PATH).replace("{{user_message}}", user_message)
        llm_messages = [{"role": "user", "content": prompt}]
        response = chat_completion(llm_messages)
        intent = _parse_intent_from_response(response)
    else:
        intent = "quote"
    return {"step": "router", "step_count": next_step_count(state), "intent": intent}


def create_router_node(
    chat_completion: Callable[..., str] | None = None,
    intent_classifier: Callable[[str], str] | None = None,
):
    """返回供 LangGraph 使用的单参节点函数 (state) -> partial_state。旧版按消息分类 intent。"""
    return lambda state: router(
        state,
        intent_classifier=intent_classifier,
        chat_completion=chat_completion,
    )


def router_by_current_intent(state: AgentState) -> dict[str, Any]:
    """
    按 state.current_intent 做路由的透传节点：不调用 LLM，仅把 current_intent 映射为 next_node 写入 state。
    实际分支由 conditional_edges 根据 state.next_node（或兼容 state.current_intent）决定。
    """
    current_intent = state.get("current_intent") or "其他"
    next_node = INTENT_TO_NODE.get(current_intent, "chat")
    return {"step": "router", "step_count": next_step_count(state), "next_node": next_node}
