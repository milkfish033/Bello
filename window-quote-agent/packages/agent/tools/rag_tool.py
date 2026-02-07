"""RAG 检索工具：供 chat 等节点通过 tool call 调用，而非写死为独立节点。"""
import json
from pathlib import Path
from typing import Any, Callable, List

from langchain_core.documents import Document
from langchain_core.tools import tool
from langchain_community.retrievers import BM25Retriever

# 1) Load docs from JSON（相对包路径，便于移植）
_json_path = Path(__file__).resolve().parent.parent.parent / "rag" / "brochure" / "product_cards_merged.json"
if _json_path.exists():
    with open(_json_path, "r", encoding="utf-8") as f:
        _items = json.load(f)
else:
    _items = []

_items = _items if isinstance(_items, list) else []

docs = [
    Document(
        page_content=item.get("text", ""),
        metadata={
            "model": item.get("model", ""),
            "pages": item.get("pages", []),
            "source": "brochure",
        },
    )
    for item in _items
]

# 2) Build a BM25 retriever（无文档时仅返回空列表）
bm25: Any = None
if docs:
    bm25 = BM25Retriever.from_documents(docs)
    bm25.k = 3  # top-k, 可调


def bm25_retrieve(query: str) -> List[str]:
    """Return top-k chunks as strings (with metadata header).供 graph 在未传入 retrieve 时使用。"""
    if not bm25:
        return []

    q = (query or "").strip() or "窗户 型材 产品"

    # ✅ BM25Retriever 是 Runnable，用 invoke
    results = bm25.invoke(q)

    out: List[str] = []
    for d in results[: getattr(bm25, "k", 3)]:
        model = d.metadata.get("model", "")
        pages = d.metadata.get("pages", [])
        header = f"[model={model} | pages={pages}]"
        out.append(header + "\n" + d.page_content)

    return out


def create_rag_tool(retrieve: Callable[[str], List[str]]) -> Any:
    """
    根据 retrieve 构造一个 LangChain Tool，供 LLM 在需要查产品资料时调用。
    - name/description 供模型决定是否调用；
    - 调用时传入 query，返回拼接后的参考资料文本。
    """
    retrieve_fn = retrieve

    @tool
    def product_knowledge_search(query: str) -> str:
        """在门窗产品资料库中检索与问题相关的参考资料。当用户询问产品规格、型号、材质、区别、推荐等问题时调用此工具。"""
        chunks = retrieve_fn((query or "").strip())
        if not chunks:
            return "（无相关检索结果）"
        return "\n\n".join(chunks)

    product_knowledge_search.name = "product_knowledge_search"
    product_knowledge_search.description = (
        "在门窗产品资料库中检索与用户问题相关的参考资料。"
        "当用户询问产品规格、型号、材质、系列区别、推荐等问题时调用。"
    )
    return product_knowledge_search


# 3) Create the tool you will pass into your agent
product_knowledge_tool = create_rag_tool(bm25_retrieve)
