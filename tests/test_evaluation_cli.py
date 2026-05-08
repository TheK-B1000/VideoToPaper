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
    artifact["rendered_clips"][0]["end"] = 109.0

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


def test_main_can_print_markdown_summary(tmp_path, capsys):
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
            "--print-summary",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "# Inquiry Audit Summary" in captured.out
    assert "**Publishable:** PASS" in captured.out
    assert "| References resolved | 100% |" in captured.out


def test_main_can_write_markdown_summary_file(tmp_path, capsys):
    artifact_path = tmp_path / "paper_artifact.json"
    audit_report_path = tmp_path / "audit_report.json"
    audit_summary_path = tmp_path / "audit_summary.md"

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
            "--audit-summary",
            str(audit_summary_path),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert audit_report_path.exists()
    assert audit_summary_path.exists()
    assert "Audit summary written to:" in captured.out

    summary = audit_summary_path.read_text(encoding="utf-8")

    assert "# Inquiry Audit Summary" in summary
    assert "**Publishable:** PASS" in summary


def test_main_can_write_manifest_file(tmp_path, capsys):
    artifact_path = tmp_path / "paper_artifact.json"
    audit_report_path = tmp_path / "audit_report.json"
    audit_summary_path = tmp_path / "audit_summary.md"
    manifest_path = tmp_path / "manifest.json"

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
            "--audit-summary",
            str(audit_summary_path),
            "--manifest",
            str(manifest_path),
            "--run-id",
            "run_001",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert manifest_path.exists()
    assert "Evaluation manifest written to:" in captured.out

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["paper_artifact_path"] == str(artifact_path)
    assert manifest["audit_report_path"] == str(audit_report_path)
    assert manifest["audit_summary_path"] == str(audit_summary_path)
    assert manifest["metadata"]["run_id"] == "run_001"


def test_main_can_use_evaluation_config_file(tmp_path, capsys):
    artifact_path = tmp_path / "paper_artifact.json"
    audit_report_path = tmp_path / "configured_audit_report.json"
    audit_summary_path = tmp_path / "configured_audit_summary.md"
    manifest_path = tmp_path / "configured_manifest.json"
    config_path = tmp_path / "evaluation_config.json"

    artifact_path.write_text(
        json.dumps(make_clean_paper_artifact()),
        encoding="utf-8",
    )

    config_path.write_text(
        json.dumps(
            {
                "evaluation": {
                    "clip_tolerance_seconds": 1.0,
                    "minimum_balanced_retrieval_ratio": 0.8,
                },
                "outputs": {
                    "audit_report_path": str(audit_report_path),
                    "audit_summary_path": str(audit_summary_path),
                    "manifest_path": str(manifest_path),
                },
                "metadata": {
                    "source": "configured_test",
                },
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--paper-artifact",
            str(artifact_path),
            "--config-path",
            str(config_path),
            "--run-id",
            "configured_run_001",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert audit_report_path.exists()
    assert audit_summary_path.exists()
    assert manifest_path.exists()
    assert "Evaluation manifest written to:" in captured.out

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["metadata"]["source"] == "configured_test"
    assert manifest["metadata"]["run_id"] == "configured_run_001"


def test_main_writes_validation_report_when_artifact_is_malformed(tmp_path):
    artifact = make_clean_paper_artifact()
    del artifact["claims"][0]["anchor_clip"]

    artifact_path = tmp_path / "bad_paper_artifact.json"
    audit_report_path = tmp_path / "audit_report.json"
    validation_report_path = tmp_path / "validation_report.json"

    artifact_path.write_text(json.dumps(artifact), encoding="utf-8")

    with pytest.raises(ValueError, match="Paper artifact validation failed"):
        main(
            [
                "--paper-artifact",
                str(artifact_path),
                "--audit-report",
                str(audit_report_path),
                "--validation-report",
                str(validation_report_path),
            ]
        )

    assert not audit_report_path.exists()
    assert validation_report_path.exists()

    payload = json.loads(validation_report_path.read_text(encoding="utf-8"))

    assert payload["valid"] is False
    assert payload["error_count"] >= 1


def test_main_writes_validation_summary_when_artifact_is_malformed(tmp_path):
    artifact = make_clean_paper_artifact()
    del artifact["claims"][0]["anchor_clip"]

    artifact_path = tmp_path / "bad_paper_artifact.json"
    audit_report_path = tmp_path / "audit_report.json"
    validation_report_path = tmp_path / "validation_report.json"
    validation_summary_path = tmp_path / "validation_summary.md"

    artifact_path.write_text(json.dumps(artifact), encoding="utf-8")

    with pytest.raises(ValueError, match="Paper artifact validation failed"):
        main(
            [
                "--paper-artifact",
                str(artifact_path),
                "--audit-report",
                str(audit_report_path),
                "--validation-report",
                str(validation_report_path),
                "--validation-summary",
                str(validation_summary_path),
            ]
        )

    assert not audit_report_path.exists()
    assert validation_report_path.exists()
    assert validation_summary_path.exists()

    summary = validation_summary_path.read_text(encoding="utf-8")

    assert "# Paper Artifact Validation Summary" in summary
    assert "**Valid:** FAIL" in summary
    assert "claims[0] is missing anchor_clip." in summary


def test_main_can_print_validation_summary_when_artifact_is_malformed(tmp_path, capsys):
    artifact = make_clean_paper_artifact()
    del artifact["claims"][0]["anchor_clip"]

    artifact_path = tmp_path / "bad_paper_artifact.json"
    audit_report_path = tmp_path / "audit_report.json"
    validation_report_path = tmp_path / "validation_report.json"

    artifact_path.write_text(json.dumps(artifact), encoding="utf-8")

    with pytest.raises(ValueError, match="Paper artifact validation failed"):
        main(
            [
                "--paper-artifact",
                str(artifact_path),
                "--audit-report",
                str(audit_report_path),
                "--validation-report",
                str(validation_report_path),
                "--print-validation-summary",
            ]
        )

    captured = capsys.readouterr()

    assert "# Paper Artifact Validation Summary" in captured.out
    assert "**Valid:** FAIL" in captured.out
