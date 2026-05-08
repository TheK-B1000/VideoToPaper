from src.evaluation.evaluation_architecture_cli import main


def test_evaluation_architecture_cli_writes_doc(tmp_path, capsys):
    output_path = tmp_path / "evaluation_architecture.md"

    exit_code = main(
        [
            "--output",
            str(output_path),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert output_path.exists()
    assert "Evaluation architecture document written to:" in captured.out

    content = output_path.read_text(encoding="utf-8")

    assert "# Evaluation System Architecture" in content
    assert "## Data Flow" in content
