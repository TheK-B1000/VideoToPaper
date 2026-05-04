import pytest

from src.argument.anchor_validator import validate_anchor, validate_anchors
from src.argument.argument_models import TranscriptChunk


def make_chunk(
    chunk_id: str = "chunk_0001",
    source_text: str = "The key point is that anchors need validation.",
    char_start: int = 0,
    start_seconds: float = 10.0,
    end_seconds: float = 20.0,
) -> TranscriptChunk:
    return TranscriptChunk(
        chunk_id=chunk_id,
        source_text=source_text,
        clean_text=source_text.strip(),
        char_start=char_start,
        char_end=char_start + len(source_text),
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        segment_ids=["seg_0001"],
        chunk_type="transcript_window",
    )


def make_anchor(
    anchor_id: str = "anchor_0001",
    chunk_id: str = "chunk_0001",
    anchor_type: str = "verbal_claim",
    source_text: str = "The key point is",
    char_start: int = 0,
    char_end: int = 16,
    start_seconds: float = 10.0,
    end_seconds: float = 20.0,
) -> dict:
    return {
        "anchor_id": anchor_id,
        "chunk_id": chunk_id,
        "type": anchor_type,
        "source_text": source_text,
        "char_start": char_start,
        "char_end": char_end,
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "confidence": "heuristic",
        "signal": "the key point is",
    }


def test_validate_anchor_accepts_valid_anchor():
    anchor = make_anchor()
    known_chunk_ids = {"chunk_0001"}
    allowed_types = {"verbal_claim", "definition", "example"}

    result = validate_anchor(
        anchor=anchor,
        known_chunk_ids=known_chunk_ids,
        allowed_types=allowed_types,
    )

    assert result["anchor_id"] == "anchor_0001"
    assert result["valid"] is True
    assert result["type_valid"] is True
    assert result["offsets_valid"] is True
    assert result["timestamps_valid"] is True
    assert result["chunk_reference_valid"] is True
    assert result["source_text_valid"] is True
    assert result["errors"] == []


def test_validate_anchor_rejects_non_dict_anchor():
    with pytest.raises(TypeError, match="anchor must be a dictionary"):
        validate_anchor(
            anchor="not an anchor",
            known_chunk_ids={"chunk_0001"},
            allowed_types={"verbal_claim"},
        )


def test_validate_anchor_rejects_non_set_known_chunk_ids():
    with pytest.raises(TypeError, match="known_chunk_ids must be a set"):
        validate_anchor(
            anchor=make_anchor(),
            known_chunk_ids=["chunk_0001"],
            allowed_types={"verbal_claim"},
        )


def test_validate_anchor_rejects_non_set_allowed_types():
    with pytest.raises(TypeError, match="allowed_types must be a set"):
        validate_anchor(
            anchor=make_anchor(),
            known_chunk_ids={"chunk_0001"},
            allowed_types=["verbal_claim"],
        )


def test_validate_anchor_detects_missing_keys():
    anchor = {
        "anchor_id": "anchor_0001",
        "chunk_id": "chunk_0001",
    }

    result = validate_anchor(
        anchor=anchor,
        known_chunk_ids={"chunk_0001"},
        allowed_types={"verbal_claim"},
    )

    assert result["valid"] is False
    assert result["anchor_id"] == "anchor_0001"
    assert any(error.startswith("missing_keys:") for error in result["errors"])


def test_validate_anchor_detects_invalid_type():
    anchor = make_anchor(anchor_type="not_allowed")

    result = validate_anchor(
        anchor=anchor,
        known_chunk_ids={"chunk_0001"},
        allowed_types={"verbal_claim"},
    )

    assert result["valid"] is False
    assert result["type_valid"] is False
    assert "invalid_type" in result["errors"]


def test_validate_anchor_detects_invalid_offsets():
    anchor = make_anchor(char_start=50, char_end=10)

    result = validate_anchor(
        anchor=anchor,
        known_chunk_ids={"chunk_0001"},
        allowed_types={"verbal_claim"},
    )

    assert result["valid"] is False
    assert result["offsets_valid"] is False
    assert "invalid_offsets" in result["errors"]


def test_validate_anchor_detects_invalid_timestamps():
    anchor = make_anchor(start_seconds=20.0, end_seconds=10.0)

    result = validate_anchor(
        anchor=anchor,
        known_chunk_ids={"chunk_0001"},
        allowed_types={"verbal_claim"},
    )

    assert result["valid"] is False
    assert result["timestamps_valid"] is False
    assert "invalid_timestamps" in result["errors"]


def test_validate_anchor_detects_unknown_chunk_reference():
    anchor = make_anchor(chunk_id="chunk_missing")

    result = validate_anchor(
        anchor=anchor,
        known_chunk_ids={"chunk_0001"},
        allowed_types={"verbal_claim"},
    )

    assert result["valid"] is False
    assert result["chunk_reference_valid"] is False
    assert "invalid_chunk_reference" in result["errors"]


def test_validate_anchor_detects_empty_source_text():
    anchor = make_anchor(source_text="   ")

    result = validate_anchor(
        anchor=anchor,
        known_chunk_ids={"chunk_0001"},
        allowed_types={"verbal_claim"},
    )

    assert result["valid"] is False
    assert result["source_text_valid"] is False
    assert "invalid_source_text" in result["errors"]


def test_validate_anchors_accepts_valid_anchors():
    chunks = [
        make_chunk(chunk_id="chunk_0001"),
        make_chunk(chunk_id="chunk_0002"),
    ]

    anchors = [
        make_anchor(anchor_id="anchor_0001", chunk_id="chunk_0001"),
        make_anchor(anchor_id="anchor_0002", chunk_id="chunk_0002"),
    ]

    metrics = validate_anchors(
        anchors=anchors,
        chunks=chunks,
        allowed_types=["verbal_claim", "definition", "example"],
    )

    assert metrics["anchor_count"] == 2
    assert metrics["valid_anchor_count"] == 2
    assert metrics["invalid_anchor_count"] == 0
    assert metrics["anchor_type_validation_pass_rate"] == 1.0
    assert metrics["anchor_offset_validation_pass_rate"] == 1.0
    assert metrics["anchor_timestamp_validation_pass_rate"] == 1.0
    assert metrics["anchor_chunk_reference_pass_rate"] == 1.0
    assert metrics["anchor_source_text_validation_pass_rate"] == 1.0
    assert metrics["invalid_anchors"] == []


def test_validate_anchors_reports_invalid_anchor_metrics():
    chunks = [make_chunk(chunk_id="chunk_0001")]

    valid_anchor = make_anchor(anchor_id="anchor_0001", chunk_id="chunk_0001")
    invalid_anchor = make_anchor(
        anchor_id="anchor_0002",
        chunk_id="chunk_missing",
        anchor_type="not_allowed",
        char_start=20,
        char_end=10,
    )

    metrics = validate_anchors(
        anchors=[valid_anchor, invalid_anchor],
        chunks=chunks,
        allowed_types=["verbal_claim"],
    )

    assert metrics["anchor_count"] == 2
    assert metrics["valid_anchor_count"] == 1
    assert metrics["invalid_anchor_count"] == 1
    assert metrics["anchor_type_validation_pass_rate"] == 0.5
    assert metrics["anchor_offset_validation_pass_rate"] == 0.5
    assert metrics["anchor_timestamp_validation_pass_rate"] == 1.0
    assert metrics["anchor_chunk_reference_pass_rate"] == 0.5
    assert metrics["anchor_source_text_validation_pass_rate"] == 1.0
    assert metrics["invalid_anchors"][0]["anchor_id"] == "anchor_0002"
    assert "invalid_type" in metrics["invalid_anchors"][0]["errors"]
    assert "invalid_offsets" in metrics["invalid_anchors"][0]["errors"]
    assert "invalid_chunk_reference" in metrics["invalid_anchors"][0]["errors"]


def test_validate_anchors_empty_list_returns_clean_metrics():
    metrics = validate_anchors(
        anchors=[],
        chunks=[make_chunk()],
        allowed_types=["verbal_claim"],
    )

    assert metrics["anchor_count"] == 0
    assert metrics["valid_anchor_count"] == 0
    assert metrics["invalid_anchor_count"] == 0
    assert metrics["anchor_type_validation_pass_rate"] == 1.0
    assert metrics["anchor_offset_validation_pass_rate"] == 1.0
    assert metrics["anchor_timestamp_validation_pass_rate"] == 1.0
    assert metrics["anchor_chunk_reference_pass_rate"] == 1.0
    assert metrics["anchor_source_text_validation_pass_rate"] == 1.0
    assert metrics["invalid_anchors"] == []


def test_validate_anchors_rejects_non_list_anchors():
    with pytest.raises(TypeError, match="anchors must be a list"):
        validate_anchors(
            anchors="not anchors",
            chunks=[make_chunk()],
            allowed_types=["verbal_claim"],
        )


def test_validate_anchors_rejects_non_list_chunks():
    with pytest.raises(TypeError, match="chunks must be a list"):
        validate_anchors(
            anchors=[],
            chunks="not chunks",
            allowed_types=["verbal_claim"],
        )


def test_validate_anchors_rejects_non_list_allowed_types():
    with pytest.raises(TypeError, match="allowed_types must be a list"):
        validate_anchors(
            anchors=[],
            chunks=[make_chunk()],
            allowed_types="verbal_claim",
        )


def test_validate_anchors_ignores_non_chunk_objects_when_building_known_ids():
    chunks = [
        make_chunk(chunk_id="chunk_0001"),
        {"chunk_id": "fake_chunk"},
    ]

    anchors = [
        make_anchor(anchor_id="anchor_0001", chunk_id="chunk_0001"),
        make_anchor(anchor_id="anchor_0002", chunk_id="fake_chunk"),
    ]

    metrics = validate_anchors(
        anchors=anchors,
        chunks=chunks,
        allowed_types=["verbal_claim"],
    )

    assert metrics["anchor_count"] == 2
    assert metrics["valid_anchor_count"] == 1
    assert metrics["invalid_anchor_count"] == 1
    assert metrics["invalid_anchors"][0]["anchor_id"] == "anchor_0002"
    assert "invalid_chunk_reference" in metrics["invalid_anchors"][0]["errors"]