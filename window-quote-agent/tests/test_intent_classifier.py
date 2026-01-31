"""意图分类模块测试：预留外部小模型调用位 + 解析逻辑。"""
import pytest

from packages.llm.intent_classifier import (
    classify_intent,
    create_intent_classifier,
    parse_intent_from_response,
    call_external_small_model,
)


def test_parse_intent_from_response():
    assert parse_intent_from_response('{"intent": "quote"}') == "quote"
    assert parse_intent_from_response('{"intent": "chat"}') == "chat"
    assert parse_intent_from_response('```json\n{"intent": "quote"}\n```') == "quote"
    assert parse_intent_from_response("invalid") == "quote"
    assert parse_intent_from_response('{"intent": "other"}') == "quote"


def test_call_external_small_model_fallback():
    """预留位未接入时返回默认 JSON，可被解析。"""
    raw = call_external_small_model("我想装窗户")
    assert "intent" in raw
    assert parse_intent_from_response(raw) in ("chat", "quote")


def test_classify_intent_uses_fallback():
    """classify_intent 内部调用预留位，当前为 fallback。"""
    intent = classify_intent("任意用户消息")
    assert intent in ("chat", "quote")


def test_create_intent_classifier_with_custom_call():
    """可注入自定义 external_call，便于测试或接入真实 API。"""
    def mock_api(msg: str) -> str:
        return '{"intent": "chat"}' if "咨询" in msg else '{"intent": "quote"}'
    classifier = create_intent_classifier(external_call=mock_api)
    assert classifier("我想咨询一下") == "chat"
    assert classifier("我要报价") == "quote"
