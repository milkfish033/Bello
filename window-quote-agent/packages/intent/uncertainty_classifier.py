from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypedDict

from packages.intent.schemas import INTENTS

# BART-large-mnli 在英文上训练，用英文标签效果更好；输出时映射回中文
BART_LABEL_TO_INTENT: dict[str, str] = {
    "Product Consultation": "产品咨询",
    "Product Recommendation": "产品推荐",
    "Price Consultation": "价格咨询",
    "Company Introduction": "公司介绍",
    "Others": "其他",
}
CANDIDATE_LABELS_EN = list(BART_LABEL_TO_INTENT)


class UncertaintyClassifierResult(TypedDict, total=False):
    """不确定性分类器 predict 返回结构。"""
    intents: list[str]                 # 1~N
    confidence: float                  # 0~1
    top_k: list[tuple[str, float]]     # [(intent, prob), ...]


class UncertaintyClassifier(ABC):
    """不确定性分类器抽象接口：仅用于规则未覆盖或不确定样本。"""

    @abstractmethod
    def predict(self, text: str) -> UncertaintyClassifierResult:
        ...


class RealZeroShotClassifier(UncertaintyClassifier):
    """基于 facebook/bart-large-mni 的零样本分类器。"""

    def __init__(self, model_path: str = "facebook/bart-large-mnli"):
        from transformers import pipeline
        self._classifier = pipeline("zero-shot-classification", model=model_path)

    def predict(self, text: str) -> UncertaintyClassifierResult:
        result = self._classifier(text, CANDIDATE_LABELS_EN)
        labels_zh = [BART_LABEL_TO_INTENT.get(l, "其他") for l in result["labels"]]
        scores = result["scores"]
        return {
            "intents": labels_zh,
            "confidence": scores[0],
            "top_k": list(zip(labels_zh, scores)),
        }


class StubUncertaintyClassifier(UncertaintyClassifier):
    """占位分类器：规则未命中时返回「其他」，不加载模型。"""

    def predict(self, text: str) -> UncertaintyClassifierResult:
        return {
            "intents": ["其他"],
            "confidence": 0.0,
            "top_k": [("其他", 0.0)],
        }
