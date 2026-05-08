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
        "--export-smoke-output-dir",
        default="data/outputs/smoke_export_and_evaluate",
        help="Directory where export-and-evaluate smoke outputs should be written.",
    )

    parser.add_argument(
        "--run-prefix",
        default="evaluation_verify",
        help="Prefix used for smoke suite run IDs.",
    )

    parser.add_argument(
        "--status-output",
        default=None,
        help="Optional path where evaluation module status Markdown should be written.",
    )

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    smoke_output_dir = Path(args.smoke_output_dir)
    docs_output_dir = Path(args.docs_output_dir)
    export_smoke_output_dir = Path(args.export_smoke_output_dir)

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
            "scripts/smoke_export_and_evaluate.py",
            "--output-dir",
            str(export_smoke_output_dir),
            "--run-id",
            f"{args.run_prefix}_export_eval",
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
    expected_export_smoke_artifacts = [
        export_smoke_output_dir / "claims.json",
        export_smoke_output_dir / "speaker_perspective.json",
        export_smoke_output_dir / "adjudications.json",
        export_smoke_output_dir / "evidence_records.json",
        export_smoke_output_dir / "paper_artifact.json",
        export_smoke_output_dir / "audit_report.json",
        export_smoke_output_dir / "audit_summary.md",
        export_smoke_output_dir / "evaluation_manifest.json",
        export_smoke_output_dir / "evaluation_artifact_index.json",
    ]

    expected_docs = [
        docs_output_dir / "evaluation_readme_section.md",
        docs_output_dir / "evaluation_architecture.md",
        docs_output_dir / "evaluation_dev_log.md",
        docs_output_dir / "evaluation_completion_checklist.md",
        docs_output_dir / "evaluation_handoff_note.md",
    ]

    for artifact in (
        expected_smoke_artifacts + expected_export_smoke_artifacts + expected_docs
    ):
        assert_exists(artifact)

    if args.status_output:
        status_output = Path(args.status_output)
        status_output.parent.mkdir(parents=True, exist_ok=True)
        status_output.write_text(
            "\n".join(
                [
                    "# Evaluation Module Status",
                    "",
                    "Module Ready: YES",
                    "",
                    "Verified smoke outputs and closeout documentation.",
                    "",
                    "Required docs:",
                    *[
                        f"- {path.name}"
                        for path in expected_docs
                    ],
                    "",
                ]
            ),
            encoding="utf-8",
        )

    print("Evaluation module verification passed.")
    print(f"Smoke outputs: {smoke_output_dir}")
    print(f"Export smoke outputs: {export_smoke_output_dir}")
    print(f"Closeout docs: {docs_output_dir}")
    if args.status_output:
        print(f"Status report: {args.status_output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
