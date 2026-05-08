import json

from src.evaluation.evaluation_runner import run_paper_evaluation


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


def test_run_paper_evaluation_writes_audit_report(tmp_path):
    paper_artifact = make_clean_paper_artifact()
    audit_report_path = tmp_path / "runs" / "audit_report.json"

    result = run_paper_evaluation(
        paper_artifact=paper_artifact,
        audit_report_path=audit_report_path,
    )

    assert result.publishable is True
    assert result.audit_report_path == audit_report_path
    assert audit_report_path.exists()

    payload = json.loads(audit_report_path.read_text(encoding="utf-8"))

    assert payload["publishable"] is True
    assert payload["steelman_accuracy"]["verbatim_anchored_assertions"] == "100%"
    assert payload["evidence_balance"]["claims_with_balanced_retrieval"] == "100%"
    assert payload["citation_integrity"]["references_resolved"] == "100%"
    assert payload["clip_anchor_accuracy"]["clips_within_tolerance"] == "100%"


def test_run_paper_evaluation_returns_not_publishable_for_bad_clip(tmp_path):
    paper_artifact = make_clean_paper_artifact()
    paper_artifact["rendered_clips"][0]["start"] = 3.0

    audit_report_path = tmp_path / "audit_report.json"

    result = run_paper_evaluation(
        paper_artifact=paper_artifact,
        audit_report_path=audit_report_path,
    )

    assert result.publishable is False

    payload = json.loads(audit_report_path.read_text(encoding="utf-8"))

    assert payload["publishable"] is False
    assert payload["clip_anchor_accuracy"]["clips_within_tolerance"] == "0%"
    assert payload["clip_anchor_accuracy"]["drift_detected"][0]["claim_id"] == "claim_001"