"""Task 4.5：报价节点测试。"""
import pytest

from packages.agent.nodes.price_quote import price_quote, create_price_quote_node
from packages.agent.state import AgentState


def _mock_calculate_price(requirements, selection):
    w = requirements.get("w", 0)
    h = requirements.get("h", 0)
    area = w * h
    return {
        "total": round(area * 500, 2),
        "breakdown": [{"item": "窗面积", "qty": area, "unit_price": 500, "amount": round(area * 500, 2)}],
        "series_id": selection.get("series_id", ""),
    }


def test_price_quote_updates_state():
    state: AgentState = {
        "requirements": {"w": 3.0, "h": 2.0},
        "selection": {"series_id": "65"},
    }
    out = price_quote(state, _mock_calculate_price)
    assert "price_result" in out
    assert out["price_result"]["total"] == 3000.0
    assert out["price_result"]["series_id"] == "65"
    assert out["step"] == "price_quote"


def test_create_price_quote_node():
    node = create_price_quote_node(_mock_calculate_price)
    state: AgentState = {"requirements": {"w": 2, "h": 1.5}, "selection": {"series_id": "70"}}
    out = node(state)
    assert out["price_result"]["total"] == 1500.0
    assert out["price_result"]["series_id"] == "70"
