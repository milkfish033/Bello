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


SYN_MAP = {
    # 结构与安全
    "晃动": "不稳定", "摇晃": "不稳定", "松动": "不稳定", "不稳": "不稳定",
    "掉下去": "坠落风险", "小孩爬": "安全防范", "防盗": "防撬性能",
    "变形": "型材挠度过大", "弯了": "型材变形", "玻璃碎": "钢化玻璃自爆",
    "小孩": "安全防范", "孩子": "安全防范",
    
    # 环境与气密性 (性能三性)
    "漏风": "密封性差", "进风": "密封性差", "漏水": "水密性失效",
    "渗水": "水密性失效", "飘雨": "水密性失效", "刮风": "大风",
    "风很大": "大风", "台风": "大风", "很晒": "紫外线阻隔",
    "不隔热": "隔热性能差", "冒汗": "冷凝结露", "起雾": "冷凝结露",
    
    # 噪音与异响
    "一直响": "噪音", "蝉鸣声": "噪音", "哨音": "噪音",
    "隔音不好": "隔音性能差", "外面声音大": "噪音",
    
    # 五金与操作
    "推不动": "启闭障碍", "卡住了": "启闭障碍", "关不严": "锁闭失效",
    "把手松": "五金件松动", "生锈": "五金件腐蚀", "把手断了": "执手损坏",
    
    # 玻璃与遮阳
    "看不见里面": "隐私保护", "反光": "镀膜玻璃", "遮光": "中空百叶",
    "遥控": "电动开窗器", "智能窗": "电动智能控制"
}


def map(text: str) -> str:
    """将口语化表述转化为专业术语"""
    for k, v in SYN_MAP.items():
        text.replace(k, v)
    return text 



def preprocess(raw_prompt: str) -> PreprocessOutput:
    """
    文本清洗：全角→半角、合并重复标点、去除语气词, 映射专业术语。
    不做语义判断，输出保留 raw_prompt 与 cleaned_prompt。
    """
    if not raw_prompt or not isinstance(raw_prompt, str):
        raw_prompt = str(raw_prompt or "")
    t = raw_prompt.strip()
    t = _normalize_unicode(t)
    t = _full_to_half(t)
    t = _merge_repeated_punctuation(t)
    t = _remove_filler_words(t)
    t = map(t)
    cleaned_prompt = t.strip()
    return {"raw_prompt": raw_prompt, "cleaned_prompt": cleaned_prompt}
