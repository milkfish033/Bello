#!/usr/bin/env python3
"""
诊断测试卡死：用超时跑 pytest，卡住时会在超时后报出具体用例名。

用法（在项目根目录）:
  .venv/bin/python scripts/diagnose_tests.py
  .venv/bin/python scripts/diagnose_tests.py tests/test_graph.py

依赖: pip install pytest-timeout（或 uv add -d pytest-timeout）
若未安装 timeout，会普通跑一遍；若安装则每用例 30s 超时，超时即显示卡住的用例。

常见卡住原因:
- check / router 节点在 OPENAI_API_KEY 已设置时调用真实 API（网络慢会卡住）
  已做：无有效 API key 时自动走 fallback，不发起请求。
- test_intent_pipeline 中规则未命中且用真实 GPT 模型（会调用 OpenAI API）
  建议：保持使用 StubUncertaintyClassifier 的用例即可。
"""
import os
import subprocess
import sys

def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    test_paths = sys.argv[1:] if len(sys.argv) > 1 else ["tests/"]
    cmd = [sys.executable, "-m", "pytest"] + test_paths + ["-v", "--tb=short"]
    try:
        import pytest_timeout  # noqa: F401
        cmd.append("--timeout=30")
        print("使用 30s 超时；卡住时会报出用例名。\n", flush=True)
    except ImportError:
        print("未安装 pytest-timeout，按普通方式运行（无超时）。安装后可定位卡住用例: pip install pytest-timeout\n", flush=True)
    for path in test_paths:
        print(f">>> pytest {path} -v\n", flush=True)
    ret = subprocess.run(cmd, cwd=root)
    if ret.returncode != 0:
        print("\n若因超时失败，最后打印的 FAILED 用例即为卡住的那一步。", flush=True)
    sys.exit(ret.returncode)

if __name__ == "__main__":
    main()
