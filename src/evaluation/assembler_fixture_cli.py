from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

from src.evaluation.assembler_fixture_writer import write_assembler_fixtures


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Write assembler-style fixture files for export-and-evaluate tests."
    )

    parser.add_argument(
        "--output-dir",
        default="data/outputs/assembler_fixture",
        help="Directory where assembler-style fixture JSON files should be written.",
    )

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    paths = write_assembler_fixtures(Path(args.output_dir))

    print("Assembler fixtures written:")
    for label, path in paths.items():
        print(f"- {label}: {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
