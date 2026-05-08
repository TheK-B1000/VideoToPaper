import json
from pathlib import Path

import pytest

from src.paper.paper_spec_builder import (
    PaperSpecBuilderError,
    build_paper_spec,
    build_paper_spec_dict,
)


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


def test_build_paper_spec_dict_combines_upstream_artifacts() -> None:
    spec = build_paper_spec_dict(
        source_registry=_source_registry(),
        claim_inventory=_claim_inventory(),
        evidence_integration=_evidence_integration(),
    )

    assert spec["title"] == (
        "Inquiry Paper: What Most People Get Wrong About Reinforcement Learning"
    )
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


def test_build_paper_spec_writes_json_file(tmp_path: Path) -> None:
    source_path = tmp_path / "source_registry.json"
    claims_path = tmp_path / "claim_inventory.json"
    integration_path = tmp_path / "evidence_integration.json"
    output_path = tmp_path / "paper_spec.json"

    source_path.write_text(json.dumps(_source_registry()), encoding="utf-8")
    claims_path.write_text(json.dumps(_claim_inventory()), encoding="utf-8")
    integration_path.write_text(json.dumps(_evidence_integration()), encoding="utf-8")

    result = build_paper_spec(
        source_registry_path=source_path,
        claim_inventory_path=claims_path,
        evidence_integration_path=integration_path,
        output_path=output_path,
        title="Custom Inquiry Paper",
        abstract="Custom abstract.",
    )

    assert result == output_path
    assert output_path.exists()

    spec = json.loads(output_path.read_text(encoding="utf-8"))

    assert spec["title"] == "Custom Inquiry Paper"
    assert spec["abstract"] == "Custom abstract."
    assert spec["video"]["embed_base_url"] == "https://www.youtube-nocookie.com/embed/ABC123"


def test_build_paper_spec_dict_uses_steelman_blocks_when_speaker_perspective_missing() -> None:
    integration = _evidence_integration()
    integration.pop("speaker_perspective")
    integration["steelman"] = {
        "narrative_blocks": [
            {"text": "First charitable block."},
            {"text": "Second charitable block."},
        ]
    }

    spec = build_paper_spec_dict(
        source_registry=_source_registry(),
        claim_inventory=_claim_inventory(),
        evidence_integration=integration,
    )

    assert spec["speaker_perspective"] == "First charitable block.\n\nSecond charitable block."


def test_build_paper_spec_dict_rejects_empty_claim_inventory() -> None:
    with pytest.raises(PaperSpecBuilderError, match="without claims"):
        build_paper_spec_dict(
            source_registry=_source_registry(),
            claim_inventory={"claims": []},
            evidence_integration=_evidence_integration(),
        )


def test_build_paper_spec_rejects_missing_input_file(tmp_path: Path) -> None:
    claims_path = tmp_path / "claim_inventory.json"
    integration_path = tmp_path / "evidence_integration.json"
    output_path = tmp_path / "paper_spec.json"

    claims_path.write_text(json.dumps(_claim_inventory()), encoding="utf-8")
    integration_path.write_text(json.dumps(_evidence_integration()), encoding="utf-8")

    with pytest.raises(PaperSpecBuilderError, match="Missing source registry file"):
        build_paper_spec(
            source_registry_path=tmp_path / "missing_source.json",
            claim_inventory_path=claims_path,
            evidence_integration_path=integration_path,
            output_path=output_path,
        )


def test_build_paper_spec_dict_rejects_bad_anchor_clip() -> None:
    inventory = _claim_inventory()
    inventory["claims"][0]["anchor_clip"] = {"start": "bad", "end": 263.0}

    with pytest.raises(PaperSpecBuilderError, match="start must be a number"):
        build_paper_spec_dict(
            source_registry=_source_registry(),
            claim_inventory=inventory,
            evidence_integration=_evidence_integration(),
        )