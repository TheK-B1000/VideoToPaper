from __future__ import annotations

from typing import Optional

from src.evaluation.evaluation_cli import main as evaluation_cli_main


def run_evaluation_pipeline(argv: Optional[list[str]] = None) -> int:
    """
    Run the paper evaluation pipeline.

    This thin wrapper keeps the project stage runner clean while allowing
    the evaluator to keep its own CLI parser and config behavior.
    """
    return evaluation_cli_main(argv)
