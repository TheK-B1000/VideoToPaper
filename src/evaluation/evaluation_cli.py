from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional

from src.evaluation.evaluation_harness import EvaluationConfig
from src.evaluation.evaluation_runner import run_paper_evaluation


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
        "--audit-report",
        required=True,
        help="Path where the audit report JSON should be written.",
    )

    parser.add_argument(
        "--clip-tolerance-seconds",
        type=float,
        default=1.0,
        help="Allowed start/end timestamp drift for rendered clips.",
    )

    parser.add_argument(
        "--minimum-balanced-retrieval-ratio",
        type=float,
        default=0.8,
        help="Minimum ratio of claims that must have balanced retrieval.",
    )

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    paper_artifact_path = Path(args.paper_artifact)
    audit_report_path = Path(args.audit_report)

    paper_artifact = load_paper_artifact(paper_artifact_path)

    config = EvaluationConfig(
        clip_tolerance_seconds=args.clip_tolerance_seconds,
        minimum_balanced_retrieval_ratio=args.minimum_balanced_retrieval_ratio,
    )

    result = run_paper_evaluation(
        paper_artifact=paper_artifact,
        audit_report_path=audit_report_path,
        config=config,
    )

    status = "publishable" if result.publishable else "not publishable"

    print(f"Audit report written to: {result.audit_report_path}")
    print(f"Evaluation result: {status}")

    return 0 if result.publishable else 1


if __name__ == "__main__":
    raise SystemExit(main())
