import json

import pytest

from src.evaluation.sample_artifact_cli import main


def test_sample_artifact_cli_writes_publishable_artifact(tmp_path, capsys):
    output_path = tmp_path / "sample_paper_artifact.json"

    exit_code = main(
        [
            "--output",
            str(output_path),
            "--publishable",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert output_path.exists()
    assert "Wrote publishable sample artifact to:" in captured.out

    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["claims"][0]["claim_id"] == "claim_001"
    assert payload["rendered_clips"][0]["start"] == 10.0
    assert payload["adjudications"][0]["balance_score"] == "balanced"


def test_sample_artifact_cli_writes_unpublishable_artifact(tmp_path, capsys):
    output_path = tmp_path / "bad_sample_paper_artifact.json"

    exit_code = main(
        [
            "--output",
            str(output_path),
            "--unpublishable",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert output_path.exists()
    assert "Wrote unpublishable sample artifact to:" in captured.out

    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["rendered_clips"][0]["start"] == 40.0
    assert payload["adjudications"][0]["balance_score"] == "supportive_skewed"
    assert payload["references"][-1]["evidence_record_id"] == "evidence_001"


def test_sample_artifact_cli_defaults_to_publishable(tmp_path):
    output_path = tmp_path / "default_sample_paper_artifact.json"

    exit_code = main(
        [
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0

    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["adjudications"][0]["balance_score"] == "balanced"


def test_sample_artifact_cli_rejects_conflicting_modes(tmp_path):
    output_path = tmp_path / "sample_paper_artifact.json"

    with pytest.raises(SystemExit):
        main(
            [
                "--output",
                str(output_path),
                "--publishable",
                "--unpublishable",
            ]
        )