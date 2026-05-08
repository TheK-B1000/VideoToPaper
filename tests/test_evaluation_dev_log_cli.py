from src.evaluation.evaluation_dev_log_cli import main


def test_evaluation_dev_log_cli_writes_log(tmp_path, capsys):
    output_path = tmp_path / "evaluation_dev_log.md"

    exit_code = main(
        [
            "--output",
            str(output_path),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert output_path.exists()
    assert "Evaluation development log written to:" in captured.out

    content = output_path.read_text(encoding="utf-8")

    assert "# Evaluation Harness Development Log" in content
    assert "## What I Learned" in content
