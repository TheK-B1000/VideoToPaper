from src.pipelines.run_evaluation_checklist_pipeline import (
    run_evaluation_checklist_pipeline,
)


def test_run_evaluation_checklist_pipeline_writes_checklist(tmp_path):
    output_path = tmp_path / "evaluation_completion_checklist.md"

    exit_code = run_evaluation_checklist_pipeline(
        [
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    assert output_path.exists()

    content = output_path.read_text(encoding="utf-8")

    assert "# Evaluation Module Completion Checklist" in content
