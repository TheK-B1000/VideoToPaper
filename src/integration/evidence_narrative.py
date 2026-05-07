from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol, Sequence


class NarrativeClient(Protocol):
    """
    Minimal protocol for an LLM client.

    This lets Week 7 depend on an interface instead of depending directly on
    a vendor SDK or a specific safe_llm_call implementation.
    """

    def generate(self, prompt: str, *, max_output_tokens: int) -> str:
        ...


@dataclass(frozen=True)
class NarrativeGenerationResult:
    narrative: str
    used_llm: bool
    fallback_reason: str | None = None


def build_evidence_narrative_prompt(
    *,
    claim: Mapping[str, Any],
    adjudication: Mapping[str, Any],
    evidence_records: Sequence[Mapping[str, Any]],
) -> str:
    claim_id = claim.get("claim_id")
    verbatim_quote = claim.get("verbatim_quote")
    verdict = adjudication.get("verdict")
    confidence = adjudication.get("confidence")

    if not isinstance(claim_id, str) or not claim_id.strip():
        raise ValueError("Claim is missing a valid claim_id.")

    if not isinstance(verbatim_quote, str) or not verbatim_quote.strip():
        raise ValueError(f"Claim {claim_id!r} is missing a valid verbatim_quote.")

    if not isinstance(verdict, str) or not verdict.strip():
        raise ValueError(f"Adjudication for {claim_id!r} is missing a valid verdict.")

    if not isinstance(confidence, str) or not confidence.strip():
        raise ValueError(f"Adjudication for {claim_id!r} is missing a valid confidence.")

    evidence_lines = []

    for index, record in enumerate(evidence_records, start=1):
        stance = record.get("stance")
        label = record.get("citation_label") or record.get("title") or record.get("source")
        key_finding = record.get("key_finding")

        if not isinstance(stance, str) or not stance.strip():
            raise ValueError(f"Evidence record {index} is missing a valid stance.")

        if not isinstance(label, str) or not label.strip():
            raise ValueError(f"Evidence record {index} is missing a usable citation label.")

        if not isinstance(key_finding, str) or not key_finding.strip():
            key_finding = "No key finding was provided."

        evidence_lines.append(
            f"{index}. [{stance.strip()}] {label.strip()}: {key_finding.strip()}"
        )

    evidence_block = "\n".join(evidence_lines) if evidence_lines else "No usable evidence records."

    return f"""
You are writing the Evidence Review section for one claim in The Inquiry Engine.

Write 2 concise paragraphs.

Rules:
- Use an inquiry tone, not a courtroom verdict tone.
- Be charitable to the speaker.
- Do not invent sources, claims, or findings.
- Use only the evidence records provided below.
- Mention uncertainty when the evidence is incomplete, mixed, or qualified.
- Do not say the speaker is lying, dishonest, foolish, or debunked.
- Do not add citations that are not listed in the evidence records.
- Preserve the difference between supports, qualifies, complicates, and contradicts.

Claim ID:
{claim_id}

Speaker's verbatim claim:
"{verbatim_quote.strip()}"

Assigned verdict:
{verdict.strip()}

Confidence:
{confidence.strip()}

Retrieved evidence:
{evidence_block}
""".strip()


def build_deterministic_fallback_narrative(
    *,
    adjudication: Mapping[str, Any],
) -> str:
    verdict = adjudication.get("verdict")
    confidence = adjudication.get("confidence")
    evidence_summary = adjudication.get("evidence_summary")

    if not isinstance(verdict, str) or not verdict.strip():
        raise ValueError("Adjudication is missing a valid verdict.")

    if not isinstance(confidence, str) or not confidence.strip():
        raise ValueError("Adjudication is missing a valid confidence.")

    if not isinstance(evidence_summary, Mapping):
        raise ValueError("Adjudication is missing a valid evidence_summary.")

    supports = evidence_summary.get("supports", [])
    qualifies = evidence_summary.get("qualifies", [])
    complicates = evidence_summary.get("complicates", [])
    contradicts = evidence_summary.get("contradicts", [])

    parts = [
        f"This claim received the verdict '{verdict}' with {confidence} confidence."
    ]

    if supports:
        parts.append(f"Supporting sources include: {', '.join(supports)}.")

    if qualifies:
        parts.append(f"Qualifying sources include: {', '.join(qualifies)}.")

    if complicates:
        parts.append(f"Complicating sources include: {', '.join(complicates)}.")

    if contradicts:
        parts.append(f"Contrary sources include: {', '.join(contradicts)}.")

    if len(parts) == 1:
        parts.append(
            "No source-level synthesis was generated because the adjudication did not include usable evidence buckets."
        )

    return " ".join(parts)


def generate_evidence_narrative(
    *,
    claim: Mapping[str, Any],
    adjudication: Mapping[str, Any],
    evidence_records: Sequence[Mapping[str, Any]],
    narrative_client: NarrativeClient | None = None,
    use_llm: bool = False,
    max_output_tokens: int = 700,
) -> NarrativeGenerationResult:
    """
    Generate the per-claim evidence review narrative.

    LLM usage is opt-in. By default this returns a deterministic fallback so
    Week 7 stays testable and free during development.
    """
    if not use_llm:
        return NarrativeGenerationResult(
            narrative=build_deterministic_fallback_narrative(adjudication=adjudication),
            used_llm=False,
            fallback_reason="LLM narrative generation disabled.",
        )

    if narrative_client is None:
        return NarrativeGenerationResult(
            narrative=build_deterministic_fallback_narrative(adjudication=adjudication),
            used_llm=False,
            fallback_reason="No narrative client was provided.",
        )

    prompt = build_evidence_narrative_prompt(
        claim=claim,
        adjudication=adjudication,
        evidence_records=evidence_records,
    )

    try:
        narrative = narrative_client.generate(
            prompt,
            max_output_tokens=max_output_tokens,
        )
    except Exception as exc:
        return NarrativeGenerationResult(
            narrative=build_deterministic_fallback_narrative(adjudication=adjudication),
            used_llm=False,
            fallback_reason=f"Narrative client failed: {exc}",
        )

    if not narrative.strip():
        return NarrativeGenerationResult(
            narrative=build_deterministic_fallback_narrative(adjudication=adjudication),
            used_llm=False,
            fallback_reason="Narrative client returned empty text.",
        )

    return NarrativeGenerationResult(
        narrative=narrative.strip(),
        used_llm=True,
        fallback_reason=None,
    )
