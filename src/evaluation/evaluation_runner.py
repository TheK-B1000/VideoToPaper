from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Union

from src.evaluation.audit_report_writer import write_audit_report
from src.evaluation.evaluation_harness import (
    EvaluationConfig,
    EvaluationReport,
    run_evaluation_harness,
)


@dataclass(frozen=True)
class EvaluationRunResult:
    report: EvaluationReport
    audit_report_path: Path

    @property
    def publishable(self) -> bool:
        return self.report.publishable


def run_paper_evaluation(
    paper_artifact: Dict[str, Any],
    audit_report_path: Union[str, Path],
    config: Optional[EvaluationConfig] = None,
) -> EvaluationRunResult:
    """
    Evaluate a generated paper artifact and write its audit report to disk.

    This function is the integration point for the paper-generation pipeline.
    The assembler should call it once the final paper artifact has been created.
    """
    report = run_evaluation_harness(
        paper_artifact=paper_artifact,
        config=config,
    )

    written_path = write_audit_report(
        report=report,
        output_path=audit_report_path,
    )

    return EvaluationRunResult(
        report=report,
        audit_report_path=written_path,
    )