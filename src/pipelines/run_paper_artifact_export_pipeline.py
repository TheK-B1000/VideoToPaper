from __future__ import annotations

from typing import Optional

from src.evaluation.paper_artifact_export_cli import main as paper_artifact_export_main


def run_paper_artifact_export_pipeline(argv: Optional[list[str]] = None) -> int:
    """
    Export evaluator-ready paper artifact JSON from assembled paper inputs.
    """
    return paper_artifact_export_main(argv)
