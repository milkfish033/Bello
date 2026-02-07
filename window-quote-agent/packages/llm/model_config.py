"""
按 intent/节点 使用不同模型的集中定义。

使用方式：
1) 环境变量：为每个「模型档位」设置 MODEL_<KEY>_BASE_URL / MODEL_<KEY>_NAME / MODEL_<KEY>_API_KEY，
   未设置时回退到 MODEL_BASE_URL / MODEL_NAME / API_KEY。
2) 非 GPT 的 LLM 节点（chat / collect_recommend_params / collect_requirements / recommend）：
   默认使用 OpenAI gpt-4o（需 OPENAI_API_KEY）；设置 LLM_BACKEND=huggingface 可改用本地 HF 模型（MODEL_ID）。
3) 构建图时：传入 chat_completions=get_all_node_chat_completions() 即可按节点用不同模型。
"""
from __future__ import annotations

import os
from typing import Any, Callable

from packages.llm.chat_completion import create_chat_completion

# 使用 LLM 的节点（与 graph.py 中 add_node 名称一致）
# 产品咨询由 chat 节点通过 RAG tool 处理，不再单独 rag_query 节点
NODES_USING_LLM = (
    "chat",                      # 其他/公司介绍/产品咨询（带 RAG tool）→ 闲聊或查资料
    "collect_recommend_params",   # 产品推荐 → 问参
    "collect_requirements",      # 价格咨询 → 采集需求
    "recommend",                 # 推荐话术（产品推荐 或 价格咨询 都会走）
)

# 节点 → 模型档位（同一档位共用 base_url/model/api_key，便于少配几组）
NODE_TO_MODEL_KEY: dict[str, str] = {
    "chat": "chat",                      # 闲聊/公司介绍/产品咨询（RAG 为 tool）
    "collect_recommend_params": "collect",
    "collect_requirements": "collect",   # 问参、采集 → 同一档
    "recommend": "qa",                   # 推荐话术
}

# 非 GPT 的 LLM 节点（chat/collect/recommend）默认用 OpenAI 跑通全流程；设为 "huggingface" 则用本地 HF 模型
LLM_BACKEND = os.environ.get("LLM_BACKEND") or os.environ.get("CHAT_BACKEND", "openai")

# 各档位未在环境变量中设置时的默认值（仅当未设 MODEL_<KEY>_* 且未设全局 MODEL_* 时用到）
MODEL_KEY_DEFAULTS: dict[str, dict[str, str]] = {
    "chat": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o",
        "api_key": "",  # 实际从 get_model_config 中读 OPENAI_API_KEY
    },
    "collect": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o",
        "api_key": "",
    },
    "qa": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o",
        "api_key": "",
    },
}


def get_model_config(model_key: str) -> dict[str, str]:
    """
    读取某模型档位的配置。优先环境变量 MODEL_<KEY>_BASE_URL / MODEL_<KEY>_NAME / MODEL_<KEY>_API_KEY，
    其次全局 MODEL_BASE_URL / MODEL_NAME / API_KEY，最后 MODEL_KEY_DEFAULTS[model_key]。
    """
    key_upper = model_key.upper()
    base_url = (
        os.environ.get(f"MODEL_{key_upper}_BASE_URL")
        or os.environ.get("MODEL_BASE_URL")
        or MODEL_KEY_DEFAULTS.get(model_key, {}).get("base_url", "http://localhost:8000/v1")
    )
    model = (
        os.environ.get(f"MODEL_{key_upper}_NAME")
        or os.environ.get("MODEL_NAME")
        or MODEL_KEY_DEFAULTS.get(model_key, {}).get("model", "deepseek-r1-lora")
    )
    api_key = (
        os.environ.get(f"MODEL_{key_upper}_API_KEY")
        or os.environ.get("API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or MODEL_KEY_DEFAULTS.get(model_key, {}).get("api_key", "dummy")
    )
    return {"base_url": base_url, "model": model, "api_key": api_key}


def get_chat_completion_for_node(node_name: str) -> Callable[..., str]:
    """按节点名返回该节点应使用的 chat_completion（由 NODE_TO_MODEL_KEY 决定档位）。"""
    if node_name not in NODE_TO_MODEL_KEY:
        raise KeyError(f"未知节点 {node_name}，需在 NODE_TO_MODEL_KEY 中定义；使用 LLM 的节点: {NODES_USING_LLM}")
    key = NODE_TO_MODEL_KEY[node_name]
    # 非 GPT 的 LLM 节点默认使用 Hugging Face 本地模型（chat/collect/recommend 统一用 MODEL_ID）
    if LLM_BACKEND.lower() == "huggingface":
        try:
            from packages.llm.hf_chat_completion import create_hf_chat_completion
        except ImportError as e:
            raise ImportError(
                "非 GPT 节点使用 Hugging Face 需安装: pip install -e \".[chat-hf]\"；"
                "或设置 LLM_BACKEND=openai 改用 OpenAI 兼容接口"
            ) from e
        model_id = os.getenv("MODEL_ID") or MODEL_KEY_DEFAULTS["chat"]["model"]
        return create_hf_chat_completion(model_id=model_id)
    cfg = get_model_config(key)
    return create_chat_completion(
        base_url=cfg["base_url"],
        model=cfg["model"],
        api_key=cfg["api_key"],
    )


def get_all_node_chat_completions() -> dict[str, Callable[..., str]]:
    """返回 节点名 -> chat_completion 的字典，供 build_quote_graph(chat_completions=...) 使用。"""
    return {node: get_chat_completion_for_node(node) for node in NODES_USING_LLM}
