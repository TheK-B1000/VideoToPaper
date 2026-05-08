import json

from src.pipelines.run_export_and_evaluate_pipeline import (
    run_export_and_evaluate_pipeline,
)


def write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def make_claims():
    return {
        "claims": [
            {
                "claim_id": "claim_001",
                "verbatim_quote": "Balanced evidence matters.",
                "anchor_clip": {
                    "start": 10.0,
                    "end": 20.0,
                },
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


def test_export_and_evaluate_pipeline_writes_artifact_and_audit_outputs(tmp_path):
    claims_path = tmp_path / "claims.json"
    speaker_path = tmp_path / "speaker_perspective.json"
    adjudications_path = tmp_path / "adjudications.json"
    evidence_path = tmp_path / "evidence_records.json"

    paper_artifact_path = tmp_path / "paper_artifact.json"
    audit_report_path = tmp_path / "audit_report.json"
    audit_summary_path = tmp_path / "audit_summary.md"
    manifest_path = tmp_path / "evaluation_manifest.json"
    artifact_index_path = tmp_path / "evaluation_artifact_index.json"

    write_json(claims_path, make_claims())
    write_json(speaker_path, make_speaker_perspective())
    write_json(adjudications_path, make_adjudications())
    write_json(evidence_path, make_evidence_records())

    exit_code = run_export_and_evaluate_pipeline(
        [
            "--claims",
            str(claims_path),
            "--speaker-perspective",
            str(speaker_path),
            "--adjudications",
            str(adjudications_path),
            "--evidence-records",
            str(evidence_path),
            "--paper-artifact",
            str(paper_artifact_path),
            "--audit-report",
            str(audit_report_path),
            "--audit-summary",
            str(audit_summary_path),
            "--manifest",
            str(manifest_path),
            "--artifact-index",
            str(artifact_index_path),
            "--run-id",
            "export_eval_test_001",
        ]
    )

    assert exit_code == 0
    assert paper_artifact_path.exists()
    assert audit_report_path.exists()
    assert audit_summary_path.exists()
    assert manifest_path.exists()
    assert artifact_index_path.exists()

    artifact = json.loads(paper_artifact_path.read_text(encoding="utf-8"))
    audit = json.loads(audit_report_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    index = json.loads(artifact_index_path.read_text(encoding="utf-8"))

    assert artifact["claims"][0]["claim_id"] == "claim_001"
    assert audit["publishable"] is True
    assert manifest["metadata"]["run_id"] == "export_eval_test_001"
    assert index["valid"] is True
    assert index["publishable"] is True


def test_export_and_evaluate_pipeline_returns_nonzero_for_unpublishable_artifact(tmp_path):
    claims_path = tmp_path / "claims.json"
    speaker_path = tmp_path / "speaker_perspective.json"
    adjudications_path = tmp_path / "adjudications.json"
    evidence_path = tmp_path / "evidence_records.json"
    rendered_clips_path = tmp_path / "rendered_clips.json"

    paper_artifact_path = tmp_path / "paper_artifact.json"
    audit_report_path = tmp_path / "audit_report.json"

    adjudications = make_adjudications()
    adjudications["adjudications"][0]["balance_score"] = "supportive_skewed"
    adjudications["adjudications"][0]["verdict"] = "well_supported"

    write_json(claims_path, make_claims())
    write_json(speaker_path, make_speaker_perspective())
    write_json(adjudications_path, adjudications)
    write_json(evidence_path, make_evidence_records())
    write_json(
        rendered_clips_path,
        {
            "rendered_clips": [
                {
                    "claim_id": "claim_001",
                    "start": 99.0,
                    "end": 110.0,
                }
            ]
        },
    )

    exit_code = run_export_and_evaluate_pipeline(
        [
            "--claims",
            str(claims_path),
            "--speaker-perspective",
            str(speaker_path),
            "--adjudications",
            str(adjudications_path),
            "--evidence-records",
            str(evidence_path),
            "--rendered-clips",
            str(rendered_clips_path),
            "--paper-artifact",
            str(paper_artifact_path),
            "--audit-report",
            str(audit_report_path),
        ]
    )

    assert exit_code == 1
    assert paper_artifact_path.exists()
    assert audit_report_path.exists()

    audit = json.loads(audit_report_path.read_text(encoding="utf-8"))
    assert audit["publishable"] is False
    assert "evidence_balance" in audit["publishability_decision"]["blocking_axes"]
    assert "clip_anchor_accuracy" in audit["publishability_decision"]["blocking_axes"]
