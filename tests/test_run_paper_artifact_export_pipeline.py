import json

from src.pipelines.run_paper_artifact_export_pipeline import (
    run_paper_artifact_export_pipeline,
)


def write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_run_paper_artifact_export_pipeline_writes_artifact(tmp_path):
    claims_path = tmp_path / "claims.json"
    speaker_path = tmp_path / "speaker_perspective.json"
    adjudications_path = tmp_path / "adjudications.json"
    evidence_path = tmp_path / "evidence_records.json"
    output_path = tmp_path / "paper_artifact.json"

    write_json(
        claims_path,
        {
            "claims": [
                {
                    "claim_id": "claim_001",
                    "verbatim_quote": "Balanced evidence matters.",
                    "anchor_clip": {"start": 10.0, "end": 20.0},
                }
            ]
        },
    )

    write_json(
        speaker_path,
        {
            "expected_qualifications": [],
            "qualifications_preserved": [],
            "narrative_blocks": [
                {
                    "assertions": [
                        {
                            "text": "The speaker argues evidence matters.",
                            "hedge_drift_detected": False,
                        }
                    ],
                    "verbatim_anchors": ["claim_001"],
                }
            ],
        },
    )

    write_json(
        adjudications_path,
        {
            "adjudications": [
                {
                    "claim_id": "claim_001",
                    "balance_score": "balanced",
                    "verdict": "well_supported_with_qualifications",
                }
            ]
        },
    )

    write_json(
        evidence_path,
        {
            "evidence_records": [
                {
                    "evidence_record_id": "evidence_001",
                    "claim_id": "claim_001",
                    "identifier": "10.1234/example",
                    "url": "https://example.com/paper",
                }
            ]
        },
    )

    exit_code = run_paper_artifact_export_pipeline(
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

    assert exit_code == 0
    assert output_path.exists()

    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert artifact["claims"][0]["claim_id"] == "claim_001"
