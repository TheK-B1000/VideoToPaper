from __future__ import annotations

from typing import Any, Dict, List


def _format_errors(errors: List[str]) -> str:
    if not errors:
        return "- No validation errors found."

    return "\n".join(f"- {error}" for error in errors)


def render_validation_summary(validation_payload: Dict[str, Any]) -> str:
    """
    Render a human-readable Markdown summary from validation diagnostics.

    Validation happens before evaluation. If validation fails, the evaluator
    should not produce an audit report because the paper artifact contract is
    already broken.
    """
    valid = bool(validation_payload.get("valid", False))
    error_count = int(validation_payload.get("error_count", 0))
    errors = validation_payload.get("errors", [])

    status = "PASS" if valid else "FAIL"

    lines = [
        "# Paper Artifact Validation Summary",
        "",
        f"**Valid:** {status}",
        f"**Error Count:** {error_count}",
        "",
        "## Errors",
        "",
        _format_errors(errors),
    ]

    return "\n".join(lines).strip() + "\n"