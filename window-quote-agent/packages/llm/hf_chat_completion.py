"""
Chat completion：使用本地 Hugging Face 模型（transformers），供 chat 节点使用。

环境变量：
- MODEL_ID：模型 ID，默认 Milkfish033/deepseek-r1-1.5b-merged
- CHAT_MODEL_ID：chat 节点专用覆盖（可选）

调用方式与 chat_completion 一致：chat_completion(messages: list[dict]) -> str
"""
from __future__ import annotations

import os
from typing import Any, Callable

_MODEL: Any = None
_TOKENIZER: Any = None


def _load_model(model_id: str | None = None) -> tuple[Any, Any]:
    """懒加载模型与 tokenizer，全局单例。"""
    global _MODEL, _TOKENIZER
    if _MODEL is not None and _TOKENIZER is not None:
        return _MODEL, _TOKENIZER

    model_id = model_id or os.getenv("CHAT_MODEL_ID") or os.getenv("MODEL_ID", "Milkfish033/deepseek-r1-1.5b-merged")

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    _TOKENIZER = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    _MODEL = AutoModelForCausalLM.from_pretrained(
        model_id,
        dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto" if torch.cuda.is_available() else None,
        trust_remote_code=True,
    )
    _MODEL.eval()
    return _MODEL, _TOKENIZER


def _generate(messages: list[dict[str, Any]], *, model: Any, tokenizer: Any, max_new_tokens: int = 1024) -> str:
    """将 messages 转为 prompt 并生成回复。"""
    import torch

    if hasattr(tokenizer, "apply_chat_template"):
        # DeepSeek R1 等：使用 chat template
        try:
            text = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
        except TypeError:
            text = tokenizer.apply_chat_template(messages, tokenize=False)
    else:
        # 兼容无 chat_template 的模型：简单拼接
        text = ""
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role == "system":
                text += f"System: {content}\n\n"
            elif role == "user":
                text += f"User: {content}\n\n"
            elif role == "assistant":
                text += f"Assistant: {content}\n\n"
        text += "Assistant: "

    inputs = tokenizer(text, return_tensors="pt").to(model.device)
    input_len = inputs["input_ids"].shape[1]

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id or tokenizer.pad_token_id,
        )

    # 只解码新生成部分
    new_tokens = outputs[0][input_len:]
    return tokenizer.decode(new_tokens, skip_special_tokens=True).strip()


def create_hf_chat_completion(
    *,
    model_id: str | None = None,
    max_new_tokens: int = 1024,
) -> Callable[..., str]:
    """
    返回符合 agent 约定的 chat_completion(messages) -> str。
    使用 Hugging Face transformers 本地推理。
    """
    model, tokenizer = _load_model(model_id)

    def chat_completion(messages: list[dict[str, Any]], **kwargs: Any) -> str:
        return _generate(messages, model=model, tokenizer=tokenizer, max_new_tokens=max_new_tokens)

    return chat_completion


def get_hf_chat_completion() -> Callable[..., str]:
    """返回默认 HF chat_completion（懒加载，读 MODEL_ID / CHAT_MODEL_ID）。"""
    return create_hf_chat_completion()
