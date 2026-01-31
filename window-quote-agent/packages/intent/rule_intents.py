"""
Step 2：Rule-based 多意图标注
职责：高精度规则为 prompt 打上 0~N 个 intent 标签。
原则：命中即加 intent，不 return；允许多意图并存；规则有优先级但不互斥。
"""
import re
from typing import Any

from packages.intent.schemas import RuleIntentsOutput, INTENTS

# 意图 → 触发词/模式（非穷举，可配置扩展）
INTENT_RULES: dict[str, list[str]] = {
    "价格咨询": ["多少钱", "报价", "价格", "费用", "预算", "多钱", "贵不贵", "划算"],
    "产品推荐": ["推荐", "怎么选", "适合", "哪个好", "选哪个", "选什么", "有啥推荐"],
    "公司介绍": ["公司", "品牌", "你们是谁", "案例", "哪家", "厂家", "厂商"],
    "产品咨询": ["型号", "参数", "规格", "这款", "这款怎么样", "区别", "对比", "材质", "厚度", "隔音", "防水", "抗风", "保温", "效果"],
}

# 规则优先级（用于 rule_hits 顺序，不用于互斥）
RULE_ORDER = ["价格咨询", "产品推荐", "产品咨询", "公司介绍"]


def rule_based_intent_tagging(cleaned_prompt: str) -> RuleIntentsOutput:
    """
    对清洗后的 prompt 做规则匹配，命中即加入 rule_intents，允许多意图。
    返回 rule_intents（去重、保持顺序）和 rule_hits（各意图命中的片段）。
    """
    rule_intents: list[str] = []
    rule_hits: dict[str, Any] = {}

    if not cleaned_prompt or not cleaned_prompt.strip():
        return {"rule_intents": [], "rule_hits": {}}

    text = cleaned_prompt.strip()
    seen: set[str] = set()

    for intent in RULE_ORDER:
        if intent not in INTENT_RULES:
            continue
        patterns = INTENT_RULES[intent]
        hits: list[str] = []
        for p in patterns:
            if p in text:
                hits.append(p)
            else:
                # 支持简单正则（仅 \w 等）
                try:
                    if re.search(re.escape(p), text):
                        hits.append(p)
                except re.error:
                    pass
        if hits:
            rule_hits[intent] = hits
            if intent not in seen:
                seen.add(intent)
                rule_intents.append(intent)

    return {"rule_intents": rule_intents, "rule_hits": rule_hits}
