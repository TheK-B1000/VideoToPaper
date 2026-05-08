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


def test_main_build_paper_spec_stage_writes_spec_file(tmp_path: Path) -> None:
    source_registry_path = tmp_path / "source_registry.json"
    claim_inventory_path = tmp_path / "claim_inventory.json"
    evidence_integration_path = tmp_path / "evidence_integration.json"
    paper_spec_output_path = tmp_path / "paper_spec.json"

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
            "build_paper_spec",
            "--source-registry-path",
            str(source_registry_path),
            "--claim-inventory-path",
            str(claim_inventory_path),
            "--evidence-integration-path",
            str(evidence_integration_path),
            "--paper-spec-output-path",
            str(paper_spec_output_path),
            "--paper-title",
            "Custom Inquiry Paper",
            "--paper-abstract",
            "Custom paper abstract.",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Paper spec written to:" in result.stdout
    assert paper_spec_output_path.exists()

    spec = json.loads(paper_spec_output_path.read_text(encoding="utf-8"))

    assert spec["title"] == "Custom Inquiry Paper"
    assert spec["abstract"] == "Custom paper abstract."
    assert spec["video"]["video_id"] == "ABC123"
    assert spec["video"]["speaker_name"] == "Dr. Jane Smith"

    assert len(spec["claims"]) == 1
    assert spec["claims"][0]["claim_id"] == "claim_0042"
    assert spec["claims"][0]["anchor_clip_start"] == 252.4
    assert spec["claims"][0]["anchor_clip_end"] == 263.0

    assert len(spec["evidence_records"]) == 1
    assert spec["evidence_records"][0]["evidence_id"] == "ev_001"

    assert len(spec["adjudications"]) == 1
    assert spec["adjudications"][0]["verdict"] == "well_supported_with_qualifications"

    assert spec["limitations"] == [
        "This pass relies on retrieved metadata and does not yet verify full-text source claims."
    ]


def test_main_build_paper_spec_stage_fails_for_missing_input(tmp_path: Path) -> None:
    claim_inventory_path = tmp_path / "claim_inventory.json"
    evidence_integration_path = tmp_path / "evidence_integration.json"
    paper_spec_output_path = tmp_path / "paper_spec.json"

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
            "build_paper_spec",
            "--source-registry-path",
            str(tmp_path / "missing_source_registry.json"),
            "--claim-inventory-path",
            str(claim_inventory_path),
            "--evidence-integration-path",
            str(evidence_integration_path),
            "--paper-spec-output-path",
            str(paper_spec_output_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert not paper_spec_output_path.exists()
