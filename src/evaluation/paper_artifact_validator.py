from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


REQUIRED_TOP_LEVEL_FIELDS = [
    "claims",
    "speaker_perspective",
    "adjudications",
    "evidence_records",
    "references",
    "rendered_clips",
]


@dataclass(frozen=True)
class ArtifactValidationResult:
    valid: bool
    errors: List[str] = field(default_factory=list)

    def raise_if_invalid(self) -> None:
        if not self.valid:
            joined = "\n".join(f"- {error}" for error in self.errors)
            raise ValueError(f"Paper artifact validation failed:\n{joined}")


def validate_paper_artifact(paper_artifact: Dict[str, Any]) -> ArtifactValidationResult:
    errors: List[str] = []

    _validate_top_level_fields(paper_artifact, errors)
    _validate_claims(paper_artifact.get("claims", []), errors)
    _validate_speaker_perspective(
        paper_artifact.get("speaker_perspective", {}),
        paper_artifact.get("claims", []),
        errors,
    )
    _validate_adjudications(
        paper_artifact.get("adjudications", []),
        paper_artifact.get("claims", []),
        errors,
    )
    _validate_evidence_records(paper_artifact.get("evidence_records", []), errors)
    _validate_references(
        paper_artifact.get("references", []),
        paper_artifact.get("evidence_records", []),
        errors,
    )
    _validate_rendered_clips(
        paper_artifact.get("rendered_clips", []),
        paper_artifact.get("claims", []),
        errors,
    )

    return ArtifactValidationResult(
        valid=not errors,
        errors=errors,
    )


def _validate_top_level_fields(
    paper_artifact: Dict[str, Any],
    errors: List[str],
) -> None:
    for field_name in REQUIRED_TOP_LEVEL_FIELDS:
        if field_name not in paper_artifact:
            errors.append(f"Missing required top-level field: {field_name}")


def _validate_claims(
    claims: Any,
    errors: List[str],
) -> None:
    if not isinstance(claims, list):
        errors.append("claims must be a list.")
        return

    seen_claim_ids = set()

    for index, claim in enumerate(claims):
        if not isinstance(claim, dict):
            errors.append(f"claims[{index}] must be an object.")
            continue

        claim_id = claim.get("claim_id")
        if not claim_id:
            errors.append(f"claims[{index}] is missing claim_id.")
        elif claim_id in seen_claim_ids:
            errors.append(f"Duplicate claim_id found: {claim_id}")
        else:
            seen_claim_ids.add(claim_id)

        if not claim.get("verbatim_quote"):
            errors.append(f"claims[{index}] is missing verbatim_quote.")

        anchor_clip = claim.get("anchor_clip")
        if not isinstance(anchor_clip, dict):
            errors.append(f"claims[{index}] is missing anchor_clip.")
            continue

        _validate_clip_range(
            start=anchor_clip.get("start"),
            end=anchor_clip.get("end"),
            label=f"claims[{index}].anchor_clip",
            errors=errors,
        )


def _validate_speaker_perspective(
    speaker_perspective: Any,
    claims: List[Dict[str, Any]],
    errors: List[str],
) -> None:
    if not isinstance(speaker_perspective, dict):
        errors.append("speaker_perspective must be an object.")
        return

    known_claim_ids = {claim.get("claim_id") for claim in claims if isinstance(claim, dict)}
    blocks = speaker_perspective.get("narrative_blocks", [])

    if not isinstance(blocks, list):
        errors.append("speaker_perspective.narrative_blocks must be a list.")
        return

    for block_index, block in enumerate(blocks):
        if not isinstance(block, dict):
            errors.append(f"speaker_perspective.narrative_blocks[{block_index}] must be an object.")
            continue

        assertions = block.get("assertions", [])
        anchors = block.get("verbatim_anchors", [])

        if not isinstance(assertions, list):
            errors.append(
                f"speaker_perspective.narrative_blocks[{block_index}].assertions must be a list."
            )

        if not isinstance(anchors, list):
            errors.append(
                f"speaker_perspective.narrative_blocks[{block_index}].verbatim_anchors must be a list."
            )
            continue

        for anchor_id in anchors:
            if anchor_id not in known_claim_ids:
                errors.append(
                    f"speaker_perspective.narrative_blocks[{block_index}] references unknown claim_id: {anchor_id}"
                )


def _validate_adjudications(
    adjudications: Any,
    claims: List[Dict[str, Any]],
    errors: List[str],
) -> None:
    if not isinstance(adjudications, list):
        errors.append("adjudications must be a list.")
        return

    known_claim_ids = {claim.get("claim_id") for claim in claims if isinstance(claim, dict)}

    for index, adjudication in enumerate(adjudications):
        if not isinstance(adjudication, dict):
            errors.append(f"adjudications[{index}] must be an object.")
            continue

        claim_id = adjudication.get("claim_id")
        if claim_id not in known_claim_ids:
            errors.append(f"adjudications[{index}] references unknown claim_id: {claim_id}")

        if not adjudication.get("balance_score"):
            errors.append(f"adjudications[{index}] is missing balance_score.")

        if not adjudication.get("verdict"):
            errors.append(f"adjudications[{index}] is missing verdict.")


def _validate_evidence_records(
    evidence_records: Any,
    errors: List[str],
) -> None:
    if not isinstance(evidence_records, list):
        errors.append("evidence_records must be a list.")
        return

    seen_evidence_ids = set()

    for index, record in enumerate(evidence_records):
        if not isinstance(record, dict):
            errors.append(f"evidence_records[{index}] must be an object.")
            continue

        evidence_id = record.get("evidence_record_id")
        if not evidence_id:
            errors.append(f"evidence_records[{index}] is missing evidence_record_id.")
        elif evidence_id in seen_evidence_ids:
            errors.append(f"Duplicate evidence_record_id found: {evidence_id}")
        else:
            seen_evidence_ids.add(evidence_id)

        if not record.get("identifier") and not record.get("url"):
            errors.append(
                f"evidence_records[{index}] must include identifier or url."
            )


def _validate_references(
    references: Any,
    evidence_records: List[Dict[str, Any]],
    errors: List[str],
) -> None:
    if not isinstance(references, list):
        errors.append("references must be a list.")
        return

    known_evidence_ids = {
        record.get("evidence_record_id")
        for record in evidence_records
        if isinstance(record, dict)
    }

    for index, reference in enumerate(references):
        if not isinstance(reference, dict):
            errors.append(f"references[{index}] must be an object.")
            continue

        evidence_id = reference.get("evidence_record_id")
        if evidence_id not in known_evidence_ids:
            errors.append(
                f"references[{index}] references unknown evidence_record_id: {evidence_id}"
            )

        if not reference.get("identifier") and not reference.get("url"):
            errors.append(f"references[{index}] must include identifier or url.")


def _validate_rendered_clips(
    rendered_clips: Any,
    claims: List[Dict[str, Any]],
    errors: List[str],
) -> None:
    if not isinstance(rendered_clips, list):
        errors.append("rendered_clips must be a list.")
        return

    known_claim_ids = {claim.get("claim_id") for claim in claims if isinstance(claim, dict)}

    for index, clip in enumerate(rendered_clips):
        if not isinstance(clip, dict):
            errors.append(f"rendered_clips[{index}] must be an object.")
            continue

        claim_id = clip.get("claim_id")
        if claim_id not in known_claim_ids:
            errors.append(f"rendered_clips[{index}] references unknown claim_id: {claim_id}")

        _validate_clip_range(
            start=clip.get("start"),
            end=clip.get("end"),
            label=f"rendered_clips[{index}]",
            errors=errors,
        )


def _validate_clip_range(
    *,
    start: Any,
    end: Any,
    label: str,
    errors: List[str],
) -> None:
    if start is None or end is None:
        errors.append(f"{label} must include start and end.")
        return

    try:
        start_value = float(start)
        end_value = float(end)
    except (TypeError, ValueError):
        errors.append(f"{label} start and end must be numeric.")
        return

    if start_value < 0:
        errors.append(f"{label}.start must be non-negative.")

    if end_value <= start_value:
        errors.append(f"{label}.end must be greater than start.")