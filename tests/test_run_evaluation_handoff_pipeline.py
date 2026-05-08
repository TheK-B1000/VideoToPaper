from src.pipelines.run_evaluation_handoff_pipeline import (
    run_evaluation_handoff_pipeline,
)


def test_run_evaluation_handoff_pipeline_writes_note(tmp_path):
    output_path = tmp_path / "evaluation_handoff_note.md"

    exit_code = run_evaluation_handoff_pipeline(
        [
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    assert output_path.exists()

    content = output_path.read_text(encoding="utf-8")

    assert "# Evaluation Module Handoff Note" in content
