from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

from src.evaluation.evaluation_closeout_bundle import (
    write_evaluation_closeout_bundle,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Write the closeout documentation bundle for the evaluation system."
    )

    parser.add_argument(
        "--output-dir",
        default="docs/evaluation",
        help="Directory where closeout documentation should be written.",
    )

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    bundle = write_evaluation_closeout_bundle(Path(args.output_dir))

    print("Evaluation closeout bundle written:")
    for label, path in bundle.to_dict().items():
        print(f"- {label}: {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
