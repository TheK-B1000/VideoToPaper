import pytest

from src.integration.evidence_verdicts import (
    ClaimVerdict,
    ConfidenceLevel,
    EvidenceStance,
    RetrievalBalance,
    classify_retrieval_balance,
    count_evidence_by_stance,
    decide_claim_verdict,
    summarize_evidence_sources_by_stance,
)


def test_counts_evidence_by_stance():
    records = [
        {"stance": "supports", "citation_label": "Foerster 2018"},
        {"stance": "qualifies", "citation_label": "Vinyals 2019"},
        {"stance": "complicates", "citation_label": "Lanctot 2017"},
    ]

    counts = count_evidence_by_stance(records)

    assert counts[EvidenceStance.SUPPORTS] == 1
    assert counts[EvidenceStance.QUALIFIES] == 1
    assert counts[EvidenceStance.COMPLICATES] == 1
    assert counts[EvidenceStance.CONTRADICTS] == 0


def test_balanced_retrieval_when_support_and_qualification_exist():
    records = [
        {"stance": "supports", "citation_label": "Foerster 2018"},
        {"stance": "qualifies", "citation_label": "Vinyals 2019"},
    ]

    assert classify_retrieval_balance(records) == RetrievalBalance.BALANCED


def test_supportive_skewed_retrieval_is_flagged():
    records = [
        {"stance": "supports", "citation_label": "Foerster 2018"},
        {"stance": "supports", "citation_label": "Hernandez-Leal 2019"},
    ]

    assert classify_retrieval_balance(records) == RetrievalBalance.SUPPORTIVE_SKEWED


def test_empty_retrieval_is_insufficient():
    assert classify_retrieval_balance([]) == RetrievalBalance.INSUFFICIENT


def test_skewed_retrieval_refuses_adjudication_by_default():
    records = [
        {"stance": "supports", "citation_label": "Foerster 2018"},
    ]

    decision = decide_claim_verdict(records)

    assert decision.verdict == ClaimVerdict.REQUIRES_MANUAL_REVIEW
    assert decision.confidence == ConfidenceLevel.LOW
    assert decision.should_generate_narrative is False
    assert decision.guard_reason is not None
    assert "skewed" in decision.guard_reason


def test_well_supported_with_qualifications_verdict():
    records = [
        {"stance": "supports", "citation_label": "Foerster 2018"},
        {"stance": "qualifies", "citation_label": "Vinyals 2019"},
    ]

    decision = decide_claim_verdict(records)

    assert decision.verdict == ClaimVerdict.WELL_SUPPORTED_WITH_QUALIFICATIONS
    assert decision.confidence == ConfidenceLevel.HIGH
    assert decision.should_generate_narrative is True
    assert decision.guard_reason is None


def test_mixed_or_contested_verdict_when_support_and_contradiction_exist():
    records = [
        {"stance": "supports", "citation_label": "Foerster 2018"},
        {"stance": "contradicts", "citation_label": "Example Contrary Paper 2021"},
    ]

    decision = decide_claim_verdict(records)

    assert decision.verdict == ClaimVerdict.MIXED_OR_CONTESTED
    assert decision.confidence == ConfidenceLevel.MEDIUM
    assert decision.should_generate_narrative is True


def test_contradicted_by_evidence_when_contradictions_outnumber_supports():
    records = [
        {"stance": "supports", "citation_label": "Support Paper 2018"},
        {"stance": "contradicts", "citation_label": "Contrary Paper 2020"},
        {"stance": "contradicts", "citation_label": "Contrary Paper 2021"},
    ]

    decision = decide_claim_verdict(records)

    assert decision.verdict == ClaimVerdict.CONTRADICTED_BY_EVIDENCE
    assert decision.confidence == ConfidenceLevel.MEDIUM
    assert decision.should_generate_narrative is True


def test_summarizes_evidence_sources_by_stance():
    records = [
        {"stance": "supports", "citation_label": "Foerster 2018"},
        {"stance": "complicates", "source": "Lanctot et al."},
        {"stance": "qualifies", "title": "AlphaStar Study"},
    ]

    summary = summarize_evidence_sources_by_stance(records)

    assert summary["supports"] == ["Foerster 2018"]
    assert summary["complicates"] == ["Lanctot et al."]
    assert summary["qualifies"] == ["AlphaStar Study"]
    assert summary["contradicts"] == []


def test_rejects_unknown_evidence_stance():
    records = [
        {"stance": "kind_of_supports", "citation_label": "Fake 2024"},
    ]

    with pytest.raises(ValueError, match="Unsupported evidence stance"):
        count_evidence_by_stance(records)
