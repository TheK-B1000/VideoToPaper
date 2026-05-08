import json

import pytest

from scripts.smoke_evaluation_suite import main as smoke_suite_main
from scripts.smoke_evaluation_suite_summary import (
    load_json,
    main,
    render_suite_summary,
    status_label,
    write_suite_summary,
)


def test_status_label_formats_optional_booleans():
    assert status_label(True) == "PASS"
    assert status_label(False) == "FAIL"
    assert status_label(None) == "N/A"


def test_load_json_raises_for_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_json(tmp_path / "missing.json")


def test_render_suite_summary_reads_smoke_outputs(tmp_path):
    output_dir = tmp_path / "suite"

    smoke_suite_main(
        [
            "--output-dir",
            str(output_dir),
            "--run-prefix",
            "summary_test",
        ]
    )

    summary = render_suite_summary(output_dir)

    assert "# Evaluation Smoke Suite Summary" in summary
    assert "| Passing artifact | PASS | PASS | Passes evaluation |" in summary
    assert (
        "| Unpublishable artifact | PASS | FAIL | Fails publishability gates |"
        in summary
    )
    assert (
        "| Malformed artifact | FAIL | N/A | Fails validation before audit |"
        in summary
    )
    assert "- evidence_balance" in summary
    assert "- citation_integrity" in summary
    assert "- clip_anchor_accuracy" in summary
    assert "- claims[0] is missing anchor_clip." in summary


def test_write_suite_summary_creates_markdown_file(tmp_path):
    output_dir = tmp_path / "suite"
    summary_path = output_dir / "summary.md"

    smoke_suite_main(
        [
            "--output-dir",
            str(output_dir),
            "--run-prefix",
            "write_summary_test",
        ]
    )

    written_path = write_suite_summary(output_dir, summary_path)

    assert written_path == summary_path
    assert summary_path.exists()

    summary = summary_path.read_text(encoding="utf-8")

    assert "# Evaluation Smoke Suite Summary" in summary
    assert "## Scenario Results" in summary


def test_suite_summary_cli_writes_summary(tmp_path, capsys):
    output_dir = tmp_path / "suite"
    summary_path = output_dir / "summary.md"

    smoke_suite_main(
        [
            "--output-dir",
            str(output_dir),
            "--run-prefix",
            "cli_summary_test",
        ]
    )

    exit_code = main(
        [
            "--output-dir",
            str(output_dir),
            "--summary-path",
            str(summary_path),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert summary_path.exists()
    assert "Smoke suite summary written to:" in captured.out

    summary = summary_path.read_text(encoding="utf-8")

    assert "Evaluation Smoke Suite Summary" in summary