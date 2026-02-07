INTENT_LABELS = [
    "Product Consultation",
    "Product Recommendation",
    "Price Consultation",
    "Company Introduction",
    "Others",
]
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
from openai import OpenAI
import json

client = OpenAI()

INTENT_LABELS = [
    "Product Consultation",
    "Product Recommendation",
    "Price Consultation",
    "Company Introduction",
    "Others",
]

SYSTEM_PROMPT = INTENT_SYSTEM_PROMPT.format(
    labels="\n".join(f"- {l}" for l in INTENT_LABELS)
)


def get_intent(text: str) -> dict:
    """
    使用 GPT 进行意图识别
    返回结构化结果，适合 agent / router 使用
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",  # intent 用 mini 就够了，快 + 便宜
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        temperature=0,  # 🔒 保证稳定
    )

    content = response.choices[0].message.content.strip()

    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        # fallback：防止模型发疯
        return {
            "intent": "Others",
            "confidence": 0.0,
            "reason": "Failed to parse model output"
        }

    return result

if __name__ == "__main__":
    print("GPT Intent Classifier ready.")

    text = "Any window for windy areas?"
    res = get_intent(text)

    print(res)
