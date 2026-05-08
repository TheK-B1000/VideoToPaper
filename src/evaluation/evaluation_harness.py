from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class EvaluationConfig:
    clip_tolerance_seconds: float = 1.0
    minimum_balanced_retrieval_ratio: float = 0.8


@dataclass
class AxisResult:
    score: str
    passed: bool
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationReport:
    steelman_accuracy: AxisResult
    evidence_balance: AxisResult
    citation_integrity: AxisResult
    clip_anchor_accuracy: AxisResult
    publishable: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "steelman_accuracy": self.steelman_accuracy.details,
            "evidence_balance": self.evidence_balance.details,
            "citation_integrity": self.citation_integrity.details,
            "clip_anchor_accuracy": self.clip_anchor_accuracy.details,
            "publishable": self.publishable,
        }


def percent(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "100%"
    return f"{round((numerator / denominator) * 100)}%"


def evaluate_steelman_accuracy(
    speaker_perspective: Dict[str, Any],
    claims_by_id: Dict[str, Dict[str, Any]],
) -> AxisResult:
    blocks = speaker_perspective.get("narrative_blocks", [])
    qualifications_expected = speaker_perspective.get("expected_qualifications", [])
    qualifications_preserved = speaker_perspective.get("qualifications_preserved", [])

    total_assertions = 0
    anchored_assertions = 0
    missing_anchors: List[Dict[str, Any]] = []
    hedge_drift_detected = False

    for block in blocks:
        assertions = block.get("assertions", [])
        anchors = block.get("verbatim_anchors", [])

        for assertion in assertions:
            total_assertions += 1

            valid_anchor_found = any(anchor_id in claims_by_id for anchor_id in anchors)
            if valid_anchor_found:
                anchored_assertions += 1
            else:
                missing_anchors.append(
                    {
                        "text": assertion.get("text", ""),
                        "anchors": anchors,
                    }
                )

            if assertion.get("hedge_drift_detected") is True:
                hedge_drift_detected = True

    preserved_count = sum(
        1 for item in qualifications_expected if item in qualifications_preserved
    )

    passed = (
        anchored_assertions == total_assertions
        and preserved_count == len(qualifications_expected)
        and not hedge_drift_detected
    )

    return AxisResult(
        score=percent(anchored_assertions, total_assertions),
        passed=passed,
        details={
            "verbatim_anchored_assertions": percent(
                anchored_assertions, total_assertions
            ),
            "qualifications_preserved": percent(
                preserved_count, len(qualifications_expected)
            ),
            "hedge_drift_detected": hedge_drift_detected,
            "missing_anchors": missing_anchors,
        },
    )


def evaluate_evidence_balance(
    adjudications: List[Dict[str, Any]],
    config: Optional[EvaluationConfig] = None,
) -> AxisResult:
    config = config or EvaluationConfig()

    total_claims = len(adjudications)
    balanced_count = 0
    false_consensus_count = 0
    skewed_claims: List[str] = []

    for adjudication in adjudications:
        claim_id = adjudication.get("claim_id", "unknown_claim")
        balance_score = adjudication.get("balance_score")
        verdict = adjudication.get("verdict", "")

        if balance_score == "balanced":
            balanced_count += 1
        else:
            skewed_claims.append(claim_id)

        if balance_score != "balanced" and verdict in {
            "well_supported",
            "well_supported_with_qualifications",
            "contradicted",
        }:
            false_consensus_count += 1

    balanced_ratio = balanced_count / total_claims if total_claims else 1.0

    passed = (
        balanced_ratio >= config.minimum_balanced_retrieval_ratio
        and false_consensus_count == 0
    )

    if false_consensus_count > 0:
        cherry_picking_score = "high"
    elif skewed_claims:
        cherry_picking_score = "moderate"
    else:
        cherry_picking_score = "low"

    return AxisResult(
        score=percent(balanced_count, total_claims),
        passed=passed,
        details={
            "claims_with_balanced_retrieval": percent(balanced_count, total_claims),
            "cherry_picking_score": cherry_picking_score,
            "false_consensus_count": false_consensus_count,
            "skewed_claims": skewed_claims,
        },
    )


def evaluate_citation_integrity(
    references: List[Dict[str, Any]],
    evidence_records_by_id: Dict[str, Dict[str, Any]],
) -> AxisResult:
    total_references = len(references)
    resolved_count = 0
    fabricated_references: List[Dict[str, Any]] = []

    for reference in references:
        evidence_id = reference.get("evidence_record_id")
        source_url = reference.get("url")
        identifier = reference.get("identifier")

        record = evidence_records_by_id.get(evidence_id)

        if record and (record.get("url") == source_url or record.get("identifier") == identifier):
            resolved_count += 1
        else:
            fabricated_references.append(reference)

    passed = len(fabricated_references) == 0

    return AxisResult(
        score=percent(resolved_count, total_references),
        passed=passed,
        details={
            "references_resolved": percent(resolved_count, total_references),
            "fabricated_references": len(fabricated_references),
            "unresolved_references": fabricated_references,
        },
    )


def evaluate_clip_anchor_accuracy(
    claims: List[Dict[str, Any]],
    rendered_clips: List[Dict[str, Any]],
    config: Optional[EvaluationConfig] = None,
) -> AxisResult:
    config = config or EvaluationConfig()

    claims_by_id = {claim["claim_id"]: claim for claim in claims}
    total_clips = len(rendered_clips)
    accurate_count = 0
    drift_detected: List[Dict[str, Any]] = []

    for clip in rendered_clips:
        claim_id = clip.get("claim_id")
        claim = claims_by_id.get(claim_id)

        if not claim:
            drift_detected.append(
                {
                    "claim_id": claim_id,
                    "reason": "clip references an unknown claim",
                }
            )
            continue

        expected_clip = claim.get("anchor_clip", {})
        expected_start = float(expected_clip.get("start", 0))
        expected_end = float(expected_clip.get("end", 0))
        actual_start = float(clip.get("start", 0))
        actual_end = float(clip.get("end", 0))

        start_drift = abs(actual_start - expected_start)
        end_drift = abs(actual_end - expected_end)

        if (
            start_drift <= config.clip_tolerance_seconds
            and end_drift <= config.clip_tolerance_seconds
        ):
            accurate_count += 1
        else:
            drift_detected.append(
                {
                    "claim_id": claim_id,
                    "expected_start": expected_start,
                    "actual_start": actual_start,
                    "expected_end": expected_end,
                    "actual_end": actual_end,
                    "start_drift": start_drift,
                    "end_drift": end_drift,
                }
            )

    passed = len(drift_detected) == 0

    return AxisResult(
        score=percent(accurate_count, total_clips),
        passed=passed,
        details={
            "clips_within_tolerance": percent(accurate_count, total_clips),
            "tolerance_seconds": config.clip_tolerance_seconds,
            "drift_detected": drift_detected,
        },
    )


def run_evaluation_harness(
    paper_artifact: Dict[str, Any],
    config: Optional[EvaluationConfig] = None,
) -> EvaluationReport:
    config = config or EvaluationConfig()

    claims = paper_artifact.get("claims", [])
    claims_by_id = {claim["claim_id"]: claim for claim in claims}

    evidence_records = paper_artifact.get("evidence_records", [])
    evidence_records_by_id = {
        record["evidence_record_id"]: record for record in evidence_records
    }

    steelman_result = evaluate_steelman_accuracy(
        speaker_perspective=paper_artifact.get("speaker_perspective", {}),
        claims_by_id=claims_by_id,
    )

    evidence_result = evaluate_evidence_balance(
        adjudications=paper_artifact.get("adjudications", []),
        config=config,
    )

    citation_result = evaluate_citation_integrity(
        references=paper_artifact.get("references", []),
        evidence_records_by_id=evidence_records_by_id,
    )

    clip_result = evaluate_clip_anchor_accuracy(
        claims=claims,
        rendered_clips=paper_artifact.get("rendered_clips", []),
        config=config,
    )

    publishable = all(
        [
            steelman_result.passed,
            evidence_result.passed,
            citation_result.passed,
            clip_result.passed,
        ]
    )

    return EvaluationReport(
        steelman_accuracy=steelman_result,
        evidence_balance=evidence_result,
        citation_integrity=citation_result,
        clip_anchor_accuracy=clip_result,
        publishable=publishable,
    )
    