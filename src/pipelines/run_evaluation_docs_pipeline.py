from __future__ import annotations

from typing import Optional

from src.evaluation.evaluation_docs_cli import main as evaluation_docs_cli_main


def run_evaluation_docs_pipeline(argv: Optional[list[str]] = None) -> int:
    """
    Generate README-ready documentation for the evaluation system.
    """
    return evaluation_docs_cli_main(argv)
