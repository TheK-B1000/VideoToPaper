from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


def normalize_claims(claims: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Normalize claim records into the evaluator artifact shape.

    Expected minimum output per claim:
    - claim_id
    - verbatim_quote
    - anchor_clip
    """
    normalized: List[Dict[str, Any]] = []

    for claim in claims:
        anchor_clip = claim.get("anchor_clip", {})

        normalized.append(
            {
                "claim_id": claim["claim_id"],
                "verbatim_quote": claim["verbatim_quote"],
                "anchor_clip": {
                    "start": float(anchor_clip["start"]),
                    "end": float(anchor_clip["end"]),
                },
            }
        )

    return normalized


def normalize_speaker_perspective(
    speaker_perspective: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Normalize the speaker perspective section into the evaluator artifact shape.
    """
    return {
        "expected_qualifications": speaker_perspective.get(
            "expected_qualifications",
            [],
        ),
        "qualifications_preserved": speaker_perspective.get(
            "qualifications_preserved",
            [],
        ),
        "narrative_blocks": speaker_perspective.get("narrative_blocks", []),
    }


def normalize_adjudications(
    adjudications: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Normalize adjudication records into the evaluator artifact shape.
    """
    normalized: List[Dict[str, Any]] = []

    for adjudication in adjudications:
        normalized.append(
            {
                "claim_id": adjudication["claim_id"],
                "speaker_claim_summary": adjudication.get(
                    "speaker_claim_summary",
                    "",
                ),
                "balance_score": adjudication["balance_score"],
                "verdict": adjudication["verdict"],
            }
        )

    return normalized


def normalize_evidence_records(
    evidence_records: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Normalize evidence records into the evaluator artifact shape.
    """
    normalized: List[Dict[str, Any]] = []

    for record in evidence_records:
        normalized.append(
            {
                "evidence_record_id": record["evidence_record_id"],
                "claim_id": record.get("claim_id"),
                "tier": record.get("tier"),
                "stance": record.get("stance"),
                "title": record.get("title", ""),
                "identifier": record.get("identifier"),
                "url": record.get("url"),
            }
        )

    return normalized


def build_references_from_evidence_records(
    evidence_records: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Build rendered references from retrieved evidence records.

    The evaluator checks that every rendered reference resolves back to an
    evidence record. This keeps references honest and traceable.
    """
    references: List[Dict[str, Any]] = []

    for record in evidence_records:
        references.append(
            {
                "evidence_record_id": record["evidence_record_id"],
                "identifier": record.get("identifier"),
                "url": record.get("url"),
            }
        )

    return references


def build_rendered_clips_from_claims(
    claims: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Build rendered clip records from claim anchor clips.

    The evaluator compares these rendered clip ranges against the original
    claim anchor clips to detect timestamp drift.
    """
    rendered_clips: List[Dict[str, Any]] = []

    for claim in claims:
        anchor_clip = claim["anchor_clip"]

        rendered_clips.append(
            {
                "claim_id": claim["claim_id"],
                "start": float(anchor_clip["start"]),
                "end": float(anchor_clip["end"]),
            }
        )

    return rendered_clips


def build_paper_artifact(
    *,
    claims: List[Dict[str, Any]],
    speaker_perspective: Dict[str, Any],
    adjudications: List[Dict[str, Any]],
    evidence_records: List[Dict[str, Any]],
    references: Optional[List[Dict[str, Any]]] = None,
    rendered_clips: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Build the evaluator-ready paper artifact.

    This is the contract between paper assembly and evaluation.
    """
    normalized_claims = normalize_claims(claims)
    normalized_evidence_records = normalize_evidence_records(evidence_records)

    return {
        "claims": normalized_claims,
        "speaker_perspective": normalize_speaker_perspective(speaker_perspective),
        "adjudications": normalize_adjudications(adjudications),
        "evidence_records": normalized_evidence_records,
        "references": (
            references
            if references is not None
            else build_references_from_evidence_records(normalized_evidence_records)
        ),
        "rendered_clips": (
            rendered_clips
            if rendered_clips is not None
            else build_rendered_clips_from_claims(normalized_claims)
        ),
    }


def write_paper_artifact(
    paper_artifact: Dict[str, Any],
    output_path: Union[str, Path],
) -> Path:
    """
    Write an evaluator-ready paper artifact to JSON.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(
        json.dumps(paper_artifact, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return path


def load_paper_artifact(input_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Load a previously exported paper artifact.
    """
    path = Path(input_path)

    if not path.exists():
        raise FileNotFoundError(f"Paper artifact not found: {path}")

    return json.loads(path.read_text(encoding="utf-8"))