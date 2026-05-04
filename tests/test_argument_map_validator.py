import pytest

from src.argument.argument_map_validator import (
    validate_argument_item,
    validate_argument_map,
)


def make_anchor(anchor_id: str = "anchor_0001") -> dict:
    return {
        "anchor_id": anchor_id,
        "chunk_id": "chunk_0001",
        "type": "verbal_claim",
        "source_text": "The key point is",
        "char_start": 0,
        "char_end": 16,
        "start_seconds": 10.0,
        "end_seconds": 20.0,
    }


def make_argument_item(
    item_id: str = "supporting_point_0001",
    item_type: str = "supporting_point",
    anchor_id: str = "anchor_0001",
    chunk_id: str = "chunk_0001",
    char_start: int = 0,
    char_end: int = 16,
    start_seconds: float = 10.0,
    end_seconds: float = 20.0,
) -> dict:
    return {
        "item_id": item_id,
        "item_type": item_type,
        "anchor_id": anchor_id,
        "chunk_id": chunk_id,
        "source_text": "The key point is",
        "context_text": "The key point is that retrieval can fail silently.",
        "char_start": char_start,
        "char_end": char_end,
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "confidence": "heuristic",
    }


def make_argument_map() -> dict:
    return {
        "map_type": "heuristic_argument_map",
        "thesis_candidates": [],
        "supporting_points": [make_argument_item()],
        "qualifications": [],
        "examples": [],
        "summary_claims": [],
        "anchor_count": 1,
        "chunk_count": 1,
    }


def test_validate_argument_item_accepts_valid_item():
    item = make_argument_item()

    result = validate_argument_item(
        item=item,
        known_anchor_ids={"anchor_0001"},
    )

    assert result["item_id"] == "supporting_point_0001"
    assert result["valid"] is True
    assert result["anchor_reference_valid"] is True
    assert result["offsets_valid"] is True
    assert result["timestamps_valid"] is True
    assert result["errors"] == []


def test_validate_argument_item_rejects_non_dict_item():
    with pytest.raises(TypeError, match="item must be a dictionary"):
        validate_argument_item(
            item="not an item",
            known_anchor_ids={"anchor_0001"},
        )


def test_validate_argument_item_rejects_non_set_known_anchor_ids():
    with pytest.raises(TypeError, match="known_anchor_ids must be a set"):
        validate_argument_item(
            item=make_argument_item(),
            known_anchor_ids=["anchor_0001"],
        )


def test_validate_argument_item_detects_missing_keys():
    item = {
        "item_id": "supporting_point_0001",
        "anchor_id": "anchor_0001",
    }

    result = validate_argument_item(
        item=item,
        known_anchor_ids={"anchor_0001"},
    )

    assert result["valid"] is False
    assert result["item_id"] == "supporting_point_0001"
    assert result["anchor_reference_valid"] is False
    assert result["offsets_valid"] is False
    assert result["timestamps_valid"] is False
    assert any(error.startswith("missing_keys:") for error in result["errors"])


def test_validate_argument_item_detects_invalid_anchor_reference():
    item = make_argument_item(anchor_id="anchor_missing")

    result = validate_argument_item(
        item=item,
        known_anchor_ids={"anchor_0001"},
    )

    assert result["valid"] is False
    assert result["anchor_reference_valid"] is False
    assert "invalid_anchor_reference" in result["errors"]


def test_validate_argument_item_detects_invalid_offsets():
    item = make_argument_item(char_start=50, char_end=10)

    result = validate_argument_item(
        item=item,
        known_anchor_ids={"anchor_0001"},
    )

    assert result["valid"] is False
    assert result["offsets_valid"] is False
    assert "invalid_offsets" in result["errors"]


def test_validate_argument_item_detects_invalid_timestamps():
    item = make_argument_item(start_seconds=20.0, end_seconds=10.0)

    result = validate_argument_item(
        item=item,
        known_anchor_ids={"anchor_0001"},
    )

    assert result["valid"] is False
    assert result["timestamps_valid"] is False
    assert "invalid_timestamps" in result["errors"]


def test_validate_argument_map_accepts_valid_map():
    argument_map = make_argument_map()
    anchors = [make_anchor("anchor_0001")]

    metrics = validate_argument_map(
        argument_map=argument_map,
        anchors=anchors,
    )

    assert metrics["argument_map_valid"] is True
    assert metrics["missing_sections"] == []
    assert metrics["argument_item_count"] == 1
    assert metrics["valid_argument_item_count"] == 1
    assert metrics["invalid_argument_item_count"] == 0
    assert metrics["argument_anchor_reference_pass_rate"] == 1.0
    assert metrics["argument_offset_validation_pass_rate"] == 1.0
    assert metrics["argument_timestamp_validation_pass_rate"] == 1.0
    assert metrics["invalid_argument_items"] == []


def test_validate_argument_map_detects_missing_sections():
    argument_map = {
        "map_type": "heuristic_argument_map",
        "supporting_points": [],
    }

    metrics = validate_argument_map(
        argument_map=argument_map,
        anchors=[],
    )

    assert metrics["argument_map_valid"] is False
    assert "thesis_candidates" in metrics["missing_sections"]
    assert "qualifications" in metrics["missing_sections"]
    assert metrics["argument_item_count"] == 0
    assert metrics["valid_argument_item_count"] == 0
    assert metrics["invalid_argument_item_count"] == 0
    assert metrics["argument_anchor_reference_pass_rate"] == 0.0
    assert metrics["argument_offset_validation_pass_rate"] == 0.0
    assert metrics["argument_timestamp_validation_pass_rate"] == 0.0


def test_validate_argument_map_handles_empty_items():
    argument_map = {
        "map_type": "heuristic_argument_map",
        "thesis_candidates": [],
        "supporting_points": [],
        "qualifications": [],
        "examples": [],
        "summary_claims": [],
        "anchor_count": 0,
        "chunk_count": 1,
    }

    metrics = validate_argument_map(
        argument_map=argument_map,
        anchors=[],
    )

    assert metrics["argument_map_valid"] is True
    assert metrics["argument_item_count"] == 0
    assert metrics["valid_argument_item_count"] == 0
    assert metrics["invalid_argument_item_count"] == 0
    assert metrics["argument_anchor_reference_pass_rate"] == 1.0
    assert metrics["argument_offset_validation_pass_rate"] == 1.0
    assert metrics["argument_timestamp_validation_pass_rate"] == 1.0
    assert metrics["invalid_argument_items"] == []


def test_validate_argument_map_reports_invalid_items():
    argument_map = {
        "map_type": "heuristic_argument_map",
        "thesis_candidates": [],
        "supporting_points": [
            make_argument_item(
                item_id="supporting_point_0001",
                anchor_id="anchor_0001",
            ),
            make_argument_item(
                item_id="supporting_point_0002",
                anchor_id="anchor_missing",
                char_start=25,
                char_end=5,
                start_seconds=30.0,
                end_seconds=10.0,
            ),
        ],
        "qualifications": [],
        "examples": [],
        "summary_claims": [],
        "anchor_count": 2,
        "chunk_count": 1,
    }

    metrics = validate_argument_map(
        argument_map=argument_map,
        anchors=[make_anchor("anchor_0001")],
    )

    assert metrics["argument_map_valid"] is False
    assert metrics["argument_item_count"] == 2
    assert metrics["valid_argument_item_count"] == 1
    assert metrics["invalid_argument_item_count"] == 1
    assert metrics["argument_anchor_reference_pass_rate"] == 0.5
    assert metrics["argument_offset_validation_pass_rate"] == 0.5
    assert metrics["argument_timestamp_validation_pass_rate"] == 0.5

    invalid_item = metrics["invalid_argument_items"][0]

    assert invalid_item["item_id"] == "supporting_point_0002"
    assert "invalid_anchor_reference" in invalid_item["errors"]
    assert "invalid_offsets" in invalid_item["errors"]
    assert "invalid_timestamps" in invalid_item["errors"]


def test_validate_argument_map_collects_items_from_all_sections():
    argument_map = {
        "map_type": "heuristic_argument_map",
        "thesis_candidates": [
            make_argument_item(
                item_id="summary_claim_0001",
                item_type="summary_claim",
                anchor_id="anchor_0001",
            )
        ],
        "supporting_points": [
            make_argument_item(
                item_id="supporting_point_0002",
                item_type="supporting_point",
                anchor_id="anchor_0002",
            )
        ],
        "qualifications": [
            make_argument_item(
                item_id="qualification_0003",
                item_type="qualification",
                anchor_id="anchor_0003",
            )
        ],
        "examples": [
            make_argument_item(
                item_id="example_0004",
                item_type="example",
                anchor_id="anchor_0004",
            )
        ],
        "summary_claims": [
            make_argument_item(
                item_id="summary_claim_0005",
                item_type="summary_claim",
                anchor_id="anchor_0005",
            )
        ],
        "anchor_count": 5,
        "chunk_count": 1,
    }

    anchors = [
        make_anchor("anchor_0001"),
        make_anchor("anchor_0002"),
        make_anchor("anchor_0003"),
        make_anchor("anchor_0004"),
        make_anchor("anchor_0005"),
    ]

    metrics = validate_argument_map(
        argument_map=argument_map,
        anchors=anchors,
    )

    assert metrics["argument_item_count"] == 5
    assert metrics["valid_argument_item_count"] == 5
    assert metrics["invalid_argument_item_count"] == 0
    assert metrics["argument_map_valid"] is True


def test_validate_argument_map_rejects_non_dict_map():
    with pytest.raises(TypeError, match="argument_map must be a dictionary"):
        validate_argument_map(
            argument_map="not a map",
            anchors=[],
        )


def test_validate_argument_map_rejects_non_list_anchors():
    with pytest.raises(TypeError, match="anchors must be a list"):
        validate_argument_map(
            argument_map=make_argument_map(),
            anchors="not anchors",
        )


def test_validate_argument_map_rejects_non_list_section():
    argument_map = make_argument_map()
    argument_map["supporting_points"] = "not a list"

    with pytest.raises(TypeError, match="supporting_points must be a list"):
        validate_argument_map(
            argument_map=argument_map,
            anchors=[make_anchor("anchor_0001")],
        )


def test_validate_argument_map_ignores_bad_anchor_objects_when_collecting_known_ids():
    argument_map = make_argument_map()

    metrics = validate_argument_map(
        argument_map=argument_map,
        anchors=[
            make_anchor("anchor_0001"),
            {"not_anchor_id": "bad"},
            "bad anchor",
        ],
    )

    assert metrics["argument_map_valid"] is True
    assert metrics["valid_argument_item_count"] == 1
    assert metrics["invalid_argument_item_count"] == 0