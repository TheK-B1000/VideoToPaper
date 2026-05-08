from __future__ import annotations

from typing import Optional

from src.evaluation.assembler_fixture_cli import main as assembler_fixture_cli_main


def run_assembler_fixture_pipeline(argv: Optional[list[str]] = None) -> int:
    """
    Generate assembler-style fixture files for export-and-evaluate testing.
    """
    return assembler_fixture_cli_main(argv)
