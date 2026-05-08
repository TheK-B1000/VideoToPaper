import json

import pytest

from src.pipelines.steelman_prompt import (
    build_steelman_prompt,
    parse_steelman_prompt_response,
)


def test_build_steelman_prompt_includes_claims_and_qualifications():
    claim_inventory = [
        {
            "claim_id": "claim_001",
            "verbatim_quote": "single-agent algorithms assume stationarity",
            "claim_type": "empirical_technical",
            "embed_url": "https://www.youtube-nocookie.com/embed/ABC123?start=1&end=2",
        }
    ]

    argument_map = {
        "thesis": "Multi-agent systems create non-stationarity.",
        "supporting_points": [
            {
                "claim": "Stationarity assumptions can break.",
                "qualifications": [
                    "some methods reduce this instability",
                ],
            }
        ],
    }

    prompt = build_steelman_prompt(
        claim_inventory=claim_inventory,
        argument_map=argument_map,
    )

    assert "Return JSON only" in prompt
    assert "claim_001" in prompt
    assert "single-agent algorithms assume stationarity" in prompt
    assert "some methods reduce this instability" in prompt
    assert "Do not introduce facts" in prompt
    assert "embedded_clip must be one of the claim IDs" in prompt


def test_build_steelman_prompt_limits_claim_count():
    claim_inventory = [
        {
            "claim_id": "claim_001",
            "verbatim_quote": "first claim",
        },
        {
            "claim_id": "claim_002",
            "verbatim_quote": "second claim",
        },
    ]

    prompt = build_steelman_prompt(
        claim_inventory=claim_inventory,
        argument_map={},
        max_claims=1,
    )

    assert "claim_001" in prompt
    assert "first claim" in prompt
    assert "claim_002" not in prompt
    assert "second claim" not in prompt


def test_build_steelman_prompt_rejects_non_positive_max_claims():
    with pytest.raises(ValueError, match="max_claims must be positive"):
        build_steelman_prompt(
            claim_inventory=[],
            argument_map={},
            max_claims=0,
        )


def test_parse_steelman_prompt_response_accepts_valid_json():
    response = json.dumps(
        {
            "narrative_blocks": [
                {
                    "text": "The speaker argues that stationarity assumptions matter.",
                    "verbatim_anchors": ["claim_001"],
                    "embedded_clip": "claim_001",
                }
            ]
        }
    )

    blocks = parse_steelman_prompt_response(response)

    assert blocks == [
        {
            "text": "The speaker argues that stationarity assumptions matter.",
            "verbatim_anchors": ["claim_001"],
            "embedded_clip": "claim_001",
        }
    ]


def test_parse_steelman_prompt_response_rejects_invalid_json():
    with pytest.raises(ValueError, match="valid JSON"):
        parse_steelman_prompt_response("not json")


def test_parse_steelman_prompt_response_rejects_missing_blocks():
    response = json.dumps({"wrong_key": []})

    with pytest.raises(ValueError, match="narrative_blocks list"):
        parse_steelman_prompt_response(response)


def test_parse_steelman_prompt_response_rejects_empty_text():
    response = json.dumps(
        {
            "narrative_blocks": [
                {
                    "text": "   ",
                    "verbatim_anchors": ["claim_001"],
                    "embedded_clip": "claim_001",
                }
            ]
        }
    )

    with pytest.raises(ValueError, match="text must be non-empty"):
        parse_steelman_prompt_response(response)


def test_parse_steelman_prompt_response_rejects_missing_anchors():
    response = json.dumps(
        {
            "narrative_blocks": [
                {
                    "text": "The speaker argues something.",
                    "verbatim_anchors": [],
                    "embedded_clip": "claim_001",
                }
            ]
        }
    )

    with pytest.raises(ValueError, match="verbatim_anchors must be a non-empty list"):
        parse_steelman_prompt_response(response)


def test_parse_steelman_prompt_response_rejects_embedded_clip_not_in_anchors():
    response = json.dumps(
        {
            "narrative_blocks": [
                {
                    "text": "The speaker argues something.",
                    "verbatim_anchors": ["claim_001"],
                    "embedded_clip": "claim_999",
                }
            ]
        }
    )

    with pytest.raises(ValueError, match="embedded_clip must appear in verbatim_anchors"):
        parse_steelman_prompt_response(response)