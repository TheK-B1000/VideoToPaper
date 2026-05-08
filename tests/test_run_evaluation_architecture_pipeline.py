from src.pipelines.run_evaluation_architecture_pipeline import (
    run_evaluation_architecture_pipeline,
)


def test_run_evaluation_architecture_pipeline_writes_doc(tmp_path):
    output_path = tmp_path / "evaluation_architecture.md"

    exit_code = run_evaluation_architecture_pipeline(
        [
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    assert output_path.exists()

    content = output_path.read_text(encoding="utf-8")

    assert "# Evaluation System Architecture" in content
