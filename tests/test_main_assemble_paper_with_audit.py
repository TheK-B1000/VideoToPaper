import json
import subprocess
import sys
from pathlib import Path


def _source_registry() -> dict:
    return {
        "source": {
            "video_id": "ABC123",
            "title": "What Most People Get Wrong About Reinforcement Learning",
            "url": "https://www.youtube.com/watch?v=ABC123",
            "embed_base_url": "https://www.youtube-nocookie.com/embed/ABC123",
            "speaker": {
                "name": "Dr. Jane Smith",
                "credentials": "Professor of Computer Science",
            },
        }
    }


def _claim_inventory() -> dict:
    return {
        "claims": [
            {
                "claim_id": "claim_0042",
                "verbatim_quote": "non-stationarity makes single-agent algorithms fundamentally unsuited",
                "claim_type": "empirical_technical",
                "anchor_clip": {
                    "start": 252.4,
                    "end": 263.0,
                },
                "embed_url": "https://www.youtube-nocookie.com/embed/ABC123?start=252&end=263&rel=0",
            }
        ]
    }


def _evidence_integration() -> dict:
    return {
        "speaker_perspective": (
            "The speaker argues that naive single-agent assumptions become fragile "
            "when moved into adaptive multi-agent environments."
        ),
        "evidence_records": [
            {
                "evidence_id": "ev_001",
                "claim_id": "claim_0042",
                "title": "Multi-Agent Reinforcement Learning: A Selective Overview",
                "source": "Journal of Artificial Intelligence Research",
                "url": "https://example.org/marl-overview",
                "tier": 1,
                "stance": "qualifies",
                "identifier": "doi:10.0000/example",
                "key_finding": (
                    "Multi-agent settings can violate stationarity assumptions, "
                    "but specialized approaches address this problem."
                ),
            }
        ],
        "adjudications": [
            {
                "claim_id": "claim_0042",
                "verdict": "well_supported_with_qualifications",
                "confidence": "high",
                "narrative": (
                    "The speaker's claim is directionally supported, but the literature "
                    "shows that specialized multi-agent methods complicate the strongest version."
                ),
                "supports": [],
                "complicates": [],
                "contradicts": [],
                "qualifies": ["ev_001"],
            }
        ],
        "limitations": [
            "This pass relies on retrieved metadata and does not yet verify full-text source claims."
        ],
    }


def test_main_assemble_paper_with_audit_writes_all_outputs(tmp_path: Path) -> None:
    source_registry_path = tmp_path / "source_registry.json"
    claim_inventory_path = tmp_path / "claim_inventory.json"
    evidence_integration_path = tmp_path / "evidence_integration.json"
    paper_spec_output_path = tmp_path / "paper_spec.json"
    html_output_path = tmp_path / "inquiry_paper.html"
    audit_report_path = tmp_path / "html_audit_report.json"

    source_registry_path.write_text(json.dumps(_source_registry()), encoding="utf-8")
    claim_inventory_path.write_text(json.dumps(_claim_inventory()), encoding="utf-8")
    evidence_integration_path.write_text(
        json.dumps(_evidence_integration()),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "main.py",
            "--stage",
            "assemble_paper",
            "--source-registry-path",
            str(source_registry_path),
            "--claim-inventory-path",
            str(claim_inventory_path),
            "--evidence-integration-path",
            str(evidence_integration_path),
            "--paper-spec-output-path",
            str(paper_spec_output_path),
            "--html-output-path",
            str(html_output_path),
            "--html-audit-report-path",
            str(audit_report_path),
            "--audit-after-assembly",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr

    assert "Paper spec written to:" in result.stdout
    assert "HTML paper written to:" in result.stdout
    assert "HTML audit report written to:" in result.stdout
    assert "HTML audit passed: True" in result.stdout

    assert paper_spec_output_path.exists()
    assert html_output_path.exists()
    assert audit_report_path.exists()

    audit_report = json.loads(audit_report_path.read_text(encoding="utf-8"))

    assert audit_report["passed"] is True
    assert audit_report["checks_run"] == 5
    assert audit_report["findings"] == []

    html = html_output_path.read_text(encoding="utf-8")

    assert '<article class="inquiry-paper">' in html
    assert "The Speaker's Perspective" in html
    assert "Claims Under Examination" in html
    assert "Evidence Review" in html
    assert "Open Questions &amp; Limitations" in html or "Open Questions & Limitations" in html
    assert "References" in html
    assert (
        "https://www.youtube-nocookie.com/embed/ABC123?start=252&end=263&rel=0" in html
        or "https://www.youtube-nocookie.com/embed/ABC123?start=252&amp;end=263&amp;rel=0"
        in html
    )


def test_main_assemble_paper_without_audit_does_not_write_audit_report(
    tmp_path: Path,
) -> None:
    source_registry_path = tmp_path / "source_registry.json"
    claim_inventory_path = tmp_path / "claim_inventory.json"
    evidence_integration_path = tmp_path / "evidence_integration.json"
    paper_spec_output_path = tmp_path / "paper_spec.json"
    html_output_path = tmp_path / "inquiry_paper.html"
    audit_report_path = tmp_path / "html_audit_report.json"

    source_registry_path.write_text(json.dumps(_source_registry()), encoding="utf-8")
    claim_inventory_path.write_text(json.dumps(_claim_inventory()), encoding="utf-8")
    evidence_integration_path.write_text(
        json.dumps(_evidence_integration()),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "main.py",
            "--stage",
            "assemble_paper",
            "--source-registry-path",
            str(source_registry_path),
            "--claim-inventory-path",
            str(claim_inventory_path),
            "--evidence-integration-path",
            str(evidence_integration_path),
            "--paper-spec-output-path",
            str(paper_spec_output_path),
            "--html-output-path",
            str(html_output_path),
            "--html-audit-report-path",
            str(audit_report_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr

    assert paper_spec_output_path.exists()
    assert html_output_path.exists()
    assert not audit_report_path.exists()

    assert "HTML audit passed" not in result.stdout
