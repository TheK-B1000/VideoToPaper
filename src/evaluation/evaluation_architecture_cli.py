from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

from src.evaluation.evaluation_architecture_doc import (
    write_evaluation_architecture_doc,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Write a Markdown architecture document for the evaluation module."
    )

    parser.add_argument(
        "--output",
        default="docs/evaluation_architecture.md",
        help="Path where the architecture document should be written.",
    )

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    written_path = write_evaluation_architecture_doc(Path(args.output))

    print(f"Evaluation architecture document written to: {written_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
