from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Union

from src.evaluation.paper_artifact_validator import ArtifactValidationResult


def build_validation_report_payload(
    validation_result: ArtifactValidationResult,
) -> Dict[str, Any]:
    return {
        "valid": validation_result.valid,
        "error_count": len(validation_result.errors),
        "errors": validation_result.errors,
    }


def write_validation_report(
    validation_result: ArtifactValidationResult,
    output_path: Union[str, Path],
) -> Path:
    """
    Write paper artifact validation diagnostics to JSON.

    This is separate from the audit report because validation happens before
    evaluation. If validation fails, no audit report should be produced.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = build_validation_report_payload(validation_result)

    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return path


def load_validation_report(input_path: Union[str, Path]) -> Dict[str, Any]:
    path = Path(input_path)

    if not path.exists():
        raise FileNotFoundError(f"Validation report not found: {path}")

    return json.loads(path.read_text(encoding="utf-8"))