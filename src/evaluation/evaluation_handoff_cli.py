from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

from src.evaluation.evaluation_handoff_note import write_evaluation_handoff_note


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Write a Markdown handoff note for the evaluation module."
    )

    parser.add_argument(
        "--output",
        default="docs/evaluation/evaluation_handoff_note.md",
        help="Path where the handoff note should be written.",
    )

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    written_path = write_evaluation_handoff_note(Path(args.output))

    print(f"Evaluation handoff note written to: {written_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
