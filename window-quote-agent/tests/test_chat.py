import os
import torch
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    TextIteratorStreamer,
)
from threading import Thread

# =====================
# Config
# =====================
MODEL_ID = os.getenv("MODEL_ID", "Milkfish033/deepseek-r1-1.5b-merged")

SYSTEM_PROMPT = (
    "你是 Bello，一个友好的智能助手。"
    "你擅长回答与窗户产品、使用场景和选型相关的问题。"
    "请用清晰、简洁的中文回答用户问题。"
)

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
DTYPE = torch.float16 if DEVICE == "cuda" else torch.float32

# =====================
# Load model
# =====================
print("🔄 正在加载模型...")
tokenizer = AutoTokenizer.from_pretrained(
    MODEL_ID,
    trust_remote_code=True,
)

model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    torch_dtype=DTYPE,
    device_map="auto" if DEVICE == "cuda" else None,
    trust_remote_code=True,
)
model.eval()
print("✅ 模型加载完成")

# =====================
# Chat loop
# =====================
def build_prompt(messages):
    """
    根据对话历史构造 prompt
    兼容 deepseek / qwen / llama 风格
    """
    prompt = f"<|system|>\n{SYSTEM_PROMPT}\n"
    for role, content in messages:
        if role == "user":
            prompt += f"<|user|>\n{content}\n"
        else:
            prompt += f"<|assistant|>\n{content}\n"
    prompt += "<|assistant|>\n"
    return prompt


def chat():
    messages = []

    print("\n💬 Bello 已上线（输入 exit 退出）\n")

    while True:
        user_input = input("你：").strip()
        if user_input.lower() in {"exit", "quit"}:
            print("👋 再见！")
            break

        messages.append(("user", user_input))

        prompt = build_prompt(messages)

        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

        streamer = TextIteratorStreamer(
            tokenizer,
            skip_prompt=True,
            skip_special_tokens=True,
        )

        generation_kwargs = dict(
            **inputs,
            streamer=streamer,
            max_new_tokens=512,
            temperature=0.7,
            top_p=0.9,
            do_sample=True,
        )

        thread = Thread(target=model.generate, kwargs=generation_kwargs)
        thread.start()

        print("Bello：", end="", flush=True)
        assistant_output = ""
        for token in streamer:
            print(token, end="", flush=True)
            assistant_output += token
        print()

        messages.append(("assistant", assistant_output))


if __name__ == "__main__":
    chat()
