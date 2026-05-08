from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Union

from src.evaluation.audit_summary import render_audit_summary


def write_audit_summary(
    audit_payload: Dict[str, Any],
    output_path: Union[str, Path],
) -> Path:
    """
    Write a human-readable Markdown audit summary to disk.

    The JSON audit report remains the source of truth. This summary is a
    readable companion artifact for development logs, demos, and operator UI.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    summary = render_audit_summary(audit_payload)

    path.write_text(summary, encoding="utf-8")

    return path