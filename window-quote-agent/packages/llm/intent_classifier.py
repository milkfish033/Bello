"""
用户意图分类：通过调用外部小模型对用户消息做 chat / quote 二分类。
预留外部模型调用位置，便于接入独立意图模型 API。
"""
import json
import re
from typing import Callable

# ---------------------------------------------------------------------------
# 预留：调用外部小模型的位置
# ---------------------------------------------------------------------------
# 可在此处或通过环境变量配置外部意图模型地址，例如：
# INTENT_MODEL_BASE_URL=http://localhost:8001
# INTENT_MODEL_PATH=/v1/classify 或 /intent


def call_external_small_model(user_message: str) -> str:
    """
    调用外部小模型进行意图分类。
    此处为预留实现位：接入真实 API 后，应在此发起 HTTP 请求并返回模型原始输出。

    预期行为：
    - 输入：用户最新一条消息（user_message）
    - 输出：模型返回的原始字符串，建议为 JSON，如 {"intent": "quote"} 或 {"intent": "chat"}

    接入示例（取消注释并配置后使用）：
        import os
        import httpx
        base_url = os.getenv("INTENT_MODEL_BASE_URL", "").rstrip("/")
        path = os.getenv("INTENT_MODEL_PATH", "/v1/classify")
        if base_url:
            r = httpx.post(f"{base_url}{path}", json={"text": user_message}, timeout=5.0)
            r.raise_for_status()
            return r.text  # 或 r.json() 再序列化
        return _fallback_intent_response()
    """
    # TODO: 在此实现真实调用，例如 httpx.post(INTENT_MODEL_URL, json={"text": user_message})
    _ = user_message  # 避免未使用参数告警
    return _fallback_intent_response()


def _fallback_intent_response() -> str:
    """未配置外部模型时的默认返回，保证下游解析不报错。"""
    return '{"intent": "quote"}'


def parse_intent_from_response(response: str) -> str:
    """从模型返回的字符串中解析出 intent，仅允许 "chat" | "quote"。"""
    text = (response or "").strip()
    if "```json" in text:
        text = re.sub(r"^.*?```json\s*", "", text)
    if "```" in text:
        text = re.sub(r"\s*```.*$", "", text)
    try:
        data = json.loads(text)
        intent = data.get("intent", "quote")
        return intent if intent in ("chat", "quote") else "quote"
    except (json.JSONDecodeError, TypeError):
        return "quote"


def classify_intent(user_message: str) -> str:
    """
    对用户消息做意图分类，返回 "chat" 或 "quote"。
    内部调用预留的 call_external_small_model(user_message)，再解析结果。
    """
    raw = call_external_small_model(user_message)
    return parse_intent_from_response(raw)


def create_intent_classifier(
    external_call: Callable[[str], str] | None = None,
) -> Callable[[str], str]:
    """
    返回意图分类函数 (user_message: str) -> "chat" | "quote"。
    若传入 external_call，则用其替代默认的 call_external_small_model，便于测试或切换实现。
    """
    if external_call is not None:
        def _classify(msg: str) -> str:
            return parse_intent_from_response(external_call(msg))
        return _classify
    return classify_intent
