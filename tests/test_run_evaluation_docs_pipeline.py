from src.pipelines.run_evaluation_docs_pipeline import run_evaluation_docs_pipeline


def test_run_evaluation_docs_pipeline_writes_docs(tmp_path):
    output_path = tmp_path / "evaluation_readme_section.md"

    exit_code = run_evaluation_docs_pipeline(
        [
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    assert output_path.exists()

    content = output_path.read_text(encoding="utf-8")

    assert "## Paper Evaluation System" in content
