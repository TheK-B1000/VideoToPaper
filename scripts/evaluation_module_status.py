from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional


REQUIRED_EVALUATION_FILES = (
    "src/evaluation/evaluation_readme_section.py",
    "src/evaluation/evaluation_architecture_doc.py",
    "src/evaluation/evaluation_dev_log.py",
    "src/evaluation/evaluation_completion_checklist.py",
    "src/evaluation/evaluation_closeout_bundle.py",
    "src/evaluation/evaluation_handoff_note.py",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check whether evaluation module closeout files are present."
    )
    parser.add_argument(
        "--base-dir",
        default=".",
        help="Repository root to evaluate.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    base_dir = Path(args.base_dir)
    missing: list[str] = []

    print("Evaluation module status:")
    for relative_path in REQUIRED_EVALUATION_FILES:
        target = base_dir / relative_path
        exists = target.exists()
        label = "OK" if exists else "MISSING"
        print(f"- [{label}] {relative_path}")
        if not exists:
            missing.append(relative_path)

    if missing:
        print("Evaluation module status: incomplete")
        return 1

    print("Evaluation module status: complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
