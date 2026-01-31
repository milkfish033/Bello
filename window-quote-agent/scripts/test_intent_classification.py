#!/usr/bin/env python3
"""
意图分类测试脚本：运行 Prompt 清洗 + 多意图识别流水线，打印结构化输出。

用法（在 window-quote-agent 根目录）：
  PYTHONPATH=. python scripts/test_intent_classification.py
  PYTHONPATH=. python scripts/test_intent_classification.py "我想报价"
  PYTHONPATH=. python scripts/test_intent_classification.py --stub   # 仅 Stub，不加载模型

规则未命中时的分类方式：
  默认：facebook/bart-large-mnli 零样本分类（需 pip install transformers torch）。
  --stub：不加载模型，规则未命中时返回「其他」。
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.intent import (
    run_intent_pipeline,
    RealZeroShotClassifier,
    StubUncertaintyClassifier,
)


SAMPLE_PROMPTS = [
    "今天风很大，窗户很晃，有没有抗风性好点的窗户？",
    "有没有隔音效果好的窗户？",
    "有没有防水性好的窗户？",
    "我想报价，多少钱一平",
    "推荐一款适合的，顺便报个价",
    "你们公司是做什么的",
    "这款型号参数和规格怎么样",
    "今天天气不错",
    "那个 就是 帮我 报个价 啊",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="测试意图分类流水线")
    parser.add_argument(
        "prompt",
        nargs="?",
        default=None,
        help="用户输入（不传则跑内置多组样例）",
    )
    parser.add_argument(
        "--stub",
        action="store_true",
        help="仅用 Stub（规则未命中返回「其他」，不加载模型）",
    )
    parser.add_argument(
        "--tau",
        type=float,
        default=0.6,
        help="置信度阈值，低于此值归为「其他」（默认 0.6）",
    )
    args = parser.parse_args()

    if args.stub:
        classifier = StubUncertaintyClassifier()
        print("使用 StubUncertaintyClassifier（规则未命中时返回「其他」）\n")
    else:
        classifier = RealZeroShotClassifier()
        print("使用 RealZeroShotClassifier（facebook/bart-large-mnli）\n")

    prompts = [args.prompt] if args.prompt else SAMPLE_PROMPTS

    for i, raw in enumerate(prompts, 1):
        print("=" * 60)
        print(f"[{i}] 用户输入: {raw!r}")
        print("-" * 60)
        out = run_intent_pipeline(
            raw,
            uncertainty_classifier=classifier,
            use_model_when_rules_empty=True,
            tau=args.tau,
        )
        print(f"  原始:     {out['raw_prompt']!r}")
        print(f"  清洗后:   {out['cleaned_prompt']!r}")
        print(f"  意图:     {out['intents']}")
        print(f"  主意图:   {out['primary_intent']}")
        print(f"  次意图:   {out['secondary_intents']}")
        print(f"  置信度:   {out['confidence']:.2f}")
        print(f"  来源:     {out['source']} (rule=规则, model=模型)")
        print(f"  任务拆分: {out['tasks']}")
        print()
    print("=" * 60)
    print("完成")


if __name__ == "__main__":
    main()
