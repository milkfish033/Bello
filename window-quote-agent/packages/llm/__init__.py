"""LLM 调用：chat_completion 等，可接微调模型；按节点用不同模型见 model_config。"""
from packages.llm.chat_completion import (
    create_chat_completion,
    create_chat_completion_from_config,
    get_chat_completion,
    MODEL_BASE_URL,
    MODEL_NAME,
    API_KEY,
)
from packages.llm.model_config import (
    NODE_TO_MODEL_KEY,
    NODES_USING_LLM,
    get_all_node_chat_completions,
    get_chat_completion_for_node,
    get_model_config,
)

try:
    from packages.llm.hf_chat_completion import create_hf_chat_completion, get_hf_chat_completion
except ImportError:
    create_hf_chat_completion = get_hf_chat_completion = None  # 未安装 transformers/torch 时

__all__ = [
    "create_chat_completion",
    "create_chat_completion_from_config",
    "get_chat_completion",
    "MODEL_BASE_URL",
    "MODEL_NAME",
    "API_KEY",
    "NODE_TO_MODEL_KEY",
    "NODES_USING_LLM",
    "get_all_node_chat_completions",
    "get_chat_completion_for_node",
    "get_model_config",
    "create_hf_chat_completion",
    "get_hf_chat_completion",
]
