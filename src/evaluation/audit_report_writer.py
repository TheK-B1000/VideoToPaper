from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Union

from src.evaluation.evaluation_harness import EvaluationReport
from src.evaluation.publishability_gate import (
    attach_publishability_decision,
    decide_publishability,
)


def write_audit_report(
    report: EvaluationReport,
    output_path: Union[str, Path],
) -> Path:
    """
    Write an evaluation report to disk as formatted JSON.

    The report includes both raw metric results and a human-readable
    publishability decision.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    decision = decide_publishability(report)
    payload: Dict[str, Any] = attach_publishability_decision(
        report.to_dict(),
        decision,
    )

    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return path


def load_audit_report(input_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Load a previously written audit report.
    """
    path = Path(input_path)

    if not path.exists():
        raise FileNotFoundError(f"Audit report not found: {path}")

    return json.loads(path.read_text(encoding="utf-8"))