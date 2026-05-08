from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Optional


def run_command(command: list[str]) -> None:
    result = subprocess.run(
        command,
        text=True,
        capture_output=True,
    )

    if result.stdout:
        print(result.stdout)

    if result.stderr:
        print(result.stderr, file=sys.stderr)

    if result.returncode != 0:
        raise RuntimeError(
            f"Verification command failed with exit code "
            f"{result.returncode}: {' '.join(command)}"
        )


def assert_exists(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Expected verification artifact missing: {path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run evaluation module verification and closeout generation."
    )

    parser.add_argument(
        "--smoke-output-dir",
        default="data/outputs/smoke_evaluation_suite",
        help="Directory where smoke suite outputs should be written.",
    )

    parser.add_argument(
        "--docs-output-dir",
        default="docs/evaluation",
        help="Directory where closeout documentation should be written.",
    )

    parser.add_argument(
        "--run-prefix",
        default="evaluation_verify",
        help="Prefix used for smoke suite run IDs.",
    )

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    smoke_output_dir = Path(args.smoke_output_dir)
    docs_output_dir = Path(args.docs_output_dir)

    run_command(
        [
            sys.executable,
            "scripts/smoke_evaluation_suite.py",
            "--output-dir",
            str(smoke_output_dir),
            "--run-prefix",
            args.run_prefix,
        ]
    )

    run_command(
        [
            sys.executable,
            "main.py",
            "--stage",
            "evaluation_closeout",
            "--output-dir",
            str(docs_output_dir),
        ]
    )

    expected_smoke_artifacts = [
        smoke_output_dir / "summary.md",
        smoke_output_dir / "passing" / "audit_report.json",
        smoke_output_dir / "passing" / "audit_summary.md",
        smoke_output_dir / "passing" / "evaluation_manifest.json",
        smoke_output_dir / "passing" / "evaluation_artifact_index.json",
        smoke_output_dir / "unpublishable" / "bad_audit_report.json",
        smoke_output_dir / "unpublishable" / "bad_audit_summary.md",
        smoke_output_dir / "unpublishable" / "bad_evaluation_manifest.json",
        smoke_output_dir / "unpublishable" / "bad_evaluation_artifact_index.json",
        smoke_output_dir / "malformed" / "validation_report.json",
        smoke_output_dir / "malformed" / "validation_summary.md",
        smoke_output_dir / "malformed" / "evaluation_artifact_index.json",
    ]

    expected_docs = [
        docs_output_dir / "evaluation_readme_section.md",
        docs_output_dir / "evaluation_architecture.md",
        docs_output_dir / "evaluation_dev_log.md",
        docs_output_dir / "evaluation_completion_checklist.md",
        docs_output_dir / "evaluation_handoff_note.md",
    ]

    for artifact in expected_smoke_artifacts + expected_docs:
        assert_exists(artifact)

    print("Evaluation module verification passed.")
    print(f"Smoke outputs: {smoke_output_dir}")
    print(f"Closeout docs: {docs_output_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
