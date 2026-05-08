from src.evaluation.evaluation_checklist_cli import main


def test_evaluation_checklist_cli_writes_checklist(tmp_path, capsys):
    output_path = tmp_path / "evaluation_completion_checklist.md"

    exit_code = main(
        [
            "--output",
            str(output_path),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert output_path.exists()
    assert "Evaluation completion checklist written to:" in captured.out

    content = output_path.read_text(encoding="utf-8")

    assert "# Evaluation Module Completion Checklist" in content
    assert "## Close Criteria" in content
