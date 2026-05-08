import json

import pytest

from src.evaluation.evaluation_cli import load_paper_artifact, main


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


def test_load_paper_artifact_reads_json(tmp_path):
    artifact_path = tmp_path / "paper_artifact.json"
    artifact = make_clean_paper_artifact()

    artifact_path.write_text(json.dumps(artifact), encoding="utf-8")

    loaded = load_paper_artifact(artifact_path)

    assert loaded["claims"][0]["claim_id"] == "claim_001"


def test_load_paper_artifact_raises_for_missing_file(tmp_path):
    missing_path = tmp_path / "missing.json"

    with pytest.raises(FileNotFoundError):
        load_paper_artifact(missing_path)


def test_main_writes_audit_report_for_publishable_artifact(tmp_path, capsys):
    artifact_path = tmp_path / "paper_artifact.json"
    audit_report_path = tmp_path / "audit_report.json"

    artifact_path.write_text(
        json.dumps(make_clean_paper_artifact()),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--paper-artifact",
            str(artifact_path),
            "--audit-report",
            str(audit_report_path),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert audit_report_path.exists()
    assert "Audit report written to:" in captured.out
    assert "Evaluation result: publishable" in captured.out


def test_main_returns_nonzero_for_unpublishable_artifact(tmp_path, capsys):
    artifact = make_clean_paper_artifact()
    artifact["rendered_clips"][0]["start"] = 99.0

    artifact_path = tmp_path / "paper_artifact.json"
    audit_report_path = tmp_path / "audit_report.json"

    artifact_path.write_text(json.dumps(artifact), encoding="utf-8")

    exit_code = main(
        [
            "--paper-artifact",
            str(artifact_path),
            "--audit-report",
            str(audit_report_path),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(audit_report_path.read_text(encoding="utf-8"))

    assert exit_code == 1
    assert payload["publishable"] is False
    assert "Evaluation result: not publishable" in captured.out
