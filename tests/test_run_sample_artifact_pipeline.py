import json

from src.pipelines.run_sample_artifact_pipeline import run_sample_artifact_pipeline


def test_run_sample_artifact_pipeline_writes_sample(tmp_path):
    output_path = tmp_path / "sample_paper_artifact.json"

    exit_code = run_sample_artifact_pipeline(
        [
            "--output",
            str(output_path),
            "--publishable",
        ]
    )

    assert exit_code == 0
    assert output_path.exists()

    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["claims"][0]["claim_id"] == "claim_001"
