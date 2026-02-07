from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import TypedDict

# GPT 使用英文标签，输出时映射回中文（与 test_qwen 一致）
INTENT_LABELS_EN = [
    "Product Consultation",
    "Product Recommendation",
    "Price Consultation",
    "Company Introduction",
    "Others",
]
LABEL_EN_TO_ZH: dict[str, str] = {
    "Product Consultation": "产品咨询",
    "Product Recommendation": "产品推荐",
    "Price Consultation": "价格咨询",
    "Company Introduction": "公司介绍",
    "Others": "其他",
}

INTENT_SYSTEM_PROMPT = """You are an intent classification engine.
Your task is to classify the user's message into ONE of the following intents:

{labels}

Rules:
- Choose exactly ONE intent from the list
- Return a JSON object ONLY
- Include a confidence score between 0 and 1
- Briefly explain the reason

Output format:
{{
  "intent": "<one of the labels>",
  "confidence": <float>,
  "reason": "<short explanation>"
}}
"""


class UncertaintyClassifierResult(TypedDict, total=False):
    """不确定性分类器 predict 返回结构。"""
    intents: list[str]  # 1~N
    confidence: float


class UncertaintyClassifier(ABC):
    """不确定性分类器抽象接口：仅用于规则未覆盖或不确定样本。"""

    @abstractmethod
    def predict(self, text: str) -> UncertaintyClassifierResult:
        ...


class GptMiniUncertaintyClassifier(UncertaintyClassifier):
    """基于 OpenAI gpt-4o-mini 的意图分类器（与 test_qwen 调用方式一致）。"""

    def __init__(self, model: str = "gpt-4o-mini"):
        from openai import OpenAI
        self._client = OpenAI()
        self._model = model
        self._system_prompt = INTENT_SYSTEM_PROMPT.format(
            labels="\n".join(f"- {l}" for l in INTENT_LABELS_EN)
        )

    def predict(self, text: str) -> UncertaintyClassifierResult:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": self._system_prompt},
                {"role": "user", "content": text},
            ],
            temperature=0,
        )
        content = (response.choices[0].message.content or "").strip()
        try:
            data = json.loads(content)
            intent_en = data.get("intent", "Others")
            confidence = float(data.get("confidence", 0.0))
            intent_zh = LABEL_EN_TO_ZH.get(intent_en, "其他")
            return {"intents": [intent_zh], "confidence": confidence}
        except (json.JSONDecodeError, TypeError):
            return {"intents": ["其他"], "confidence": 0.0}


class StubUncertaintyClassifier(UncertaintyClassifier):
    """占位分类器：规则未命中时返回「其他」，不加载模型。"""

    def predict(self, text: str) -> UncertaintyClassifierResult:
        return {"intents": ["其他"], "confidence": 0.0}
