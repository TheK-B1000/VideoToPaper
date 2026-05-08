from src.pipelines.run_evaluation_dev_log_pipeline import (
    run_evaluation_dev_log_pipeline,
)


def test_run_evaluation_dev_log_pipeline_writes_log(tmp_path):
    output_path = tmp_path / "evaluation_dev_log.md"

    exit_code = run_evaluation_dev_log_pipeline(
        [
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    assert output_path.exists()

    content = output_path.read_text(encoding="utf-8")

    assert "# Evaluation Harness Development Log" in content
