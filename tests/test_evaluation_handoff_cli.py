from src.evaluation.evaluation_handoff_cli import main


def test_evaluation_handoff_cli_writes_note(tmp_path, capsys):
    output_path = tmp_path / "evaluation_handoff_note.md"

    exit_code = main(
        [
            "--output",
            str(output_path),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert output_path.exists()
    assert "Evaluation handoff note written to:" in captured.out

    content = output_path.read_text(encoding="utf-8")

    assert "# Evaluation Module Handoff Note" in content
    assert "## Next Engineering Step" in content
