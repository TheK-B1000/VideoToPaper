#!/usr/bin/env python3
"""
Run the full local pipeline from a YouTube URL through HTML paper assembly.

Prefer ``main.py --stage youtube_paper --youtube-url ...`` (same implementation).

Usage (from repo root)::

    python scripts/run_youtube_to_paper.py --youtube-url \"https://youtu.be/VIDEO_ID\"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="VideoToPaper: YouTube URL → full inquiry HTML paper (local run).",
    )
    parser.add_argument(
        "--youtube-url",
        required=True,
        help="Any supported YouTube URL or short link (youtu.be).",
    )
    parser.add_argument(
        "--config-path",
        default="configs/argument_config.json",
        help="Argument / budget / evidence_retrieval config (default: configs/argument_config.json).",
    )
    parser.add_argument(
        "--speaker-name",
        default=None,
        help="Optional speaker label (default: channel name from yt-dlp).",
    )
    parser.add_argument(
        "--audit-after-assembly",
        action="store_true",
        help=(
            "Run the Week 8 HTML audit after assembly. "
            "If timing/embed checks fail, the script exits non-zero."
        ),
    )
    args = parser.parse_args(argv)

    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))

    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, OSError):
        pass

    from src.pipelines.run_youtube_paper_pipeline import run_youtube_paper_pipeline

    return run_youtube_paper_pipeline(
        repo_root=REPO_ROOT,
        youtube_url=args.youtube_url.strip(),
        config_path=args.config_path,
        speaker_name=args.speaker_name,
        audit_after_assembly=args.audit_after_assembly,
    )


if __name__ == "__main__":
    raise SystemExit(main())
