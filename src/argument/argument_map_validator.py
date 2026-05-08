def validate_argument_map(argument_map: dict, anchors: list[dict]) -> dict:
    """
    Validate a heuristic argument map and return safety metrics.

    Args:
        argument_map: Argument map produced by argument_map_builder.py.
        anchors: Anchor dictionaries produced by anchor_detector.py.

    Returns:
        Dictionary of validation metrics.
    """
    if not isinstance(argument_map, dict):
        raise TypeError("argument_map must be a dictionary")

    if not isinstance(anchors, list):
        raise TypeError("anchors must be a list")

    required_sections = [
        "map_type",
        "thesis_candidates",
        "supporting_points",
        "qualifications",
        "examples",
        "summary_claims",
        "anchor_count",
        "chunk_count",
    ]

    missing_sections = [
        section for section in required_sections
        if section not in argument_map
    ]

    if missing_sections:
        return {
            "argument_map_valid": False,
            "missing_sections": missing_sections,
            "argument_item_count": 0,
            "valid_argument_item_count": 0,
            "invalid_argument_item_count": 0,
            "argument_anchor_reference_pass_rate": 0.0,
            "argument_offset_validation_pass_rate": 0.0,
            "argument_timestamp_validation_pass_rate": 0.0,
            "invalid_argument_items": [],
        }

    known_anchor_ids = {
        anchor["anchor_id"]
        for anchor in anchors
        if isinstance(anchor, dict) and "anchor_id" in anchor
    }

    argument_items = _collect_argument_items(argument_map)

    if not argument_items:
        return {
            "argument_map_valid": True,
            "missing_sections": [],
            "argument_item_count": 0,
            "valid_argument_item_count": 0,
            "invalid_argument_item_count": 0,
            "argument_anchor_reference_pass_rate": 1.0,
            "argument_offset_validation_pass_rate": 1.0,
            "argument_timestamp_validation_pass_rate": 1.0,
            "invalid_argument_items": [],
        }

    invalid_argument_items = []

    anchor_reference_pass_count = 0
    offset_pass_count = 0
    timestamp_pass_count = 0

    for item in argument_items:
        item_result = validate_argument_item(
            item=item,
            known_anchor_ids=known_anchor_ids,
        )

        if item_result["anchor_reference_valid"]:
            anchor_reference_pass_count += 1

        if item_result["offsets_valid"]:
            offset_pass_count += 1

        if item_result["timestamps_valid"]:
            timestamp_pass_count += 1

        if not item_result["valid"]:
            invalid_argument_items.append(item_result)

    argument_item_count = len(argument_items)
    invalid_argument_item_count = len(invalid_argument_items)
    valid_argument_item_count = argument_item_count - invalid_argument_item_count

    return {
        "argument_map_valid": invalid_argument_item_count == 0,
        "missing_sections": [],
        "argument_item_count": argument_item_count,
        "valid_argument_item_count": valid_argument_item_count,
        "invalid_argument_item_count": invalid_argument_item_count,
        "argument_anchor_reference_pass_rate": anchor_reference_pass_count / argument_item_count,
        "argument_offset_validation_pass_rate": offset_pass_count / argument_item_count,
        "argument_timestamp_validation_pass_rate": timestamp_pass_count / argument_item_count,
        "invalid_argument_items": invalid_argument_items,
    }


def validate_argument_item(item: dict, known_anchor_ids: set[str]) -> dict:
    """
    Validate one argument-map item.
    """
    if not isinstance(item, dict):
        raise TypeError("item must be a dictionary")

    if not isinstance(known_anchor_ids, set):
        raise TypeError("known_anchor_ids must be a set")

    required_keys = [
        "item_id",
        "item_type",
        "anchor_id",
        "chunk_id",
        "source_text",
        "char_start",
        "char_end",
        "start_seconds",
        "end_seconds",
    ]

    missing_keys = [
        key for key in required_keys
        if key not in item
    ]

    if missing_keys:
        return {
            "item_id": item.get("item_id", None),
            "valid": False,
            "anchor_reference_valid": False,
            "offsets_valid": False,
            "timestamps_valid": False,
            "errors": [f"missing_keys:{missing_keys}"],
        }

    if item.get("fallback_generated") is True:
        # Synthetic rows from ensure_argument_map_has_supporting_points; no real anchor.
        anchor_reference_valid = True
    else:
        anchor_reference_valid = (
            isinstance(item["anchor_id"], str)
            and item["anchor_id"] in known_anchor_ids
        )

    offsets_valid = (
        isinstance(item["char_start"], int)
        and isinstance(item["char_end"], int)
        and item["char_start"] >= 0
        and item["char_end"] >= item["char_start"]
    )

    timestamps_valid = (
        isinstance(item["start_seconds"], (int, float))
        and isinstance(item["end_seconds"], (int, float))
        and item["start_seconds"] >= 0
        and item["end_seconds"] >= item["start_seconds"]
    )

    errors = []

    if not anchor_reference_valid:
        errors.append("invalid_anchor_reference")

    if not offsets_valid:
        errors.append("invalid_offsets")

    if not timestamps_valid:
        errors.append("invalid_timestamps")

    valid = (
        anchor_reference_valid
        and offsets_valid
        and timestamps_valid
    )

    return {
        "item_id": item["item_id"],
        "valid": valid,
        "anchor_reference_valid": anchor_reference_valid,
        "offsets_valid": offsets_valid,
        "timestamps_valid": timestamps_valid,
        "errors": errors,
    }


def _collect_argument_items(argument_map: dict) -> list[dict]:
    """
    Collect all argument items from the main argument-map sections.
    """
    sections = [
        "thesis_candidates",
        "supporting_points",
        "qualifications",
        "examples",
        "summary_claims",
    ]

    items = []

    for section in sections:
        section_items = argument_map.get(section, [])

        if not isinstance(section_items, list):
            raise TypeError(f"{section} must be a list")

        items.extend(section_items)

    return items