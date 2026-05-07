from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Mapping, Sequence


class EvidenceStance(str, Enum):
    SUPPORTS = "supports"
    COMPLICATES = "complicates"
    CONTRADICTS = "contradicts"
    QUALIFIES = "qualifies"


class RetrievalBalance(str, Enum):
    BALANCED = "balanced"
    SUPPORTIVE_SKEWED = "supportive_skewed"
    CONTRARY_SKEWED = "contrary_skewed"
    INSUFFICIENT = "insufficient"


class ClaimVerdict(str, Enum):
    WELL_SUPPORTED = "well_supported"
    WELL_SUPPORTED_WITH_QUALIFICATIONS = "well_supported_with_qualifications"
    MIXED_OR_CONTESTED = "mixed_or_contested"
    CONTRADICTED_BY_EVIDENCE = "contradicted_by_evidence"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    REQUIRES_MANUAL_REVIEW = "requires_manual_review"


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class VerdictDecision:
    verdict: ClaimVerdict
    confidence: ConfidenceLevel
    should_generate_narrative: bool
    guard_reason: str | None = None


def normalize_stance(raw_stance: str) -> EvidenceStance:
    """
    Normalize external evidence stance labels into the integration taxonomy.

    This intentionally accepts only known stance values. Evidence integration
    should not silently invent categories because the downstream HTML paper
    depends on stable stance buckets.
    """
    try:
        return EvidenceStance(raw_stance.strip().lower())
    except ValueError as exc:
        raise ValueError(f"Unsupported evidence stance: {raw_stance!r}") from exc


def count_evidence_by_stance(
    evidence_records: Sequence[Mapping[str, object]],
) -> dict[EvidenceStance, int]:
    counts = {
        EvidenceStance.SUPPORTS: 0,
        EvidenceStance.COMPLICATES: 0,
        EvidenceStance.CONTRADICTS: 0,
        EvidenceStance.QUALIFIES: 0,
    }

    for record in evidence_records:
        raw_stance = record.get("stance")

        if not isinstance(raw_stance, str):
            raise ValueError(f"Evidence record is missing a string stance: {record!r}")

        stance = normalize_stance(raw_stance)
        counts[stance] += 1

    return counts


def classify_retrieval_balance(
    evidence_records: Sequence[Mapping[str, object]],
) -> RetrievalBalance:
    """
    Classify whether retrieved evidence is balanced enough for adjudication.

    The goal is not to force false symmetry. The goal is to prevent the
    integrator from writing confident analytical prose from one-sided retrieval.
    """
    if not evidence_records:
        return RetrievalBalance.INSUFFICIENT

    counts = count_evidence_by_stance(evidence_records)

    supportive_count = counts[EvidenceStance.SUPPORTS]
    contrary_count = (
        counts[EvidenceStance.CONTRADICTS]
        + counts[EvidenceStance.COMPLICATES]
        + counts[EvidenceStance.QUALIFIES]
    )

    if supportive_count == 0 and contrary_count == 0:
        return RetrievalBalance.INSUFFICIENT

    if supportive_count > 0 and contrary_count > 0:
        return RetrievalBalance.BALANCED

    if supportive_count > 0:
        return RetrievalBalance.SUPPORTIVE_SKEWED

    return RetrievalBalance.CONTRARY_SKEWED


def decide_claim_verdict(
    evidence_records: Sequence[Mapping[str, object]],
    *,
    allow_skewed_adjudication: bool = False,
) -> VerdictDecision:
    """
    Map evidence patterns into a stable claim-level verdict.

    This is deliberately deterministic. Later, the LLM can write the narrative,
    but it should not be the first authority deciding whether a claim is
    supported, complicated, contradicted, or under-evidenced.
    """
    balance = classify_retrieval_balance(evidence_records)

    if balance == RetrievalBalance.INSUFFICIENT:
        return VerdictDecision(
            verdict=ClaimVerdict.INSUFFICIENT_EVIDENCE,
            confidence=ConfidenceLevel.LOW,
            should_generate_narrative=False,
            guard_reason="No usable evidence records were retrieved.",
        )

    if balance != RetrievalBalance.BALANCED and not allow_skewed_adjudication:
        return VerdictDecision(
            verdict=ClaimVerdict.REQUIRES_MANUAL_REVIEW,
            confidence=ConfidenceLevel.LOW,
            should_generate_narrative=False,
            guard_reason=f"Retrieval is {balance.value}; refusing to adjudicate from skewed evidence.",
        )

    counts = count_evidence_by_stance(evidence_records)

    supports = counts[EvidenceStance.SUPPORTS]
    complicates = counts[EvidenceStance.COMPLICATES]
    contradicts = counts[EvidenceStance.CONTRADICTS]
    qualifies = counts[EvidenceStance.QUALIFIES]

    if contradicts > supports:
        return VerdictDecision(
            verdict=ClaimVerdict.CONTRADICTED_BY_EVIDENCE,
            confidence=ConfidenceLevel.MEDIUM,
            should_generate_narrative=True,
        )

    if supports > 0 and contradicts == 0 and complicates == 0 and qualifies == 0:
        return VerdictDecision(
            verdict=ClaimVerdict.WELL_SUPPORTED,
            confidence=ConfidenceLevel.HIGH,
            should_generate_narrative=True,
        )

    if supports > 0 and contradicts == 0 and (complicates > 0 or qualifies > 0):
        return VerdictDecision(
            verdict=ClaimVerdict.WELL_SUPPORTED_WITH_QUALIFICATIONS,
            confidence=ConfidenceLevel.HIGH,
            should_generate_narrative=True,
        )

    if supports > 0 and (contradicts > 0 or complicates > 0 or qualifies > 0):
        return VerdictDecision(
            verdict=ClaimVerdict.MIXED_OR_CONTESTED,
            confidence=ConfidenceLevel.MEDIUM,
            should_generate_narrative=True,
        )

    return VerdictDecision(
        verdict=ClaimVerdict.REQUIRES_MANUAL_REVIEW,
        confidence=ConfidenceLevel.LOW,
        should_generate_narrative=False,
        guard_reason="Evidence pattern did not match a safe adjudication rule.",
    )


def summarize_evidence_sources_by_stance(
    evidence_records: Iterable[Mapping[str, object]],
) -> dict[str, list[str]]:
    """
    Build the compact evidence_summary payload expected by Week 7.

    Each source label should be stable enough for the paper renderer,
    for example: "Foerster 2018", "Lanctot 2017", or a title fallback.
    """
    summary = {
        EvidenceStance.SUPPORTS.value: [],
        EvidenceStance.COMPLICATES.value: [],
        EvidenceStance.CONTRADICTS.value: [],
        EvidenceStance.QUALIFIES.value: [],
    }

    for record in evidence_records:
        raw_stance = record.get("stance")
        if not isinstance(raw_stance, str):
            raise ValueError(f"Evidence record is missing a string stance: {record!r}")

        stance = normalize_stance(raw_stance)

        source_label = (
            record.get("citation_label")
            or record.get("source")
            or record.get("title")
            or record.get("identifier")
        )

        if not isinstance(source_label, str) or not source_label.strip():
            raise ValueError(f"Evidence record is missing a usable source label: {record!r}")

        summary[stance.value].append(source_label.strip())

    return summary
