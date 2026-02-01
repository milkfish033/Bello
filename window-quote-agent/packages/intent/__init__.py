"""Prompt 清洗 + 多意图识别：规则优先 + 不确定性模型兜底，输出结构化中间表示。"""
from packages.intent.schemas import (
    PreprocessOutput,
    RuleIntentsOutput,
    IntentPipelineOutput,
    TaskItem,
    INTENTS,
    INTENT_PRIORITY,
)
from packages.intent.preprocess import preprocess
from packages.intent.rule_intents import rule_based_intent_tagging
from packages.intent.uncertainty_classifier import (
    UncertaintyClassifier,
    RealZeroShotClassifier,
    StubUncertaintyClassifier,
    UncertaintyClassifierResult,
)
from packages.intent.pipeline import run_intent_pipeline
from packages.intent.intent_check import intent_check, keyword_switch

__all__ = [
    "preprocess",
    "rule_based_intent_tagging",
    "UncertaintyClassifier",
    "RealZeroShotClassifier",
    "StubUncertaintyClassifier",
    "UncertaintyClassifierResult",
    "run_intent_pipeline",
    "PreprocessOutput",
    "RuleIntentsOutput",
    "IntentPipelineOutput",
    "TaskItem",
    "INTENTS",
    "INTENT_PRIORITY",
    "intent_check",
    "keyword_switch",
]
