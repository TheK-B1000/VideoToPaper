from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Union

from src.evaluation.validation_summary import render_validation_summary


def write_validation_summary(
    validation_payload: Dict[str, Any],
    output_path: Union[str, Path],
) -> Path:
    """
    Write a human-readable Markdown validation summary to disk.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    summary = render_validation_summary(validation_payload)

    path.write_text(summary, encoding="utf-8")

    return path