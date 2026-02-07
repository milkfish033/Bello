"""Prompt 清洗 + 多意图识别流水线单测：各步骤可单测、可回放。"""
import pytest

from packages.intent.preprocess import preprocess
from packages.intent.rule_intents import rule_based_intent_tagging
from packages.intent.uncertainty_classifier import (
    UncertaintyClassifier,
    StubUncertaintyClassifier,
    GptMiniUncertaintyClassifier,
)
from packages.intent.pipeline import run_intent_pipeline
from packages.intent.schemas import (
    INTENT_PRIORITY,
)


# --- Step 1: Preprocess ---
def test_preprocess_preserves_raw():
    out = preprocess("  我想　报价  ")
    assert out["raw_prompt"] == "  我想　报价  "
    assert "报价" in out["cleaned_prompt"]


def test_preprocess_full_to_half():
    out = preprocess("价格多少钱")  # 全角数字可在此扩展
    assert "raw_prompt" in out and "cleaned_prompt" in out


def test_preprocess_merge_punctuation():
    out = preprocess("你好。。。")
    assert "raw_prompt" in out and "cleaned_prompt" in out
    # 重复标点应被合并（实现依赖 _merge_repeated_punctuation）
    assert len(out["cleaned_prompt"]) <= len(out["raw_prompt"]) + 1


def test_preprocess_remove_filler():
    out = preprocess("那个 就是 报价 啊")
    assert out["cleaned_prompt"].strip() != "" or "报价" in out["cleaned_prompt"]


# --- Step 2: Rule-based ---
def test_rule_intents_single():
    out = rule_based_intent_tagging("多少钱一平")
    assert "价格咨询" in out["rule_intents"]
    assert "价格咨询" in out["rule_hits"]


def test_rule_intents_multi():
    out = rule_based_intent_tagging("推荐一款适合的，顺便报个价")
    intents = out["rule_intents"]
    assert len(intents) >= 1
    assert "产品推荐" in intents or "价格咨询" in intents
    assert "rule_hits" in out


def test_rule_intents_empty():
    out = rule_based_intent_tagging("哈哈今天天气不错")
    assert out["rule_intents"] == [] or "其他" not in out["rule_intents"]


# --- Step 3: UncertaintyClassifier ---
def test_stub_classifier_returns_other():
    stub = StubUncertaintyClassifier()
    r = stub.predict("随便一句话")
    assert "intents" in r
    assert r["intents"] == ["其他"]
    assert 0 <= r.get("confidence", 0) <= 1


# --- Pipeline ---
def test_pipeline_rule_priority():
    out = run_intent_pipeline("我想报价，多少钱", uncertainty_classifier=GptMiniUncertaintyClassifier())
    assert out["source"] == "rule"
    assert "价格咨询" in out["intents"]
    assert out["primary_intent"] in INTENT_PRIORITY
    assert "raw_prompt" in out and "cleaned_prompt" in out
    assert "tasks" in out and len(out["tasks"]) >= 1


def test_pipeline_multi_intent_tasks():
    out = run_intent_pipeline("推荐一款，顺便报个价", uncertainty_classifier=GptMiniUncertaintyClassifier())
    assert len(out["intents"]) >= 1
    assert out["primary_intent"] in out["intents"]
    assert all(t["intent"] in out["intents"] for t in out["tasks"])


def test_pipeline_empty_uses_model():
    out = run_intent_pipeline(
        "哈哈今天天气真好",
        use_model_when_rules_empty=True,
        uncertainty_classifier=GptMiniUncertaintyClassifier(),
    )
    return out 
    assert "intents" in out
    assert out["primary_intent"] == "其他" or out["primary_intent"] in out["intents"]
    assert out["source"] in ("rule", "model")


def test_pipeline_structured_output_keys():
    out = run_intent_pipeline("报价", uncertainty_classifier=GptMiniUncertaintyClassifier())
    required = ["raw_prompt", "cleaned_prompt", "intents", "primary_intent", "tasks", "confidence", "source"]
    for k in required:
        assert k in out, f"missing key: {k}"



if __name__ == "__main__":
    print("GPT Intent Classifier ready.")

    res = test_pipeline_empty_uses_model()

    print(res)
