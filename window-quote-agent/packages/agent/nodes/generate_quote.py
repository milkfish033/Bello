"""报价单生成节点：根据 price_result 生成 Markdown 报价单。"""
from typing import Any

from packages.agent.state import AgentState, next_step_count


def generate_quote(state: AgentState) -> dict[str, Any]:
    """
    从 state.price_result 生成 Markdown 格式报价单，
    必须包含「总价」和「明细表格」。
    """
    price_result = state.get("price_result") or {}
    total = price_result.get("total", 0)
    breakdown = price_result.get("breakdown") or []
    series_id = price_result.get("series_id", "")

    lines = ["# 窗户报价单", ""]
    lines.append("## 总价")
    lines.append(f"**¥{total:,.2f}**")
    lines.append("")

    lines.append("## 明细表格")
    lines.append("| 项目 | 数量 | 单价(元) | 金额(元) |")
    lines.append("|------|------|----------|----------|")
    for item in breakdown:
        name = item.get("item", "")
        qty = item.get("qty", 0)
        unit_price = item.get("unit_price", 0)
        amount = item.get("amount", qty * unit_price)
        lines.append(f"| {name} | {qty} | {unit_price} | {amount:,.2f} |")
    lines.append("")
    if series_id:
        lines.append(f"*系列：{series_id}*")

    quote_md = "\n".join(lines)
    return {"step": "generate_quote", "step_count": next_step_count(state), "quote_md": quote_md}
