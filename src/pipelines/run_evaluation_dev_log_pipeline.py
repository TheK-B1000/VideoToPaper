from __future__ import annotations

from typing import Optional

from src.evaluation.evaluation_dev_log_cli import main as evaluation_dev_log_cli_main


def run_evaluation_dev_log_pipeline(argv: Optional[list[str]] = None) -> int:
    """
    Generate a development log for the evaluation system.
    """
    return evaluation_dev_log_cli_main(argv)
