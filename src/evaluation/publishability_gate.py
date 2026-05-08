from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from src.evaluation.evaluation_harness import EvaluationReport


@dataclass(frozen=True)
class PublishabilityDecision:
    publishable: bool
    reasons: List[str] = field(default_factory=list)
    blocking_axes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "publishable": self.publishable,
            "reasons": self.reasons,
            "blocking_axes": self.blocking_axes,
        }


def decide_publishability(report: EvaluationReport) -> PublishabilityDecision:
    reasons: List[str] = []
    blocking_axes: List[str] = []

    if not report.steelman_accuracy.passed:
        blocking_axes.append("steelman_accuracy")
        details = report.steelman_accuracy.details

        if details.get("hedge_drift_detected") is True:
            reasons.append(
                "The speaker perspective contains hedge drift."
            )

        missing_anchors = details.get("missing_anchors", [])
        if missing_anchors:
            reasons.append(
                f"{len(missing_anchors)} speaker-perspective assertion(s) lack valid verbatim anchors."
            )

        if details.get("qualifications_preserved") != "100%":
            reasons.append(
                "Not all expected qualifications were preserved."
            )

    if not report.evidence_balance.passed:
        blocking_axes.append("evidence_balance")
        details = report.evidence_balance.details

        false_consensus_count = details.get("false_consensus_count", 0)
        if false_consensus_count:
            reasons.append(
                f"{false_consensus_count} claim(s) present a strong verdict despite skewed retrieval."
            )

        skewed_claims = details.get("skewed_claims", [])
        if skewed_claims:
            reasons.append(
                f"{len(skewed_claims)} claim(s) have skewed retrieval."
            )

    if not report.citation_integrity.passed:
        blocking_axes.append("citation_integrity")
        details = report.citation_integrity.details

        fabricated_references = details.get("fabricated_references", 0)
        reasons.append(
            f"{fabricated_references} reference(s) could not be resolved to retrieved evidence."
        )

    if not report.clip_anchor_accuracy.passed:
        blocking_axes.append("clip_anchor_accuracy")
        details = report.clip_anchor_accuracy.details

        drift_detected = details.get("drift_detected", [])
        reasons.append(
            f"{len(drift_detected)} rendered clip(s) drift outside the allowed timestamp tolerance."
        )

    publishable = not blocking_axes

    if publishable:
        reasons.append(
            "All evaluation gates passed."
        )

    return PublishabilityDecision(
        publishable=publishable,
        reasons=reasons,
        blocking_axes=blocking_axes,
    )


def attach_publishability_decision(
    audit_payload: Dict[str, Any],
    decision: PublishabilityDecision,
) -> Dict[str, Any]:
    enriched_payload = dict(audit_payload)
    enriched_payload["publishability_decision"] = decision.to_dict()
    return enriched_payload