"""Task 4.6：报价单生成节点测试。"""
import pytest

from packages.agent.nodes.generate_quote import generate_quote
from packages.agent.state import AgentState


def test_generate_quote_contains_total_and_table():
    state: AgentState = {
        "price_result": {
            "total": 3000,
            "breakdown": [
                {"item": "窗面积", "qty": 6, "unit_price": 500, "amount": 3000},
            ],
            "series_id": "65",
        },
    }
    out = generate_quote(state)
    assert "quote_md" in out
    md = out["quote_md"]
    assert "总价" in md
    assert "明细表格" in md
    assert "3,000" in md or "3000" in md
    assert "|" in md
    assert out["step"] == "generate_quote"


def test_generate_quote_empty_price_result():
    state: AgentState = {"price_result": {}}
    out = generate_quote(state)
    assert "总价" in out["quote_md"]
    assert "明细表格" in out["quote_md"]
