import pytest

from src.pipelines.steelman_pipeline import (
    SECTION_TITLE,
    SELF_RECOGNITION_FAILED,
    SELF_RECOGNITION_PASSED,
    build_steelman_section,
    extract_qualifications,
    validate_narrative_blocks,
)


@pytest.fixture
def sample_claim_inventory():
    return [
        {
            "claim_id": "claim_001",
            "verbatim_quote": "single-agent algorithms assume a stationary environment",
            "anchor_chunk": "chunk_001",
            "char_offset_start": 10,
            "char_offset_end": 64,
            "anchor_clip": {"start": 12.0, "end": 18.0},
            "claim_type": "empirical_technical",
            "verification_strategy": "literature_review",
            "embed_url": "https://www.youtube-nocookie.com/embed/ABC123?start=12&end=18",
        },
        {
            "claim_id": "claim_002",
            "verbatim_quote": "multi-agent systems change as each agent learns",
            "anchor_chunk": "chunk_002",
            "char_offset_start": 90,
            "char_offset_end": 136,
            "anchor_clip": {"start": 40.0, "end": 50.0},
            "claim_type": "empirical_technical",
            "verification_strategy": "literature_review",
            "embed_url": "https://www.youtube-nocookie.com/embed/ABC123?start=40&end=50",
        },
    ]


@pytest.fixture
def sample_argument_map():
    return {
        "thesis": "Multi-agent learning introduces non-stationarity.",
        "supporting_points": [
            {
                "claim": "Single-agent assumptions break down in multi-agent settings.",
                "qualifications": [
                    "with the exception of some meta-learning approaches",
                    "practical workarounds may still exist",
                ],
                "anchor_moments": [
                    {"type": "verbal_claim", "start": 12.0, "end": 18.0}
                ],
            }
        ],
    }


def test_build_steelman_section_from_claims_creates_anchored_blocks(
    sample_claim_inventory,
    sample_argument_map,
):
    section = build_steelman_section(
        claim_inventory=sample_claim_inventory,
        argument_map=sample_argument_map,
    )

    assert section["section_title"] == SECTION_TITLE
    assert section["self_recognition_check"] == SELF_RECOGNITION_PASSED
    assert len(section["narrative_blocks"]) >= 2

    for block in section["narrative_blocks"]:
        assert block["verbatim_anchors"]
        assert block["embedded_clip"] in block["verbatim_anchors"]


def test_validate_narrative_blocks_strips_unsupported_blocks(sample_claim_inventory):
    claim_lookup = {
        claim["claim_id"]: claim
        for claim in sample_claim_inventory
    }

    drafted_blocks = [
        {
            "text": "The speaker argues that non-stationarity matters.",
            "verbatim_anchors": ["claim_001"],
            "embedded_clip": "claim_001",
        },
        {
            "text": "The speaker secretly hates all single-agent research.",
            "verbatim_anchors": ["fake_claim_999"],
            "embedded_clip": "fake_claim_999",
        },
        {
            "text": "This block has no anchors and should disappear.",
            "verbatim_anchors": [],
        },
    ]

    valid_blocks = validate_narrative_blocks(
        drafted_blocks=drafted_blocks,
        claim_lookup=claim_lookup,
    )

    assert len(valid_blocks) == 1
    assert valid_blocks[0].text == "The speaker argues that non-stationarity matters."
    assert valid_blocks[0].verbatim_anchors == ["claim_001"]


def test_qualifications_are_extracted_from_argument_map(sample_argument_map):
    qualifications = extract_qualifications(sample_argument_map)

    assert "with the exception of some meta-learning approaches" in qualifications
    assert "practical workarounds may still exist" in qualifications


def test_qualifications_are_preserved_in_final_section(
    sample_claim_inventory,
    sample_argument_map,
):
    section = build_steelman_section(
        claim_inventory=sample_claim_inventory,
        argument_map=sample_argument_map,
    )

    all_block_text = " ".join(
        block["text"]
        for block in section["narrative_blocks"]
    )

    assert "with the exception of some meta-learning approaches" in all_block_text
    assert "practical workarounds may still exist" in all_block_text

    assert section["qualifications_preserved"] == [
        "with the exception of some meta-learning approaches",
        "practical workarounds may still exist",
    ]


def test_drafted_blocks_keep_only_real_claim_anchors(
    sample_claim_inventory,
    sample_argument_map,
):
    drafted_blocks = [
        {
            "text": "The speaker frames the problem around stationarity assumptions.",
            "verbatim_anchors": ["claim_001", "missing_claim"],
            "embedded_clip": "missing_claim",
        }
    ]

    section = build_steelman_section(
        claim_inventory=sample_claim_inventory,
        argument_map=sample_argument_map,
        drafted_blocks=drafted_blocks,
    )

    first_block = section["narrative_blocks"][0]

    assert first_block["verbatim_anchors"] == ["claim_001"]
    assert first_block["embedded_clip"] == "claim_001"


def test_empty_claim_inventory_fails_self_recognition_check(sample_argument_map):
    section = build_steelman_section(
        claim_inventory=[],
        argument_map=sample_argument_map,
    )

    assert section["section_title"] == SECTION_TITLE
    assert section["narrative_blocks"] == []
    assert section["self_recognition_check"] == SELF_RECOGNITION_FAILED