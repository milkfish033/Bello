"""
Step 4~6：意图聚合、主次意图判定、多意图拆分
Pipeline：串联 Preprocess → Rule-based → UncertaintyClassifier → Aggregation → Output
"""
from typing import Any

from packages.intent.schemas import (
    IntentPipelineOutput,
    TaskItem,
    INTENT_PRIORITY,
)
from packages.intent.preprocess import preprocess
from packages.intent.rule_intents import rule_based_intent_tagging
from packages.intent.uncertainty_classifier import (
    UncertaintyClassifier,
    RealZeroShotClassifier,
)


def _aggregate_intents(
    rule_intents: list[str],
    model_result: dict[str, Any] | None,
    tau: float = 0.6,
) -> tuple[list[str], float, str]:
    """
    Step 4：意图聚合
    final_intents = rule_intents 非空 → rule_intents；否则 → model_intents。
    返回 (final_intents, confidence, source)。
    """
    if rule_intents:
        return (list(rule_intents), 1.0, "rule")
    if model_result:
        intents = list(model_result.get("intents") or [])
        confidence = float(model_result.get("confidence", 0.0))
        if confidence < tau or not intents:
            intents = ["其他"]
        return (intents, confidence, "model")
    return (["其他"], 0.0, "rule")


def _primary_secondary_intents(final_intents: list[str]) -> tuple[str, list[str]]:
    """
    Step 5：主次意图判定（用于任务编排）
    优先级：价格咨询 > 产品推荐 > 产品咨询 > 公司介绍 > 其他
    """
    if not final_intents:
        return ("其他", [])
    ordered = [i for i in INTENT_PRIORITY if i in final_intents]
    if not ordered:
        ordered = list(final_intents)
    primary = ordered[0]
    secondary = [i for i in ordered[1:]]
    return (primary, secondary)


def _task_split(final_intents: list[str], cleaned_prompt: str) -> list[TaskItem]:
    """
    Step 6：多意图拆分
    当 final_intents.length > 1 时，拆成 tasks；否则单任务。
    """
    if not final_intents:
        return [{"intent": "其他", "description": cleaned_prompt or ""}]
    primary, secondary = _primary_secondary_intents(final_intents)
    all_ordered = [primary] + secondary
    tasks: list[TaskItem] = []
    for intent in all_ordered:
        tasks.append({
            "intent": intent,
            "description": cleaned_prompt or "",
        })
    return tasks


def run_intent_pipeline(
    raw_prompt: str,
    *,
    uncertainty_classifier: UncertaintyClassifier | None = None,
    use_model_when_rules_empty: bool = True,
    tau: float = 0.6,
) -> IntentPipelineOutput:
    """
    完整流水线：Preprocess → Rule-based →（可选）UncertaintyClassifier → 聚合 → 主次意图 → Task Split。
    返回结构化输出，供后续 agent 使用。
    """
    # Step 1
    pre = preprocess(raw_prompt)
    raw_prompt = pre["raw_prompt"]
    cleaned_prompt = pre["cleaned_prompt"]

    # Step 2
    rule_out = rule_based_intent_tagging(cleaned_prompt)
    rule_intents = rule_out["rule_intents"]
    rule_hits = rule_out["rule_hits"]

    # Step 3：仅当 rule_intents 为空时调用不确定性分类器（默认 facebook/bart-large-mnli）
    model_result: dict[str, Any] | None = None
    if use_model_when_rules_empty and (not rule_intents):
        classifier = uncertainty_classifier or RealZeroShotClassifier()
        model_result = classifier.predict(cleaned_prompt)
        if model_result.get("confidence", 0) < tau:
            model_result = {"intents": ["其他"], "confidence": model_result.get("confidence", 0)}

    # Step 4
    final_intents, confidence, source = _aggregate_intents(
        rule_intents, model_result, tau=tau
    )

    # Step 5
    primary_intent, secondary_intents = _primary_secondary_intents(final_intents)

    # Step 6
    tasks = _task_split(final_intents, cleaned_prompt)

    return IntentPipelineOutput(
        raw_prompt=raw_prompt,
        cleaned_prompt=cleaned_prompt,
        intents=final_intents,
        primary_intent=primary_intent,
        secondary_intents=secondary_intents, 
        tasks=tasks,
        confidence=confidence,
        source=source,
    )
