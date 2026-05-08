from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

from src.evaluation.evaluation_dev_log import write_evaluation_dev_log


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Write a Markdown development log for the evaluation system."
    )

    parser.add_argument(
        "--output",
        default="docs/evaluation_dev_log.md",
        help="Path where the evaluation development log should be written.",
    )

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    written_path = write_evaluation_dev_log(Path(args.output))

    print(f"Evaluation development log written to: {written_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
