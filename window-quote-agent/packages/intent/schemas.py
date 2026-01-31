"""多意图流水线结构化输出 Schema。"""
from typing import Any, TypedDict

# 意图集合（与设计一致）
INTENTS = ("产品咨询", "产品推荐", "价格咨询", "公司介绍", "其他")

# 主次意图优先级（用于任务编排）：价格咨询 > 产品推荐 > 产品咨询 > 公司介绍 > 其他
INTENT_PRIORITY = ("价格咨询", "产品推荐", "产品咨询", "公司介绍", "其他")


class PreprocessOutput(TypedDict):
    """Step 1 输出。"""
    raw_prompt: str
    cleaned_prompt: str


class RuleIntentsOutput(TypedDict):
    """Step 2 输出。"""
    rule_intents: list[str]
    rule_hits: dict[str, Any]


class TaskItem(TypedDict):
    """多意图拆分后的单任务。"""
    intent: str
    description: str


class IntentPipelineOutput(TypedDict, total=False):
    """最终结构化输出，供后续 agent 使用。"""
    raw_prompt: str
    cleaned_prompt: str
    intents: list[str]
    primary_intent: str
    secondary_intents: list[str]
    tasks: list[TaskItem]
    confidence: float
    source: str  # "rule" | "model"
