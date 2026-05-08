from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

from src.evaluation.sample_artifacts import write_sample_artifact


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Write a sample paper artifact for evaluation smoke tests."
    )

    parser.add_argument(
        "--output",
        required=True,
        help="Path where the sample paper artifact JSON should be written.",
    )

    parser.add_argument(
        "--publishable",
        action="store_true",
        help="Write a sample artifact expected to pass evaluation.",
    )

    parser.add_argument(
        "--unpublishable",
        action="store_true",
        help="Write a sample artifact expected to fail evaluation.",
    )

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.publishable and args.unpublishable:
        parser.error("Choose either --publishable or --unpublishable, not both.")

    publishable = True
    if args.unpublishable:
        publishable = False

    output_path = Path(args.output)

    written_path = write_sample_artifact(
        output_path=output_path,
        publishable=publishable,
    )

    status = "publishable" if publishable else "unpublishable"
    print(f"Wrote {status} sample artifact to: {written_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())