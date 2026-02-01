"""在终端或输出中查看 agent 图（无需 Jupyter）。

从项目根目录运行：
  python scripts/print_graph.py              # 终端 ASCII 图
  python scripts/print_graph.py --png        # 生成 PNG 图片，用系统看图打开
  python scripts/print_graph.py --mermaid    # 只打印 Mermaid 代码
"""
import argparse
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

DEFAULT_PNG_PATH = root / "agent_graph.png"


def _mock_chat(_messages):
    return ""


def _mock_retrieve(_query):
    return []


def _mock_list_series():
    return [{"id": "65", "name": "65系列"}]


def _mock_calculate_price(_req, _sel):
    return {"total": 0, "breakdown": [], "series_id": ""}


def main():
    parser = argparse.ArgumentParser(description="打印报价 Agent 的 LangGraph 图")
    parser.add_argument("--mermaid", action="store_true", help="只输出 Mermaid 图代码")
    parser.add_argument("--png", action="store_true", help="生成 PNG 图片（可指定路径，默认 agent_graph.png）")
    parser.add_argument("-o", "--output", default=None, help="PNG 输出路径（与 --png 一起用）")
    args = parser.parse_args()

    from packages.agent.graph import build_quote_graph

    graph = build_quote_graph(
        chat_completion=_mock_chat,
        retrieve=_mock_retrieve,
        list_series=_mock_list_series,
        calculate_price=_mock_calculate_price,
    )
    g = graph.get_graph()

    if args.mermaid:
        try:
            mermaid_code = g.draw_mermaid()
            print(mermaid_code)
        except Exception as e:
            print("Mermaid 输出失败（可能需更新 langgraph）:", e, file=sys.stderr)
            sys.exit(1)
        return

    if args.png:
        out_path = Path(args.output) if args.output else DEFAULT_PNG_PATH
        try:
            png_bytes = g.draw_mermaid_png()
            out_path.write_bytes(png_bytes)
            print("已保存:", out_path.resolve())
        except Exception as e:
            print("PNG 生成失败:", e, file=sys.stderr)
            sys.exit(1)
        return

    print("=== Agent 图 (ASCII) ===\n")
    try:
        g.print_ascii()
    except Exception as e:
        print("print_ascii 失败:", e, file=sys.stderr)
        print("可尝试: python scripts/print_graph.py --mermaid 或 --png", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
