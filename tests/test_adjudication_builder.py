import pytest

from src.integration.adjudication_builder import (
    AdjudicationRecord,
    build_adjudication_record,
    build_interactive_payload,
    build_speaker_claim_summary,
)


def test_builds_speaker_claim_summary_from_verbatim_quote():
    claim = {
        "claim_id": "claim_001",
        "verbatim_quote": "Multi-agent systems become unstable when agents learn at the same time.",
    }

    summary = build_speaker_claim_summary(claim)

    assert summary == (
        'The speaker claims: "Multi-agent systems become unstable when agents learn at the same time."'
    )


def test_rejects_claim_without_verbatim_quote():
    claim = {
        "claim_id": "claim_001",
    }

    with pytest.raises(ValueError, match="verbatim_quote"):
        build_speaker_claim_summary(claim)


def test_builds_interactive_payload_grouped_by_stance():
    evidence_records = [
        {
            "stance": "supports",
            "citation_label": "Foerster 2018",
            "title": "Learning with Opponent-Learning Awareness",
            "tier": 1,
            "identifier": "doi:example-support",
            "key_finding": "Opponent learning can affect training dynamics.",
        },
        {
            "stance": "qualifies",
            "citation_label": "Vinyals 2019",
            "title": "Grandmaster Level in StarCraft II",
            "tier": 1,
            "identifier": "doi:example-qualify",
            "key_finding": "Large-scale training can mitigate some instability.",
        },
        {
            "stance": "contradicts",
            "citation_label": "Contrary Example 2021",
            "title": "A Contrary Finding",
            "tier": 2,
            "identifier": "url:contrary",
            "key_finding": "Some environments show stable learning.",
        },
    ]

    payload = build_interactive_payload(evidence_records)

    assert len(payload["supporting_sources"]) == 1
    assert len(payload["qualifying_sources"]) == 1
    assert len(payload["contrary_sources"]) == 1
    assert len(payload["complicating_sources"]) == 0

    assert payload["supporting_sources"][0]["citation_label"] == "Foerster 2018"
    assert payload["qualifying_sources"][0]["tier"] == 1
    assert payload["contrary_sources"][0]["identifier"] == "url:contrary"


def test_builds_complete_adjudication_record():
    claim = {
        "claim_id": "claim_001",
        "verbatim_quote": "Non-stationarity makes multi-agent learning difficult.",
    }

    evidence_records = [
        {
            "stance": "supports",
            "citation_label": "Foerster 2018",
            "title": "Learning with Opponent-Learning Awareness",
            "source": "Journal Example",
            "tier": 1,
            "identifier": "doi:example-support",
            "url": "https://example.com/support",
            "key_finding": "Opponent updates create non-stationary learning dynamics.",
        },
        {
            "stance": "qualifies",
            "citation_label": "Vinyals 2019",
            "title": "Grandmaster Level in StarCraft II",
            "source": "Nature",
            "tier": 1,
            "identifier": "doi:example-qualify",
            "url": "https://example.com/qualify",
            "key_finding": "Scale and self-play can reduce some practical instability.",
        },
    ]

    record = build_adjudication_record(claim, evidence_records)

    assert isinstance(record, AdjudicationRecord)
    assert record.claim_id == "claim_001"
    assert record.verdict == "well_supported_with_qualifications"
    assert record.confidence == "high"
    assert record.guard_reason is None

    assert record.evidence_summary["supports"] == ["Foerster 2018"]
    assert record.evidence_summary["qualifies"] == ["Vinyals 2019"]

    assert len(record.interactive_payload["supporting_sources"]) == 1
    assert len(record.interactive_payload["qualifying_sources"]) == 1

    assert "Supporting evidence includes: Foerster 2018." in record.narrative
    assert "Qualifying evidence includes: Vinyals 2019." in record.narrative


def test_skewed_evidence_record_gets_guard_reason():
    claim = {
        "claim_id": "claim_002",
        "verbatim_quote": "This claim only has supportive evidence so far.",
    }

    evidence_records = [
        {
            "stance": "supports",
            "citation_label": "Support Only 2020",
            "title": "Support Only Paper",
            "tier": 1,
            "identifier": "doi:support-only",
        }
    ]

    record = build_adjudication_record(claim, evidence_records)

    assert record.verdict == "requires_manual_review"
    assert record.confidence == "low"
    assert record.guard_reason is not None
    assert "skewed" in record.guard_reason
    assert "not balanced enough" in record.narrative


def test_rejects_unknown_stance_in_payload():
    evidence_records = [
        {
            "stance": "unclear",
            "citation_label": "Unclear 2022",
        }
    ]

    with pytest.raises(ValueError, match="Unsupported evidence stance"):
        build_interactive_payload(evidence_records)
