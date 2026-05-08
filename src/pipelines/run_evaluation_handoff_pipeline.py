from __future__ import annotations

from typing import Optional

from src.evaluation.evaluation_handoff_cli import main as evaluation_handoff_cli_main


def run_evaluation_handoff_pipeline(argv: Optional[list[str]] = None) -> int:
    """
    Generate a handoff note for the evaluation module.
    """
    return evaluation_handoff_cli_main(argv)
