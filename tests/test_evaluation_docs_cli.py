from src.evaluation.evaluation_docs_cli import main


def test_evaluation_docs_cli_writes_section(tmp_path, capsys):
    output_path = tmp_path / "evaluation_readme_section.md"

    exit_code = main(
        [
            "--output",
            str(output_path),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert output_path.exists()
    assert "Evaluation README section written to:" in captured.out

    content = output_path.read_text(encoding="utf-8")

    assert "## Paper Evaluation System" in content
    assert "python scripts/smoke_evaluation_suite.py" in content
