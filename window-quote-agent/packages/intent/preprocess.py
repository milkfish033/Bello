"""
Step 1：Preprocess（文本清洗）
职责：仅做规范化，不做语义判断。
- 全角 → 半角
- 合并重复标点
- 去除口语/语气词
- 保留 raw_prompt
"""
import re
import unicodedata

from packages.intent.schemas import PreprocessOutput


# 口语/语气词（非穷举，可配置扩展）
FILLER_WORDS = frozenset({
    "啊", "呀", "呢", "吧", "哦", "噢", "嗯", "哈", "嘿", "哎",
    "那个", "这个", "就是", "然后", "就是说", "就是说呢", "怎么说呢",
})


def _full_to_half(text: str) -> str:
    """全角转半角。"""
    result = []
    for c in text:
        if ord(c) == 0x3000:  # 全角空格
            result.append(" ")
        elif 0xFF01 <= ord(c) <= 0xFF5E:
            result.append(chr(ord(c) - 0xFEE0))
        else:
            result.append(c)
    return "".join(result)


def _normalize_unicode(text: str) -> str:
    """NFKC 规范化，统一全角数字/字母等。"""
    return unicodedata.normalize("NFKC", text)


def _merge_repeated_punctuation(text: str) -> str:
    """合并重复标点（连续相同标点保留一个）。"""
    return re.sub(r"([^\w\s])\1+", r"\1", text)


def _remove_filler_words(text: str) -> str:
    """去除口语/语气词（词边界匹配，保留其它内容）。"""
    t = text
    for w in sorted(FILLER_WORDS, key=len, reverse=True):
        # 词边界：前后为空白或标点或首尾
        t = re.sub(rf"(?<!\S){re.escape(w)}(?!\S)", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def preprocess(raw_prompt: str) -> PreprocessOutput:
    """
    文本清洗：全角→半角、合并重复标点、去除语气词。
    不做语义判断，输出保留 raw_prompt 与 cleaned_prompt。
    """
    if not raw_prompt or not isinstance(raw_prompt, str):
        raw_prompt = str(raw_prompt or "")
    t = raw_prompt.strip()
    t = _normalize_unicode(t)
    t = _full_to_half(t)
    t = _merge_repeated_punctuation(t)
    t = _remove_filler_words(t)
    cleaned_prompt = t.strip()
    return {"raw_prompt": raw_prompt, "cleaned_prompt": cleaned_prompt}
