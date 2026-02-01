"""Intent check 两层逻辑单测。"""
import pytest

from packages.intent.intent_check import keyword_switch, intent_check


def test_keyword_switch_empty_message():
    assert keyword_switch("", "产品咨询") is None
    assert keyword_switch("  ", "价格咨询") is None


def test_keyword_switch_same_intent_no_switch():
    # 当前是价格咨询，消息也是价格相关，不切换
    assert keyword_switch("多少钱", "价格咨询") is None


def test_keyword_switch_switch_to_price():
    # 当前是产品咨询，消息出现「报价」→ 切换到价格咨询
    assert keyword_switch("这款报价多少", "产品咨询") == "价格咨询"


def test_keyword_switch_switch_to_recommend():
    # 当前是其他，消息出现「推荐」→ 产品推荐
    assert keyword_switch("有什么推荐", "其他") == "产品推荐"


def test_intent_check_layer1_keyword_switches():
    new_intent, new_turns = intent_check("我要报价", "产品咨询", 2)
    assert new_intent == "价格咨询"
    assert new_turns == 1


def test_intent_check_no_switch_increments_turns():
    new_intent, new_turns = intent_check("继续说说", "其他", 1, run_intent_pipeline=None)
    assert new_intent == "其他"
    assert new_turns == 2


def test_intent_check_layer2_stale_pipeline_switches():
    def stub_pipeline(_msg):
        return {"primary_intent": "价格咨询"}

    new_intent, new_turns = intent_check(
        "那给我报个价吧",
        "其他",
        3,
        stale_threshold=3,
        run_intent_pipeline=stub_pipeline,
    )
    assert new_intent == "价格咨询"
    assert new_turns == 1


def test_intent_check_layer2_stale_pipeline_unchanged():
    def stub_same(_msg):
        return {"primary_intent": "其他"}

    new_intent, new_turns = intent_check(
        "随便聊聊",
        "其他",
        3,
        stale_threshold=3,
        run_intent_pipeline=stub_same,
    )
    assert new_intent == "其他"
    assert new_turns == 4
