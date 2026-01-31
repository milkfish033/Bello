"""
Step 3：不确定性分类器（抽象接口）
触发条件：rule_intents 为空，或规则命中不足以决策（可选）。
决策策略：confidence < τ → intent = 其他；支持返回多意图。
"""
from abc import ABC, abstractmethod
from typing import Any, TypedDict

from packages.intent.schemas import INTENTS


class UncertaintyClassifierResult(TypedDict, total=False):
    """不确定性分类器 predict 返回结构。"""
    intents: list[str]   # 1~N
    confidence: float    # 0~1
    top_k: list[tuple[str, float]]  # [(intent, prob), ...]


class UncertaintyClassifier(ABC):
    """不确定性分类器抽象接口：仅用于规则未覆盖或不确定样本。"""

    @abstractmethod
    def predict(self, text: str) -> UncertaintyClassifierResult:
        """
        对文本做多意图预测。
        - intents: 1~N 个意图标签
        - confidence: 0~1
        - top_k: 可选，[(intent, prob), ...]
        """
        ...


class StubUncertaintyClassifier(UncertaintyClassifier):
    """
    占位实现：规则未命中时返回「其他」或简单启发。
    接入真实小模型时替换为调用 call_external_small_model 的封装。
    """
    DEFAULT_OTHER_CONFIDENCE = 0.5
    TAU = 0.6  # confidence < τ → intent = 其他

    def predict(self, text: str) -> UncertaintyClassifierResult:
        if not (text and text.strip()):
            return {
                "intents": ["其他"],
                "confidence": 0.0,
                "top_k": [("其他", 1.0)],
            }
        # TODO: 在此调用外部小模型，例如：
        # raw = call_external_small_model(text)
        # return self._parse_model_output(raw)
        return {
            "intents": ["其他"],
            "confidence": self.DEFAULT_OTHER_CONFIDENCE,
            "top_k": [("其他", self.DEFAULT_OTHER_CONFIDENCE)],
        }

    def predict_with_threshold(
        self, text: str, tau: float | None = None
    ) -> UncertaintyClassifierResult:
        """带阈值：confidence < τ 时强制 intents = ["其他"]。"""
        tau = tau if tau is not None else self.TAU
        out = self.predict(text)
        confidence = out.get("confidence", 0.0)
        intents = list(out.get("intents", []))
        if confidence < tau or not intents:
            intents = ["其他"]
        return {
            "intents": intents,
            "confidence": confidence,
            "top_k": out.get("top_k", [("其他", 1.0)]),
        }
