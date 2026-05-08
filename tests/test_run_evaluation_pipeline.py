import json

from src.pipelines.run_evaluation_pipeline import run_evaluation_pipeline


def make_clean_paper_artifact():
    return {
        "claims": [
            {
                "claim_id": "claim_001",
                "verbatim_quote": "Balanced evidence matters.",
                "anchor_clip": {"start": 10.0, "end": 20.0},
            }
        ],
        "speaker_perspective": {
            "expected_qualifications": ["the literature may be mixed"],
            "qualifications_preserved": ["the literature may be mixed"],
            "narrative_blocks": [
                {
                    "assertions": [
                        {
                            "text": "The speaker presents a claim that requires evidence.",
                            "hedge_drift_detected": False,
                        }
                    ],
                    "verbatim_anchors": ["claim_001"],
                }
            ],
        },
        "adjudications": [
            {
                "claim_id": "claim_001",
                "balance_score": "balanced",
                "verdict": "well_supported_with_qualifications",
            }
        ],
        "evidence_records": [
            {
                "evidence_record_id": "evidence_001",
                "identifier": "10.1234/example",
                "url": "https://example.com/paper",
            }
        ],
        "references": [
            {
                "evidence_record_id": "evidence_001",
                "identifier": "10.1234/example",
                "url": "https://example.com/paper",
            }
        ],
        "rendered_clips": [
            {
                "claim_id": "claim_001",
                "start": 10.0,
                "end": 20.0,
            }
        ],
    }


def test_run_evaluation_pipeline_writes_outputs(tmp_path):
    artifact_path = tmp_path / "paper_artifact.json"
    audit_report_path = tmp_path / "audit_report.json"
    audit_summary_path = tmp_path / "audit_summary.md"
    manifest_path = tmp_path / "manifest.json"

    artifact_path.write_text(
        json.dumps(make_clean_paper_artifact()),
        encoding="utf-8",
    )

    exit_code = run_evaluation_pipeline(
        [
            "--paper-artifact",
            str(artifact_path),
            "--audit-report",
            str(audit_report_path),
            "--audit-summary",
            str(audit_summary_path),
            "--manifest",
            str(manifest_path),
            "--run-id",
            "pipeline_test_001",
        ]
    )

    assert exit_code == 0
    assert audit_report_path.exists()
    assert audit_summary_path.exists()
    assert manifest_path.exists()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["publishable"] is True
    assert manifest["metadata"]["run_id"] == "pipeline_test_001"
