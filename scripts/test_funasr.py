#!/usr/bin/env python3
"""阶段 2 验证脚本：不依赖 ROS 2，直接用 FunASR 把一个 wav 转成中文。

在 Ubuntu 26.04 虚拟机里、已激活虚拟环境的前提下：

    python3 scripts/test_funasr.py
    python3 scripts/test_funasr.py --audio samples/test_long.wav --output outputs/result.txt
    python3 scripts/test_funasr.py --no-punc          # 只要纯文字，加载更快
    python3 scripts/test_funasr.py --model-path models/asr/paraformer-local

首次运行会联网下载 paraformer-zh / fsmn-vad / ct-punc 权重（约 1GB）。
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src" / "ai_asr"))

from ai_asr.funasr_engine import FunAsrEngine, probe_wav  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FunASR 离线中文识别自测")
    parser.add_argument("--audio", default=str(PROJECT_ROOT / "samples" / "test.wav"))
    parser.add_argument("--model", default="paraformer-zh")
    parser.add_argument("--model-path", default="", help="本地模型目录，优先于 --model")
    parser.add_argument(
        "--cache-dir",
        default=str(PROJECT_ROOT / "models" / "asr"),
        help="权重缓存目录（写入 MODELSCOPE_CACHE）",
    )
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--batch-size-s", type=float, default=300.0)
    parser.add_argument("--hotword", default="")
    parser.add_argument("--output", default="", help="把识别文字另存到该文件")
    parser.add_argument("--no-vad", action="store_true", help="不使用 fsmn-vad 分段")
    parser.add_argument("--no-punc", action="store_true", help="不使用 ct-punc 加标点")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audio_path = os.path.abspath(os.path.expanduser(args.audio))

    if not os.path.exists(audio_path):
        print(f"[error] 找不到音频文件: {audio_path}")
        return 1

    info = probe_wav(audio_path)
    print(
        f"[audio] {audio_path}\n        {info['sample_rate']}Hz / {info['channels']}声道 / "
        f"{info['bit_depth']}bit / {info['duration']:.2f}s"
    )

    engine = FunAsrEngine(
        model=args.model,
        model_path=args.model_path,
        use_vad=not args.no_vad,
        use_punc=not args.no_punc,
        device=args.device,
        cache_dir=args.cache_dir,
    )

    started = time.perf_counter()
    text, elapsed = engine.recognize(
        audio_path, batch_size_s=args.batch_size_s, hotword=args.hotword
    )
    total = time.perf_counter() - started

    print(f"[load ] {engine.load_seconds:.1f}s（含首次下载权重则更久）")
    print(f"[infer] {elapsed:.2f}s  RTF={elapsed / max(info['duration'], 1e-6):.3f}")
    print(f"[total] {total:.1f}s")
    print(f"[text ] {text}")

    if args.output:
        output_path = os.path.abspath(os.path.expanduser(args.output))
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        Path(output_path).write_text(text, encoding="utf-8")
        print(f"[save ] {output_path}")

    return 0 if text else 2


if __name__ == "__main__":
    raise SystemExit(main())
