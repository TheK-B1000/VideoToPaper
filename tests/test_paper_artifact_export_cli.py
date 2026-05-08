import json

import pytest

from src.evaluation.paper_artifact_export_cli import _unwrap_list, load_json, main


def write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def make_claims():
    return {
        "claims": [
            {
                "claim_id": "claim_001",
                "verbatim_quote": "Balanced evidence matters.",
                "anchor_clip": {"start": 10.0, "end": 20.0},
            }
        ]
    }


def make_speaker_perspective():
    return {
        "expected_qualifications": ["the literature may be mixed"],
        "qualifications_preserved": ["the literature may be mixed"],
        "narrative_blocks": [
            {
                "assertions": [
                    {
                        "text": "The speaker argues evidence should be weighed carefully.",
                        "hedge_drift_detected": False,
                    }
                ],
                "verbatim_anchors": ["claim_001"],
            }
        ],
    }


def make_adjudications():
    return {
        "adjudications": [
            {
                "claim_id": "claim_001",
                "speaker_claim_summary": "The speaker says evidence should be balanced.",
                "balance_score": "balanced",
                "verdict": "well_supported_with_qualifications",
            }
        ]
    }


def make_evidence_records():
    return {
        "evidence_records": [
            {
                "evidence_record_id": "evidence_001",
                "claim_id": "claim_001",
                "tier": 1,
                "stance": "supports",
                "title": "Example Evidence Record",
                "identifier": "10.1234/example",
                "url": "https://example.com/paper",
            }
        ]
    }


def test_unwrap_list_accepts_plain_list():
    payload = [{"id": "one"}]

    assert _unwrap_list(payload, "items") == [{"id": "one"}]


def test_unwrap_list_accepts_wrapped_list():
    payload = {"items": [{"id": "one"}]}

    assert _unwrap_list(payload, "items") == [{"id": "one"}]


def test_unwrap_list_rejects_invalid_payload():
    with pytest.raises(ValueError, match="Expected a list"):
        _unwrap_list({"wrong": []}, "items")


def test_load_json_raises_for_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_json(tmp_path / "missing.json")


def test_export_cli_writes_valid_paper_artifact(tmp_path, capsys):
    claims_path = tmp_path / "claims.json"
    speaker_path = tmp_path / "speaker_perspective.json"
    adjudications_path = tmp_path / "adjudications.json"
    evidence_path = tmp_path / "evidence_records.json"
    output_path = tmp_path / "paper_artifact.json"

    write_json(claims_path, make_claims())
    write_json(speaker_path, make_speaker_perspective())
    write_json(adjudications_path, make_adjudications())
    write_json(evidence_path, make_evidence_records())

    exit_code = main(
        [
            "--claims",
            str(claims_path),
            "--speaker-perspective",
            str(speaker_path),
            "--adjudications",
            str(adjudications_path),
            "--evidence-records",
            str(evidence_path),
            "--output",
            str(output_path),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert output_path.exists()
    assert "Paper artifact written to:" in captured.out

    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert artifact["claims"][0]["claim_id"] == "claim_001"
    assert artifact["references"][0]["evidence_record_id"] == "evidence_001"
    assert artifact["rendered_clips"][0]["start"] == 10.0


def test_export_cli_accepts_explicit_references_and_rendered_clips(tmp_path):
    claims_path = tmp_path / "claims.json"
    speaker_path = tmp_path / "speaker_perspective.json"
    adjudications_path = tmp_path / "adjudications.json"
    evidence_path = tmp_path / "evidence_records.json"
    references_path = tmp_path / "references.json"
    clips_path = tmp_path / "rendered_clips.json"
    output_path = tmp_path / "paper_artifact.json"

    write_json(claims_path, make_claims())
    write_json(speaker_path, make_speaker_perspective())
    write_json(adjudications_path, make_adjudications())
    write_json(evidence_path, make_evidence_records())
    write_json(
        references_path,
        {
            "references": [
                {
                    "evidence_record_id": "evidence_001",
                    "identifier": "10.1234/example",
                    "url": "https://example.com/paper",
                }
            ]
        },
    )
    write_json(
        clips_path,
        {
            "rendered_clips": [
                {
                    "claim_id": "claim_001",
                    "start": 10.0,
                    "end": 20.0,
                }
            ]
        },
    )

    exit_code = main(
        [
            "--claims",
            str(claims_path),
            "--speaker-perspective",
            str(speaker_path),
            "--adjudications",
            str(adjudications_path),
            "--evidence-records",
            str(evidence_path),
            "--references",
            str(references_path),
            "--rendered-clips",
            str(clips_path),
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0

    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert artifact["references"][0]["evidence_record_id"] == "evidence_001"
    assert artifact["rendered_clips"][0]["claim_id"] == "claim_001"


def test_export_cli_fails_validation_for_bad_artifact(tmp_path):
    claims = make_claims()
    del claims["claims"][0]["anchor_clip"]

    claims_path = tmp_path / "claims.json"
    speaker_path = tmp_path / "speaker_perspective.json"
    adjudications_path = tmp_path / "adjudications.json"
    evidence_path = tmp_path / "evidence_records.json"
    output_path = tmp_path / "paper_artifact.json"

    write_json(claims_path, claims)
    write_json(speaker_path, make_speaker_perspective())
    write_json(adjudications_path, make_adjudications())
    write_json(evidence_path, make_evidence_records())

    with pytest.raises(KeyError):
        main(
            [
                "--claims",
                str(claims_path),
                "--speaker-perspective",
                str(speaker_path),
                "--adjudications",
                str(adjudications_path),
                "--evidence-records",
                str(evidence_path),
                "--output",
                str(output_path),
            ]
        )
