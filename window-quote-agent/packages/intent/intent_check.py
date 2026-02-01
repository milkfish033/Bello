"""
意图校验：两层逻辑，用于在 router 前决定是否切换 current_intent。
1. 关键词检测：若当前消息命中明显区别于 current_intent 的关键词，果断切换。
2. 长时间不变软校验：若 current_intent 已连续保持多轮，用 run_intent_pipeline 软测；一致则继续，不一致则切换。
暂不考虑多意图。
"""
from typing import Any, Callable

from packages.intent.rule_intents import INTENT_RULES, RULE_ORDER
from packages.intent.schemas import INTENTS  # 产品咨询 | 产品推荐 | 价格咨询 | 公司介绍 | 其他


def keyword_switch(message: str, current_intent: str) -> str | None:
    """
    第一层：关键词检测。
    若 message 命中某意图 Y 的关键词，且 Y != current_intent，则返回 Y（果断切换）；
    否则返回 None（不切换）。
    若命中多个 Y，按 RULE_ORDER 取第一个与 current_intent 不同的。
    """
    if not message or not message.strip():
        return None
    text = message.strip()
    current = (current_intent or "").strip()
    for intent in RULE_ORDER:
        if intent not in INTENT_RULES or intent == current:
            continue
        for kw in INTENT_RULES[intent]:
            if kw in text:
                return intent
    return None


def intent_check(
    message: str,
    current_intent: str,
    turns_with_same_intent: int,
    *,
    stale_threshold: int = 3,
    run_intent_pipeline: Callable[[str], Any] | None = None,
) -> tuple[str, int]:
    """
    两层意图校验，返回 (new_intent, new_turns_with_same_intent)。

    - Layer 1：若 keyword_switch 返回 Y，则 (Y, 1)。
    - Layer 2：若 turns_with_same_intent >= stale_threshold 且提供了 run_intent_pipeline，
      则对 message 跑 pipeline，取 primary_intent；若与 current_intent 不同则 (primary_intent, 1)，否则 (current_intent, turns+1)。
    - 否则：(current_intent, turns+1)。
    """
    # Layer 1
    switched = keyword_switch(message, current_intent)
    if switched is not None:
        return (switched, 1)

    # Layer 2：长时间不变时软校验
    current = current_intent or "其他"
    turns = max(0, turns_with_same_intent)

    if turns >= stale_threshold and run_intent_pipeline is not None:
        out = run_intent_pipeline(message)
        primary = out.get("primary_intent") if isinstance(out, dict) else getattr(out, "primary_intent", None)
        if primary and primary in INTENTS and primary != current:
            return (primary, 1)
        return (current, turns + 1)

    return (current, turns + 1)
