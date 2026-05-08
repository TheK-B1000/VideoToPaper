from scripts.evaluation_module_status import REQUIRED_EVALUATION_FILES, main


def test_evaluation_module_status_returns_complete_for_current_repo(capsys):
    exit_code = main(["--base-dir", "."])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Evaluation module status: complete" in captured.out
    for relative_path in REQUIRED_EVALUATION_FILES:
        assert relative_path in captured.out


def test_evaluation_module_status_returns_incomplete_when_missing_files(
    tmp_path, capsys
):
    exit_code = main(["--base-dir", str(tmp_path)])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Evaluation module status: incomplete" in captured.out
    assert "[MISSING]" in captured.out
