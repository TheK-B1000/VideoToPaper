from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, Optional


REQUIRED_SMOKE_ARTIFACTS = [
    "summary.md",
    "passing/audit_report.json",
    "passing/audit_summary.md",
    "passing/evaluation_manifest.json",
    "passing/evaluation_artifact_index.json",
    "unpublishable/bad_audit_report.json",
    "unpublishable/bad_audit_summary.md",
    "unpublishable/bad_evaluation_manifest.json",
    "unpublishable/bad_evaluation_artifact_index.json",
    "malformed/validation_report.json",
    "malformed/validation_summary.md",
    "malformed/evaluation_artifact_index.json",
]

REQUIRED_EXPORT_SMOKE_ARTIFACTS = [
    "claims.json",
    "speaker_perspective.json",
    "adjudications.json",
    "evidence_records.json",
    "paper_artifact.json",
    "audit_report.json",
    "audit_summary.md",
    "evaluation_manifest.json",
    "evaluation_artifact_index.json",
]


REQUIRED_DOC_ARTIFACTS = [
    "evaluation_readme_section.md",
    "evaluation_architecture.md",
    "evaluation_dev_log.md",
    "evaluation_completion_checklist.md",
    "evaluation_handoff_note.md",
]


def check_required_files(base_dir: Path, relative_paths: list[str]) -> Dict[str, bool]:
    return {
        relative_path: (base_dir / relative_path).exists()
        for relative_path in relative_paths
    }


def all_present(results: Dict[str, bool]) -> bool:
    return all(results.values())


def _render_checklist(results: Dict[str, bool]) -> list[str]:
    lines: list[str] = []
    for relative_path, exists in results.items():
        marker = "x" if exists else " "
        lines.append(f"- [{marker}] `{relative_path}`")
    return lines


def render_status_report(
    *,
    smoke_output_dir: Path,
    export_smoke_output_dir: Path,
    docs_output_dir: Path,
    smoke_results: Dict[str, bool],
    export_smoke_results: Dict[str, bool],
    docs_results: Dict[str, bool],
) -> str:
    smoke_ready = all_present(smoke_results)
    export_smoke_ready = all_present(export_smoke_results)
    docs_ready = all_present(docs_results)
    module_ready = smoke_ready and export_smoke_ready and docs_ready

    lines = [
        "# Evaluation Module Status Report",
        "",
        f"**Module Ready:** {'YES' if module_ready else 'NO'}",
        "",
        "## Core Smoke Suite Artifacts",
        "",
        f"Base directory: `{smoke_output_dir}`",
        "",
    ]
    lines.extend(_render_checklist(smoke_results))
    lines.extend(
        [
            "",
            "## Export-And-Evaluate Bridge Artifacts",
            "",
            f"Base directory: `{export_smoke_output_dir}`",
            "",
        ]
    )
    lines.extend(_render_checklist(export_smoke_results))
    lines.extend(
        [
            "",
            "## Closeout Documentation",
            "",
            f"Base directory: `{docs_output_dir}`",
            "",
        ]
    )
    lines.extend(_render_checklist(docs_results))
    lines.extend(
        [
            "",
            "## Decision",
            "",
        ]
    )

    if module_ready:
        lines.append(
            "The evaluation module has the required smoke outputs, export-and-evaluate bridge outputs, "
            "and closeout documentation. It is ready to close and connect to real paper assembler output."
        )
    else:
        lines.append(
            "The evaluation module is missing one or more required artifacts. "
            "Run the verification script before closing the module."
        )

    return "\n".join(lines).strip() + "\n"


def write_status_report(
    *,
    smoke_output_dir: Path,
    export_smoke_output_dir: Path,
    docs_output_dir: Path,
    output_path: Path,
) -> Path:
    smoke_results = check_required_files(
        smoke_output_dir,
        REQUIRED_SMOKE_ARTIFACTS,
    )
    export_smoke_results = check_required_files(
        export_smoke_output_dir,
        REQUIRED_EXPORT_SMOKE_ARTIFACTS,
    )
    docs_results = check_required_files(
        docs_output_dir,
        REQUIRED_DOC_ARTIFACTS,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    report = render_status_report(
        smoke_output_dir=smoke_output_dir,
        export_smoke_output_dir=export_smoke_output_dir,
        docs_output_dir=docs_output_dir,
        smoke_results=smoke_results,
        export_smoke_results=export_smoke_results,
        docs_results=docs_results,
    )
    output_path.write_text(report, encoding="utf-8")
    return output_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Write a final status report for the evaluation module."
    )
    parser.add_argument(
        "--smoke-output-dir",
        default="data/outputs/smoke_evaluation_suite",
        help="Directory containing core smoke suite outputs.",
    )
    parser.add_argument(
        "--export-smoke-output-dir",
        default="data/outputs/smoke_export_and_evaluate",
        help="Directory containing export-and-evaluate smoke outputs.",
    )
    parser.add_argument(
        "--docs-output-dir",
        default="docs/evaluation",
        help="Directory containing evaluation closeout docs.",
    )
    parser.add_argument(
        "--output",
        default="docs/evaluation/evaluation_module_status.md",
        help="Path where the status report should be written.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    written_path = write_status_report(
        smoke_output_dir=Path(args.smoke_output_dir),
        export_smoke_output_dir=Path(args.export_smoke_output_dir),
        docs_output_dir=Path(args.docs_output_dir),
        output_path=Path(args.output),
    )

    print(f"Evaluation module status report written to: {written_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
