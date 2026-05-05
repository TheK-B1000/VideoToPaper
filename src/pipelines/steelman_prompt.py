"""
Week 4: Steelman prompt builder.

This module does not call an LLM.
It only builds the prompt contract for an LLM-assisted Speaker's Perspective pass.

Rule:
The LLM may draft prose, but every narrative block must anchor to existing
claim IDs from claim_inventory.json.
"""

from __future__ import annotations

import json
from typing import Any


def build_steelman_prompt(
    *,
    claim_inventory: list[dict[str, Any]],
    argument_map: dict[str, Any],
    max_claims: int | None = None,
) -> str:
    """
    Build a strict prompt for the Speaker's Perspective section.

    Args:
        claim_inventory:
            Week 3 claim records.

        argument_map:
            Week 2 argument map.

        max_claims:
            Optional claim limit for prompt-size control.

    Returns:
        A prompt string that asks for JSON-only narrative blocks.
    """
    claims = _prepare_claims_for_prompt(claim_inventory, max_claims=max_claims)
    qualifications = _extract_qualifications(argument_map)

    payload = {
        "task": "Draft the Speaker's Perspective section.",
        "section_title": "The Speaker's Perspective",
        "speaker_thesis": argument_map.get("thesis", ""),
        "claims": claims,
        "qualifications_to_preserve": qualifications,
        "output_schema": {
            "narrative_blocks": [
                {
                    "text": "Charitable narrative paragraph grounded in the supplied claims.",
                    "verbatim_anchors": ["claim_id"],
                    "embedded_clip": "claim_id",
                }
            ]
        },
    }

    return (
        "You are drafting the Speaker's Perspective section for an inquiry paper.\n"
        "\n"
        "Your job is to reconstruct the speaker's argument charitably, using only "
        "the supplied claim records and qualifications.\n"
        "\n"
        "Hard rules:\n"
        "1. Return JSON only. Do not include markdown.\n"
        "2. Every narrative block must include at least one verbatim_anchors claim ID.\n"
        "3. embedded_clip must be one of the claim IDs listed in verbatim_anchors.\n"
        "4. Do not introduce facts, motives, criticisms, or conclusions not supported "
        "by the supplied claims.\n"
        "5. Preserve qualifications and hedges. Do not flatten cautious claims into "
        "strong claims.\n"
        "6. Do not make the speaker sound foolish, dishonest, or simplistic.\n"
        "7. If a point cannot be supported by the supplied claims, omit it.\n"
        "\n"
        "Input payload:\n"
        f"{json.dumps(payload, indent=2, ensure_ascii=False)}"
    )


def parse_steelman_prompt_response(response_text: str) -> list[dict[str, Any]]:
    """
    Parse and validate the JSON returned by the prompt.

    Expected shape:
    {
      "narrative_blocks": [
        {
          "text": "...",
          "verbatim_anchors": ["claim_001"],
          "embedded_clip": "claim_001"
        }
      ]
    }
    """
    try:
        data = json.loads(response_text)
    except json.JSONDecodeError as error:
        raise ValueError("Steelman response must be valid JSON") from error

    if not isinstance(data, dict):
        raise ValueError("Steelman response must be a JSON object")

    blocks = data.get("narrative_blocks")
    if not isinstance(blocks, list):
        raise ValueError("Steelman response must contain narrative_blocks list")

    validated_blocks: list[dict[str, Any]] = []

    for index, block in enumerate(blocks):
        if not isinstance(block, dict):
            raise ValueError(f"narrative_blocks[{index}] must be an object")

        text = block.get("text")
        anchors = block.get("verbatim_anchors")
        embedded_clip = block.get("embedded_clip")

        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"narrative_blocks[{index}].text must be non-empty")

        if not isinstance(anchors, list) or not anchors:
            raise ValueError(
                f"narrative_blocks[{index}].verbatim_anchors must be a non-empty list"
            )

        clean_anchors = []
        for anchor in anchors:
            if not isinstance(anchor, str) or not anchor.strip():
                raise ValueError(
                    f"narrative_blocks[{index}].verbatim_anchors contains invalid anchor"
                )
            clean_anchors.append(anchor.strip())

        if not isinstance(embedded_clip, str) or not embedded_clip.strip():
            raise ValueError(
                f"narrative_blocks[{index}].embedded_clip must be non-empty"
            )

        embedded_clip = embedded_clip.strip()

        if embedded_clip not in clean_anchors:
            raise ValueError(
                f"narrative_blocks[{index}].embedded_clip must appear in verbatim_anchors"
            )

        validated_blocks.append(
            {
                "text": text.strip(),
                "verbatim_anchors": clean_anchors,
                "embedded_clip": embedded_clip,
            }
        )

    return validated_blocks


def _prepare_claims_for_prompt(
    claim_inventory: list[dict[str, Any]],
    *,
    max_claims: int | None,
) -> list[dict[str, Any]]:
    if max_claims is not None and max_claims <= 0:
        raise ValueError("max_claims must be positive when provided")

    prepared: list[dict[str, Any]] = []

    for claim in claim_inventory:
        claim_id = claim.get("claim_id")
        quote = claim.get("verbatim_quote")
        claim_type = claim.get("claim_type")
        embed_url = claim.get("embed_url")

        if not isinstance(claim_id, str) or not claim_id.strip():
            continue

        if not isinstance(quote, str) or not quote.strip():
            continue

        prepared.append(
            {
                "claim_id": claim_id.strip(),
                "verbatim_quote": quote.strip(),
                "claim_type": claim_type if isinstance(claim_type, str) else "",
                "embed_url": embed_url if isinstance(embed_url, str) else "",
            }
        )

    if max_claims is not None:
        return prepared[:max_claims]

    return prepared


def _extract_qualifications(argument_map: dict[str, Any]) -> list[str]:
    qualifications: list[str] = []

    top_level = argument_map.get("qualifications", [])
    if isinstance(top_level, list):
        qualifications.extend(_clean_strings(top_level))

    supporting_points = argument_map.get("supporting_points", [])
    if isinstance(supporting_points, list):
        for point in supporting_points:
            if not isinstance(point, dict):
                continue

            point_qualifications = point.get("qualifications", [])
            if isinstance(point_qualifications, list):
                qualifications.extend(_clean_strings(point_qualifications))

    return _dedupe_preserve_order(qualifications)


def _clean_strings(values: list[Any]) -> list[str]:
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