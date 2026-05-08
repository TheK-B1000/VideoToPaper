from src.evaluation.evaluation_closeout_cli import main


def test_evaluation_closeout_cli_writes_bundle(tmp_path, capsys):
    exit_code = main(
        [
            "--output-dir",
            str(tmp_path),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Evaluation closeout bundle written:" in captured.out

    assert (tmp_path / "evaluation_readme_section.md").exists()
    assert (tmp_path / "evaluation_architecture.md").exists()
    assert (tmp_path / "evaluation_dev_log.md").exists()
    assert (tmp_path / "evaluation_completion_checklist.md").exists()
