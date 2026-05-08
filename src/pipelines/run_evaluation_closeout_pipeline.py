from __future__ import annotations

from typing import Optional

from src.evaluation.evaluation_closeout_cli import main as evaluation_closeout_cli_main


def run_evaluation_closeout_pipeline(argv: Optional[list[str]] = None) -> int:
    """
    Generate the closeout documentation bundle for the evaluation system.
    """
    return evaluation_closeout_cli_main(argv)
