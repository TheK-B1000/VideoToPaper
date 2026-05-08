from src.argument.argument_models import TranscriptChunk


def validate_anchors(
    anchors: list[dict],
    chunks: list[TranscriptChunk],
    allowed_types: list[str],
) -> dict:
    """
    Validate anchor moments and return safety metrics.

    Args:
        anchors: Anchor dictionaries produced by anchor_detector.py.
        chunks: TranscriptChunk objects the anchors should reference.
        allowed_types: Anchor types allowed by config.

    Returns:
        Dictionary of validation metrics.
    """
    if not isinstance(anchors, list):
        raise TypeError("anchors must be a list")

    if not isinstance(chunks, list):
        raise TypeError("chunks must be a list")

    if not isinstance(allowed_types, list):
        raise TypeError("allowed_types must be a list")

    known_chunk_ids = {
        chunk.chunk_id
        for chunk in chunks
        if isinstance(chunk, TranscriptChunk)
    }

    allowed_type_set = set(allowed_types)

    if not anchors:
        return {
            "anchor_count": 0,
            "valid_anchor_count": 0,
            "invalid_anchor_count": 0,
            "anchor_type_validation_pass_rate": 1.0,
            "anchor_offset_validation_pass_rate": 1.0,
            "anchor_timestamp_validation_pass_rate": 1.0,
            "anchor_chunk_reference_pass_rate": 1.0,
            "anchor_source_text_validation_pass_rate": 1.0,
            "invalid_anchors": [],
        }

    invalid_anchors = []

    type_pass_count = 0
    offset_pass_count = 0
    timestamp_pass_count = 0
    chunk_reference_pass_count = 0
    source_text_pass_count = 0

    for anchor in anchors:
        anchor_result = validate_anchor(
            anchor=anchor,
            known_chunk_ids=known_chunk_ids,
            allowed_types=allowed_type_set,
        )

        if anchor_result["type_valid"]:
            type_pass_count += 1

        if anchor_result["offsets_valid"]:
            offset_pass_count += 1

        if anchor_result["timestamps_valid"]:
            timestamp_pass_count += 1

        if anchor_result["chunk_reference_valid"]:
            chunk_reference_pass_count += 1

        if anchor_result["source_text_valid"]:
            source_text_pass_count += 1

        if not anchor_result["valid"]:
            invalid_anchors.append(anchor_result)

    anchor_count = len(anchors)
    invalid_anchor_count = len(invalid_anchors)
    valid_anchor_count = anchor_count - invalid_anchor_count

    return {
        "anchor_count": anchor_count,
        "valid_anchor_count": valid_anchor_count,
        "invalid_anchor_count": invalid_anchor_count,
        "anchor_type_validation_pass_rate": type_pass_count / anchor_count,
        "anchor_offset_validation_pass_rate": offset_pass_count / anchor_count,
        "anchor_timestamp_validation_pass_rate": timestamp_pass_count / anchor_count,
        "anchor_chunk_reference_pass_rate": chunk_reference_pass_count / anchor_count,
        "anchor_source_text_validation_pass_rate": source_text_pass_count / anchor_count,
        "invalid_anchors": invalid_anchors,
    }


def validate_anchor(
    anchor: dict,
    known_chunk_ids: set[str],
    allowed_types: set[str],
) -> dict:
    """
    Validate one anchor moment.
    """
    if not isinstance(anchor, dict):
        raise TypeError("anchor must be a dictionary")

    if not isinstance(known_chunk_ids, set):
        raise TypeError("known_chunk_ids must be a set")

    if not isinstance(allowed_types, set):
        raise TypeError("allowed_types must be a set")

    required_keys = [
        "anchor_id",
        "chunk_id",
        "type",
        "source_text",
        "char_start",
        "char_end",
        "start_seconds",
        "end_seconds",
    ]

    missing_keys = [
        key for key in required_keys
        if key not in anchor
    ]

    errors = []

    if missing_keys:
        return {
            "anchor_id": anchor.get("anchor_id", None),
            "valid": False,
            "type_valid": False,
            "offsets_valid": False,
            "timestamps_valid": False,
            "chunk_reference_valid": False,
            "source_text_valid": False,
            "errors": [f"missing_keys:{missing_keys}"],
        }

    type_valid = (
        isinstance(anchor["type"], str)
        and anchor["type"] in allowed_types
    )

    offsets_valid = (
        isinstance(anchor["char_start"], int)
        and isinstance(anchor["char_end"], int)
        and anchor["char_start"] >= 0
        and anchor["char_end"] >= anchor["char_start"]
    )

    timestamps_valid = (
        isinstance(anchor["start_seconds"], (int, float))
        and isinstance(anchor["end_seconds"], (int, float))
        and anchor["start_seconds"] >= 0
        and anchor["end_seconds"] >= anchor["start_seconds"]
    )

    chunk_reference_valid = (
        isinstance(anchor["chunk_id"], str)
        and anchor["chunk_id"] in known_chunk_ids
    )

    source_text_valid = (
        isinstance(anchor["source_text"], str)
        and bool(anchor["source_text"].strip())
    )

    if not type_valid:
        errors.append("invalid_type")

    if not offsets_valid:
        errors.append("invalid_offsets")

    if not timestamps_valid:
        errors.append("invalid_timestamps")

    if not chunk_reference_valid:
        errors.append("invalid_chunk_reference")

    if not source_text_valid:
        errors.append("invalid_source_text")

    valid = (
        type_valid
        and offsets_valid
        and timestamps_valid
        and chunk_reference_valid
        and source_text_valid
    )

    return {
        "anchor_id": anchor["anchor_id"],
        "valid": valid,
        "type_valid": type_valid,
        "offsets_valid": offsets_valid,
        "timestamps_valid": timestamps_valid,
        "chunk_reference_valid": chunk_reference_valid,
        "source_text_valid": source_text_valid,
        "errors": errors,
    }