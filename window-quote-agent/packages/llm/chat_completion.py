"""
Chat completion：调用 OpenAI 兼容接口，供 agent 各节点使用。

使用实际模型的方式（任选其一）：
1) 环境变量：在 .env 中设置 MODEL_BASE_URL / MODEL_NAME / API_KEY，然后调用 get_chat_completion()。
2) 代码传入：create_chat_completion(base_url=..., model=..., api_key=...) 或 create_chat_completion_from_config(settings)。
3) API 层：用 apps.api.config.get_settings() 得到 Settings，再 create_chat_completion_from_config(s) 传入。
"""
from __future__ import annotations

import os
from typing import Any, Callable

# 从环境变量读取默认值（未设置时使用）
MODEL_BASE_URL = os.environ.get("MODEL_BASE_URL", "http://localhost:8000/v1")
MODEL_NAME = os.environ.get("MODEL_NAME", "deepseek-r1-lora")
API_KEY = os.environ.get("API_KEY", "dummy")


def _call_api(messages: list[dict[str, Any]], *, base_url: str, model: str, api_key: str) -> str:
    from openai import OpenAI

    client = OpenAI(base_url=base_url, api_key=api_key)
    resp = client.chat.completions.create(model=model, messages=messages)
    if not resp.choices:
        return ""
    return (resp.choices[0].message.content or "").strip()


def create_chat_completion(
    *,
    base_url: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
) -> Callable[..., str]:
    """
    返回符合 agent 约定的 chat_completion(messages) -> str。
    未传参数时使用环境变量 MODEL_BASE_URL / MODEL_NAME / API_KEY。
    """
    url = base_url if base_url is not None else MODEL_BASE_URL
    name = model if model is not None else MODEL_NAME
    key = api_key if api_key is not None else API_KEY

    def chat_completion(messages: list[dict[str, Any]], **kwargs: Any) -> str:
        return _call_api(messages, base_url=url, model=name, api_key=key)

    return chat_completion


def create_chat_completion_from_config(config: Any) -> Callable[..., str]:
    """
    从配置对象创建 chat_completion。支持具有 MODEL_BASE_URL / MODEL_NAME / API_KEY 属性的对象
    （如 apps.api.config.Settings 或 dict）。
    """
    if hasattr(config, "MODEL_BASE_URL"):
        base_url = getattr(config, "MODEL_BASE_URL", None)
        model = getattr(config, "MODEL_NAME", None)
        api_key = getattr(config, "API_KEY", None)
    elif isinstance(config, dict):
        base_url = config.get("MODEL_BASE_URL")
        model = config.get("MODEL_NAME")
        api_key = config.get("API_KEY")
    else:
        base_url = model = api_key = None
    return create_chat_completion(base_url=base_url, model=model, api_key=api_key)


# 默认单例，方便直接传给 build_quote_graph
_default_chat_completion: Callable[..., str] | None = None


def get_chat_completion() -> Callable[..., str]:
    """返回默认 chat_completion（懒加载，读当前环境变量）。"""
    global _default_chat_completion
    if _default_chat_completion is None:
        _default_chat_completion = create_chat_completion()
    return _default_chat_completion
