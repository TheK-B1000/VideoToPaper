from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Union

from src.evaluation.evaluation_harness import EvaluationReport


def write_audit_report(
    report: EvaluationReport,
    output_path: Union[str, Path],
) -> Path:
    """
    Write an evaluation report to disk as formatted JSON.

    The report is intentionally written as plain JSON so it can be inspected
    by humans, loaded by the backend, or displayed later in the operator UI.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    payload: Dict[str, Any] = report.to_dict()

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