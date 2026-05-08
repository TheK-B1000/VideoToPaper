from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Union

from src.evaluation.audit_report_writer import load_audit_report, write_audit_report
from src.evaluation.audit_summary_writer import write_audit_summary
from src.evaluation.evaluation_harness import (
    EvaluationConfig,
    EvaluationReport,
    run_evaluation_harness,
)


@dataclass(frozen=True)
class EvaluationRunResult:
    report: EvaluationReport
    audit_report_path: Path
    audit_summary_path: Optional[Path] = None

    @property
    def publishable(self) -> bool:
        return self.report.publishable


def run_paper_evaluation(
    paper_artifact: Dict[str, Any],
    audit_report_path: Union[str, Path],
    config: Optional[EvaluationConfig] = None,
    audit_summary_path: Optional[Union[str, Path]] = None,
) -> EvaluationRunResult:
    """
    Evaluate a generated paper artifact and write its audit artifacts to disk.

    The JSON report is always written. The Markdown summary is optional.
    """
    report = run_evaluation_harness(
        paper_artifact=paper_artifact,
        config=config,
    )

    written_report_path = write_audit_report(
        report=report,
        output_path=audit_report_path,
    )

    written_summary_path: Optional[Path] = None

    if audit_summary_path is not None:
        audit_payload = load_audit_report(written_report_path)
        written_summary_path = write_audit_summary(
            audit_payload=audit_payload,
            output_path=audit_summary_path,
        )

    return EvaluationRunResult(
        report=report,
        audit_report_path=written_report_path,
        audit_summary_path=written_summary_path,
    )