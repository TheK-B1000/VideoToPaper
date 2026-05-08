from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

from src.evaluation.evaluation_completion_checklist import (
    write_evaluation_completion_checklist,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Write a Markdown completion checklist for the evaluation module."
    )

    parser.add_argument(
        "--output",
        default="docs/evaluation_completion_checklist.md",
        help="Path where the completion checklist should be written.",
    )

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    written_path = write_evaluation_completion_checklist(Path(args.output))

    print(f"Evaluation completion checklist written to: {written_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
