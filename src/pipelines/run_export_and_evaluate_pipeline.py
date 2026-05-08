from __future__ import annotations

import argparse
from typing import Optional

from src.evaluation.evaluation_cli import main as evaluation_cli_main
from src.evaluation.paper_artifact_export_cli import main as paper_artifact_export_main


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export evaluator-ready paper artifact JSON and run evaluation."
    )

    parser.add_argument(
        "--claims",
        required=True,
        help="Path to claims JSON. Expected shape: list or {'claims': [...]}",
    )
    parser.add_argument(
        "--speaker-perspective",
        required=True,
        help="Path to speaker perspective JSON.",
    )
    parser.add_argument(
        "--adjudications",
        required=True,
        help="Path to adjudications JSON. Expected shape: list or {'adjudications': [...]}",
    )
    parser.add_argument(
        "--evidence-records",
        required=True,
        help="Path to evidence records JSON. Expected shape: list or {'evidence_records': [...]}",
    )
    parser.add_argument(
        "--references",
        required=False,
        help="Optional references JSON. Expected shape: list or {'references': [...]}",
    )
    parser.add_argument(
        "--rendered-clips",
        required=False,
        help="Optional rendered clips JSON. Expected shape: list or {'rendered_clips': [...]}",
    )
    parser.add_argument(
        "--paper-artifact",
        required=True,
        help="Path where the exported evaluator-ready paper artifact should be written.",
    )
    parser.add_argument(
        "--config-path",
        required=False,
        help="Optional evaluation config JSON path.",
    )
    parser.add_argument(
        "--audit-report",
        required=False,
        help="Optional path where the audit report JSON should be written.",
    )
    parser.add_argument(
        "--audit-summary",
        required=False,
        help="Optional path where the audit summary Markdown should be written.",
    )
    parser.add_argument(
        "--manifest",
        required=False,
        help="Optional path where the evaluation manifest should be written.",
    )
    parser.add_argument(
        "--validation-report",
        required=False,
        help="Optional path where validation diagnostics JSON should be written.",
    )
    parser.add_argument(
        "--validation-summary",
        required=False,
        help="Optional path where validation summary Markdown should be written.",
    )
    parser.add_argument(
        "--artifact-index",
        required=False,
        help="Optional path where the evaluation artifact index should be written.",
    )
    parser.add_argument(
        "--run-id",
        required=False,
        help="Optional run identifier for evaluation metadata.",
    )
    parser.add_argument(
        "--clip-tolerance-seconds",
        type=float,
        required=False,
        help="Optional clip timestamp tolerance override.",
    )
    parser.add_argument(
        "--minimum-balanced-retrieval-ratio",
        type=float,
        required=False,
        help="Optional balanced retrieval threshold override.",
    )
    parser.add_argument(
        "--print-summary",
        action="store_true",
        help="Print the audit summary after evaluation.",
    )
    parser.add_argument(
        "--print-validation-summary",
        action="store_true",
        help="Print validation diagnostics if artifact validation fails.",
    )
    return parser


def _append_optional_flag(args: list[str], flag: str, value: Optional[str]) -> None:
    if value:
        args.extend([flag, value])


def run_export_and_evaluate_pipeline(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    export_args = [
        "--claims",
        args.claims,
        "--speaker-perspective",
        args.speaker_perspective,
        "--adjudications",
        args.adjudications,
        "--evidence-records",
        args.evidence_records,
        "--output",
        args.paper_artifact,
    ]
    _append_optional_flag(export_args, "--references", args.references)
    _append_optional_flag(export_args, "--rendered-clips", args.rendered_clips)
    paper_artifact_export_main(export_args)

    evaluation_args = [
        "--paper-artifact",
        args.paper_artifact,
    ]
    _append_optional_flag(evaluation_args, "--config-path", args.config_path)
    _append_optional_flag(evaluation_args, "--audit-report", args.audit_report)
    _append_optional_flag(evaluation_args, "--audit-summary", args.audit_summary)
    _append_optional_flag(evaluation_args, "--manifest", args.manifest)
    _append_optional_flag(evaluation_args, "--validation-report", args.validation_report)
    _append_optional_flag(
        evaluation_args, "--validation-summary", args.validation_summary
    )
    _append_optional_flag(evaluation_args, "--artifact-index", args.artifact_index)
    _append_optional_flag(evaluation_args, "--run-id", args.run_id)

    if args.clip_tolerance_seconds is not None:
        evaluation_args.extend(
            ["--clip-tolerance-seconds", str(args.clip_tolerance_seconds)]
        )
    if args.minimum_balanced_retrieval_ratio is not None:
        evaluation_args.extend(
            [
                "--minimum-balanced-retrieval-ratio",
                str(args.minimum_balanced_retrieval_ratio),
            ]
        )
    if args.print_summary:
        evaluation_args.append("--print-summary")
    if args.print_validation_summary:
        evaluation_args.append("--print-validation-summary")

    return evaluation_cli_main(evaluation_args)
