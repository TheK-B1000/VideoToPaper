from src.pipelines.run_evaluation_closeout_pipeline import (
    run_evaluation_closeout_pipeline,
)


def test_run_evaluation_closeout_pipeline_writes_bundle(tmp_path):
    exit_code = run_evaluation_closeout_pipeline(
        [
            "--output-dir",
            str(tmp_path),
        ]
    )

    assert exit_code == 0
    assert (tmp_path / "evaluation_readme_section.md").exists()
    assert (tmp_path / "evaluation_architecture.md").exists()
    assert (tmp_path / "evaluation_dev_log.md").exists()
    assert (tmp_path / "evaluation_completion_checklist.md").exists()
