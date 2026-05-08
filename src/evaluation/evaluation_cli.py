from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional

from src.evaluation.audit_report_writer import load_audit_report
from src.evaluation.audit_summary import render_audit_summary
from src.evaluation.evaluation_config import load_evaluation_runtime_config
from src.evaluation.evaluation_artifact_index import (
    build_evaluation_artifact_index,
    write_evaluation_artifact_index,
)
from src.evaluation.evaluation_harness import EvaluationConfig
from src.evaluation.evaluation_runner import run_paper_evaluation
from src.evaluation.validation_report_writer import load_validation_report
from src.evaluation.validation_summary import render_validation_summary
from src.evaluation.validation_summary_writer import write_validation_summary


def load_paper_artifact(path: Path) -> Dict[str, Any]:
    """
    Load a generated paper artifact from JSON.

    The artifact should contain the claims, speaker perspective,
    adjudications, evidence records, references, and rendered clips needed
    by the evaluation harness.
    """
    if not path.exists():
        raise FileNotFoundError(f"Paper artifact not found: {path}")

    return json.loads(path.read_text(encoding="utf-8"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate a generated inquiry paper artifact."
    )

    parser.add_argument(
        "--paper-artifact",
        required=True,
        help="Path to the generated paper artifact JSON.",
    )

    parser.add_argument(
        "--config-path",
        required=False,
        help="Optional evaluation config JSON path.",
    )

    parser.add_argument(
        "--audit-report",
        required=False,
        help="Path where the audit report JSON should be written.",
    )

    parser.add_argument(
        "--audit-summary",
        required=False,
        help="Optional path where the Markdown audit summary should be written.",
    )

    parser.add_argument(
        "--manifest",
        required=False,
        help="Optional path where the evaluation run manifest should be written.",
    )

    parser.add_argument(
        "--validation-report",
        required=False,
        help="Optional path where artifact validation diagnostics should be written.",
    )

    parser.add_argument(
        "--validation-summary",
        required=False,
        help="Optional path where artifact validation Markdown summary should be written.",
    )

    parser.add_argument(
        "--artifact-index",
        required=False,
        help="Optional path where the evaluation artifact index should be written.",
    )

    parser.add_argument(
        "--run-id",
        required=False,
        help="Optional run identifier to store in the manifest metadata.",
    )

    parser.add_argument(
        "--clip-tolerance-seconds",
        type=float,
        default=None,
        help="Allowed start/end timestamp drift for rendered clips.",
    )

    parser.add_argument(
        "--minimum-balanced-retrieval-ratio",
        type=float,
        default=None,
        help="Minimum ratio of claims that must have balanced retrieval.",
    )

    parser.add_argument(
        "--print-summary",
        action="store_true",
        help="Print a human-readable Markdown audit summary.",
    )

    parser.add_argument(
        "--print-validation-summary",
        action="store_true",
        help="Print validation diagnostics if validation fails.",
    )

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    runtime_config = None
    if args.config_path:
        runtime_config = load_evaluation_runtime_config(args.config_path)

    paper_artifact_path = Path(args.paper_artifact)
    audit_report_path = Path(
        args.audit_report
        or (
            runtime_config.outputs.audit_report_path
            if runtime_config
            else "data/outputs/audit_report.json"
        )
    )
    audit_summary_path = (
        Path(
            args.audit_summary
            or (
                runtime_config.outputs.audit_summary_path
                if runtime_config
                else "data/outputs/audit_summary.md"
            )
        )
        if (args.audit_summary or runtime_config)
        else None
    )
    manifest_path = (
        Path(
            args.manifest
            or (
                runtime_config.outputs.manifest_path
                if runtime_config
                else "data/outputs/evaluation_manifest.json"
            )
        )
        if (args.manifest or runtime_config)
        else None
    )
    validation_report_path = (
        Path(
            args.validation_report
            or (
                runtime_config.outputs.validation_report_path
                if runtime_config
                else "data/outputs/validation_report.json"
            )
        )
        if (args.validation_report or runtime_config)
        else None
    )
    validation_summary_path = (
        Path(
            args.validation_summary
            or (
                runtime_config.outputs.validation_summary_path
                if runtime_config
                else "data/outputs/validation_summary.md"
            )
        )
        if (args.validation_summary or runtime_config)
        else None
    )
    artifact_index_path = (
        Path(
            args.artifact_index
            or (
                runtime_config.outputs.artifact_index_path
                if runtime_config
                else "data/outputs/evaluation_artifact_index.json"
            )
        )
        if (args.artifact_index or runtime_config)
        else None
    )

    paper_artifact = load_paper_artifact(paper_artifact_path)

    clip_tolerance_seconds = (
        args.clip_tolerance_seconds
        if args.clip_tolerance_seconds is not None
        else (
            runtime_config.evaluation.clip_tolerance_seconds
            if runtime_config
            else 1.0
        )
    )

    minimum_balanced_retrieval_ratio = (
        args.minimum_balanced_retrieval_ratio
        if args.minimum_balanced_retrieval_ratio is not None
        else (
            runtime_config.evaluation.minimum_balanced_retrieval_ratio
            if runtime_config
            else 0.8
        )
    )

    config = EvaluationConfig(
        clip_tolerance_seconds=clip_tolerance_seconds,
        minimum_balanced_retrieval_ratio=minimum_balanced_retrieval_ratio,
    )

    metadata = dict(runtime_config.metadata) if runtime_config else {}
    if args.run_id:
        metadata["run_id"] = args.run_id

    try:
        result = run_paper_evaluation(
            paper_artifact=paper_artifact,
            paper_artifact_path=paper_artifact_path,
            audit_report_path=audit_report_path,
            audit_summary_path=audit_summary_path,
            manifest_path=manifest_path,
            validation_report_path=validation_report_path,
            metadata=metadata,
            config=config,
        )
    except ValueError:
        if validation_report_path is not None and validation_report_path.exists():
            validation_payload = load_validation_report(validation_report_path)

            if validation_summary_path is not None:
                written_summary_path = write_validation_summary(
                    validation_payload=validation_payload,
                    output_path=validation_summary_path,
                )
                print(f"Validation summary written to: {written_summary_path}")

            if args.print_validation_summary:
                print()
                print(render_validation_summary(validation_payload))

        if artifact_index_path is not None:
            index = build_evaluation_artifact_index(
                paper_artifact_path=paper_artifact_path,
                audit_report_path=None,
                audit_summary_path=None,
                manifest_path=None,
                validation_report_path=validation_report_path,
                validation_summary_path=validation_summary_path,
                publishable=None,
                valid=False,
                metadata=metadata,
            )
            written_index_path = write_evaluation_artifact_index(
                index=index,
                output_path=artifact_index_path,
            )
            print(f"Evaluation artifact index written to: {written_index_path}")

        raise

    status = "publishable" if result.publishable else "not publishable"

    print(f"Audit report written to: {result.audit_report_path}")

    if result.audit_summary_path is not None:
        print(f"Audit summary written to: {result.audit_summary_path}")

    if result.manifest_path is not None:
        print(f"Evaluation manifest written to: {result.manifest_path}")

    print(f"Evaluation result: {status}")

    if args.print_summary:
        audit_payload = load_audit_report(audit_report_path)
        print()
        print(render_audit_summary(audit_payload))

    if artifact_index_path is not None:
        index = build_evaluation_artifact_index(
            paper_artifact_path=paper_artifact_path,
            audit_report_path=result.audit_report_path,
            audit_summary_path=result.audit_summary_path,
            manifest_path=result.manifest_path,
            validation_report_path=validation_report_path,
            validation_summary_path=validation_summary_path,
            publishable=result.publishable,
            valid=True,
            metadata=metadata,
        )
        written_index_path = write_evaluation_artifact_index(
            index=index,
            output_path=artifact_index_path,
        )
        print(f"Evaluation artifact index written to: {written_index_path}")

    return 0 if result.publishable else 1


if __name__ == "__main__":
    raise SystemExit(main())
