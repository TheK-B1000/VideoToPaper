from __future__ import annotations

from typing import Optional

from src.evaluation.sample_artifact_cli import main as sample_artifact_cli_main


def run_sample_artifact_pipeline(argv: Optional[list[str]] = None) -> int:
    """
    Generate sample paper artifacts for local evaluation smoke tests.
    """
    return sample_artifact_cli_main(argv)
