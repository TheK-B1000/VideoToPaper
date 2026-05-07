from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class CherryPickingGuardReport:
    total_adjudications: int
    safe_adjudications: int
    guarded_adjudications: int
    insufficient_evidence_count: int
    manual_review_count: int
    publishable_for_week8: bool
    guarded_claim_ids: list[str]
    report_notes: list[str]


def build_cherry_picking_guard_report(
    adjudications: Sequence[Mapping[str, Any]],
    *,
    max_guarded_ratio_for_publish: float = 0.25,
) -> dict[str, Any]:
    """
    Build a stage-level balance and cherry-picking guard report.

    This does not replace per-claim guard_reason fields. It summarizes whether
    the batch as a whole is safe to hand to Week 8 paper assembly.
    """
    if max_guarded_ratio_for_publish < 0 or max_guarded_ratio_for_publish > 1:
        raise ValueError("max_guarded_ratio_for_publish must be between 0 and 1.")

    total = len(adjudications)
    guarded_claim_ids: list[str] = []
    insufficient_evidence_count = 0
    manual_review_count = 0

    for adjudication in adjudications:
        claim_id = adjudication.get("claim_id")
        verdict = adjudication.get("verdict")
        guard_reason = adjudication.get("guard_reason")

        if not isinstance(claim_id, str) or not claim_id.strip():
            raise ValueError(f"Adjudication is missing a valid claim_id: {adjudication!r}")

        if not isinstance(verdict, str) or not verdict.strip():
            raise ValueError(f"Adjudication {claim_id!r} is missing a valid verdict.")

        is_guarded = isinstance(guard_reason, str) and bool(guard_reason.strip())

        if is_guarded:
            guarded_claim_ids.append(claim_id.strip())

        if verdict == "insufficient_evidence":
            insufficient_evidence_count += 1

        if verdict == "requires_manual_review":
            manual_review_count += 1

    guarded_count = len(guarded_claim_ids)
    safe_count = total - guarded_count

    guarded_ratio = guarded_count / total if total else 0.0
    publishable_for_week8 = total > 0 and guarded_ratio <= max_guarded_ratio_for_publish

    notes: list[str] = []

    if total == 0:
        notes.append("No adjudications were produced. Week 8 should not assemble an evidence review.")
    elif guarded_count == 0:
        notes.append("No guarded adjudications detected.")
    else:
        notes.append(
            f"{guarded_count} of {total} adjudications were guarded "
            f"({guarded_ratio:.2%})."
        )

    if insufficient_evidence_count:
        notes.append(
            f"{insufficient_evidence_count} claim(s) had insufficient evidence."
        )

    if manual_review_count:
        notes.append(
            f"{manual_review_count} claim(s) require manual review before publication."
        )

    if not publishable_for_week8:
        notes.append(
            "This batch should not be treated as publishable input for Week 8 without review."
        )

    report = CherryPickingGuardReport(
        total_adjudications=total,
        safe_adjudications=safe_count,
        guarded_adjudications=guarded_count,
        insufficient_evidence_count=insufficient_evidence_count,
        manual_review_count=manual_review_count,
        publishable_for_week8=publishable_for_week8,
        guarded_claim_ids=guarded_claim_ids,
        report_notes=notes,
    )

    return asdict(report)
