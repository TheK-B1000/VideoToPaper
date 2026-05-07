from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from src.integration.evidence_verdicts import (
    ClaimVerdict,
    VerdictDecision,
    decide_claim_verdict,
    summarize_evidence_sources_by_stance,
)


@dataclass(frozen=True)
class AdjudicationRecord:
    claim_id: str
    speaker_claim_summary: str
    evidence_summary: dict[str, list[str]]
    verdict: str
    confidence: str
    narrative: str
    interactive_payload: dict[str, list[dict[str, Any]]]
    guard_reason: str | None = None


def build_speaker_claim_summary(claim: Mapping[str, Any]) -> str:
    """
    Create a compact summary of the speaker's claim.

    This is intentionally conservative. Week 7 should not invent analysis here.
    The summary starts from the verbatim quote so the adjudication stays grounded.
    """
    claim_id = claim.get("claim_id")
    verbatim_quote = claim.get("verbatim_quote")

    if not isinstance(claim_id, str) or not claim_id.strip():
        raise ValueError("Claim is missing a valid claim_id.")

    if not isinstance(verbatim_quote, str) or not verbatim_quote.strip():
        raise ValueError(f"Claim {claim_id!r} is missing a valid verbatim_quote.")

    return f'The speaker claims: "{verbatim_quote.strip()}"'


def build_interactive_payload(
    evidence_records: Sequence[Mapping[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """
    Build the structured payload that the future HTML evidence-trail component
    will consume.

    Records are grouped by stance so the frontend can toggle between supporting,
    contrary, and qualifying evidence without re-processing the source data.
    """
    payload = {
        "supporting_sources": [],
        "contrary_sources": [],
        "qualifying_sources": [],
        "complicating_sources": [],
    }

    for record in evidence_records:
        stance = record.get("stance")

        if not isinstance(stance, str):
            raise ValueError(f"Evidence record is missing a valid stance: {record!r}")

        normalized = stance.strip().lower()

        payload_record = {
            "title": record.get("title"),
            "source": record.get("source"),
            "citation_label": record.get("citation_label"),
            "identifier": record.get("identifier"),
            "url": record.get("url"),
            "tier": record.get("tier"),
            "key_finding": record.get("key_finding"),
            "stance": normalized,
        }

        if normalized == "supports":
            payload["supporting_sources"].append(payload_record)
        elif normalized == "contradicts":
            payload["contrary_sources"].append(payload_record)
        elif normalized == "qualifies":
            payload["qualifying_sources"].append(payload_record)
        elif normalized == "complicates":
            payload["complicating_sources"].append(payload_record)
        else:
            raise ValueError(f"Unsupported evidence stance: {stance!r}")

    return payload


def build_placeholder_narrative(
    claim: Mapping[str, Any],
    decision: VerdictDecision,
    evidence_summary: Mapping[str, list[str]],
) -> str:
    """
    Build a deterministic placeholder narrative.

    This keeps Week 7 testable before we add LLM-assisted prose generation.
    Later, this function can be replaced by a safe LLM-backed narrative generator.
    """
    claim_id = claim.get("claim_id")

    if not isinstance(claim_id, str) or not claim_id.strip():
        raise ValueError("Claim is missing a valid claim_id.")

    if decision.verdict == ClaimVerdict.REQUIRES_MANUAL_REVIEW:
        return (
            "This claim was not adjudicated because the retrieved evidence was not "
            "balanced enough for a reliable synthesis."
        )

    if decision.verdict == ClaimVerdict.INSUFFICIENT_EVIDENCE:
        return (
            "This claim was not adjudicated because there was not enough usable "
            "retrieved evidence to support a fair analysis."
        )

    supports = evidence_summary.get("supports", [])
    complicates = evidence_summary.get("complicates", [])
    contradicts = evidence_summary.get("contradicts", [])
    qualifies = evidence_summary.get("qualifies", [])

    parts = []

    if supports:
        parts.append(f"Supporting evidence includes: {', '.join(supports)}.")

    if qualifies:
        parts.append(f"Qualifying evidence includes: {', '.join(qualifies)}.")

    if complicates:
        parts.append(f"Complicating evidence includes: {', '.join(complicates)}.")

    if contradicts:
        parts.append(f"Contrary evidence includes: {', '.join(contradicts)}.")

    if not parts:
        return "No narrative was generated because no evidence summary was available."

    return " ".join(parts)


def build_adjudication_record(
    claim: Mapping[str, Any],
    evidence_records: Sequence[Mapping[str, Any]],
    *,
    allow_skewed_adjudication: bool = False,
) -> AdjudicationRecord:
    """
    Build a complete Week 7 adjudication record for one claim.

    This function connects the verdict taxonomy, evidence summary, and
    interactive payload into one stable output object.
    """
    claim_id = claim.get("claim_id")

    if not isinstance(claim_id, str) or not claim_id.strip():
        raise ValueError("Claim is missing a valid claim_id.")

    speaker_claim_summary = build_speaker_claim_summary(claim)
    decision = decide_claim_verdict(
        evidence_records,
        allow_skewed_adjudication=allow_skewed_adjudication,
    )

    evidence_summary = summarize_evidence_sources_by_stance(evidence_records)
    narrative = build_placeholder_narrative(claim, decision, evidence_summary)
    interactive_payload = build_interactive_payload(evidence_records)

    return AdjudicationRecord(
        claim_id=claim_id,
        speaker_claim_summary=speaker_claim_summary,
        evidence_summary=evidence_summary,
        verdict=decision.verdict.value,
        confidence=decision.confidence.value,
        narrative=narrative,
        interactive_payload=interactive_payload,
        guard_reason=decision.guard_reason,
    )
