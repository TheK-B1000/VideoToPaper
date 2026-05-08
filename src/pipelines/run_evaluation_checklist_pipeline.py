from __future__ import annotations

from typing import Optional

from src.evaluation.evaluation_checklist_cli import main as evaluation_checklist_cli_main


def run_evaluation_checklist_pipeline(argv: Optional[list[str]] = None) -> int:
    """
    Generate a completion checklist for the evaluation module.
    """
    return evaluation_checklist_cli_main(argv)
