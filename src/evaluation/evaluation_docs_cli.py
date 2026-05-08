from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

from src.evaluation.evaluation_readme_section import write_evaluation_readme_section


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Write README-ready evaluation documentation."
    )

    parser.add_argument(
        "--output",
        default="docs/evaluation_readme_section.md",
        help="Path where the Markdown documentation section should be written.",
    )

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    written_path = write_evaluation_readme_section(Path(args.output))

    print(f"Evaluation README section written to: {written_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
