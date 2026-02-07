"""报价节点：根据 requirements 与 selection 调用定价工具，写入 state.price_result。"""
from typing import Any, Callable

from packages.agent.state import AgentState, next_step_count


def price_quote(
    state: AgentState,
    calculate_price: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    """
    从 state.requirements 和 state.selection 组装输入，调用定价工具，
    将结果写入 state.price_result。
    calculate_price(requirements, selection) -> price_result dict，
    至少包含 total、breakdown 等。
    """
    requirements = state.get("requirements") or {}
    selection = state.get("selection") or {}
    result = calculate_price(requirements, selection)
    return {"step": "price_quote", "step_count": next_step_count(state), "price_result": result}


def create_price_quote_node(
    calculate_price: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]],
):
    """返回供 LangGraph 使用的单参节点函数 (state) -> partial_state。"""
    return lambda state: price_quote(state, calculate_price)
