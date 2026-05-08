"""
Week 4: Steelmanning the Speaker

Builds the Speaker's Perspective section from verbatim-anchored claims.

Design rule:
- Every narrative block must point back to one or more claim IDs.
- Unsupported blocks are stripped, not repaired.
- Qualifications from the argument map must survive into the final section.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


SECTION_TITLE = "The Speaker's Perspective"
SELF_RECOGNITION_PASSED = "passed"
SELF_RECOGNITION_FAILED = "failed"


@dataclass(frozen=True)
class NarrativeBlock:
    text: str
    verbatim_anchors: list[str]
    embedded_clip: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SteelmanSection:
    section_title: str
    narrative_blocks: list[NarrativeBlock]
    qualifications_preserved: list[str]
    self_recognition_check: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "section_title": self.section_title,
            "narrative_blocks": [block.to_dict() for block in self.narrative_blocks],
            "qualifications_preserved": self.qualifications_preserved,
            "self_recognition_check": self.self_recognition_check,
        }


def build_steelman_section(
    claim_inventory: list[dict[str, Any]],
    argument_map: dict[str, Any],
    drafted_blocks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Build the Speaker's Perspective section.

    If drafted_blocks are provided, this function validates and keeps only blocks
    whose anchors resolve to real verbatim claims.

    If drafted_blocks are not provided, this function creates a conservative
    starter perspective directly from the claim inventory.

    Args:
        claim_inventory:
            Week 3 claim records. Each claim should include:
            - claim_id
            - verbatim_quote
            - embed_url

        argument_map:
            Week 2 argument structure. Used here mainly for qualifications.

        drafted_blocks:
            Optional proposed narrative blocks, usually from an LLM later.
            Unsupported blocks are dropped.

    Returns:
        A serializable Speaker's Perspective section dict.
    """
    claim_lookup = _build_claim_lookup(claim_inventory)
    qualifications = extract_qualifications(argument_map)

    if drafted_blocks is None:
        blocks = _build_conservative_blocks_from_claims(claim_inventory)
    else:
        blocks = validate_narrative_blocks(drafted_blocks, claim_lookup)

    blocks = preserve_qualifications_in_blocks(
        blocks=blocks,
        qualifications=qualifications,
        claim_lookup=claim_lookup,
    )

    recognition_status = (
        SELF_RECOGNITION_PASSED
        if blocks and all(block.verbatim_anchors for block in blocks)
        else SELF_RECOGNITION_FAILED
    )

    section = SteelmanSection(
        section_title=SECTION_TITLE,
        narrative_blocks=blocks,
        qualifications_preserved=qualifications,
        self_recognition_check=recognition_status,
    )

    return section.to_dict()


def validate_narrative_blocks(
    drafted_blocks: list[dict[str, Any]],
    claim_lookup: dict[str, dict[str, Any]],
) -> list[NarrativeBlock]:
    """
    Keep only narrative blocks that are grounded in real claim IDs.

    This is the Week 4 refusal-by-design behavior:
    unsupported assertions are stripped, not repaired.
    """
    valid_blocks: list[NarrativeBlock] = []

    for block in drafted_blocks:
        text = str(block.get("text", "")).strip()
        anchors = block.get("verbatim_anchors", [])

        if not text:
            continue

        if not isinstance(anchors, list) or not anchors:
            continue

        valid_anchors = [
            anchor for anchor in anchors
            if isinstance(anchor, str) and anchor in claim_lookup
        ]

        if not valid_anchors:
            continue

        embedded_clip = block.get("embedded_clip")

        if embedded_clip not in valid_anchors:
            embedded_clip = valid_anchors[0]

        valid_blocks.append(
            NarrativeBlock(
                text=text,
                verbatim_anchors=valid_anchors,
                embedded_clip=embedded_clip,
            )
        )

    return valid_blocks


def extract_qualifications(argument_map: dict[str, Any]) -> list[str]:
    """
    Extract qualifications/concessions/hedges from a Week 2 argument map.

    Supports both:
    - top-level "qualifications"
    - nested supporting_points[*]["qualifications"]
    """
    qualifications: list[str] = []

    top_level = argument_map.get("qualifications", [])
    if isinstance(top_level, list):
        qualifications.extend(_clean_string_list(top_level))

    supporting_points = argument_map.get("supporting_points", [])
    if isinstance(supporting_points, list):
        for point in supporting_points:
            if not isinstance(point, dict):
                continue

            point_qualifications = point.get("qualifications", [])
            if isinstance(point_qualifications, list):
                qualifications.extend(_clean_string_list(point_qualifications))

    return _dedupe_preserve_order(qualifications)


def preserve_qualifications_in_blocks(
    blocks: list[NarrativeBlock],
    qualifications: list[str],
    claim_lookup: dict[str, dict[str, Any]],
) -> list[NarrativeBlock]:
    """
    Ensure extracted qualifications appear in the Speaker's Perspective.

    If a qualification is already present in any block, do nothing.
    Otherwise, attach a conservative qualification block to the first available
    claim anchor.

    This keeps Week 4 honest: hedges do not vanish into the fog machine.
    """
    if not blocks or not qualifications:
        return blocks

    existing_text = " ".join(block.text.lower() for block in blocks)
    updated_blocks = list(blocks)

    fallback_anchor = blocks[0].verbatim_anchors[0]

    for qualification in qualifications:
        if qualification.lower() in existing_text:
            continue

        if fallback_anchor not in claim_lookup:
            continue

        updated_blocks.append(
            NarrativeBlock(
                text=f"The speaker also qualifies the argument: {qualification}",
                verbatim_anchors=[fallback_anchor],
                embedded_clip=fallback_anchor,
            )
        )

    return updated_blocks


def _build_conservative_blocks_from_claims(
    claim_inventory: list[dict[str, Any]],
) -> list[NarrativeBlock]:
    """
    Create a safe starter Speaker's Perspective without an LLM.

    This is intentionally plain. Week 4 starts with correctness before style.
    """
    blocks: list[NarrativeBlock] = []

    for claim in claim_inventory:
        claim_id = claim.get("claim_id")
        quote = claim.get("verbatim_quote")

        if not isinstance(claim_id, str) or not claim_id.strip():
            continue

        if not isinstance(quote, str) or not quote.strip():
            continue

        blocks.append(
            NarrativeBlock(
                text=f"The speaker emphasizes the following point: “{quote.strip()}”",
                verbatim_anchors=[claim_id],
                embedded_clip=claim_id,
            )
        )

    return blocks


def _build_claim_lookup(
    claim_inventory: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    claim_lookup: dict[str, dict[str, Any]] = {}

    for claim in claim_inventory:
        claim_id = claim.get("claim_id")

        if not isinstance(claim_id, str) or not claim_id.strip():
            continue

        claim_lookup[claim_id] = claim

    return claim_lookup


def _clean_string_list(values: list[Any]) -> list[str]:
    return [
        value.strip()
        for value in values
        if isinstance(value, str) and value.strip()
    ]


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []

    for value in values:
        key = value.lower()

        if key in seen:
            continue

        seen.add(key)
        deduped.append(value)

    return deduped