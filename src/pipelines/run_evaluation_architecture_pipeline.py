from __future__ import annotations

from typing import Optional

from src.evaluation.evaluation_architecture_cli import (
    main as evaluation_architecture_cli_main,
)


def run_evaluation_architecture_pipeline(argv: Optional[list[str]] = None) -> int:
    """
    Generate an architecture document for the evaluation system.
    """
    return evaluation_architecture_cli_main(argv)
