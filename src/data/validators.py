from src.core.text_cleaner import clean_text


def validate_segment(segment: dict, config=None) -> dict:
    """
    Validate and normalize a single transcript segment.

    Args:
        segment: A dictionary containing text, start_time, and end_time.
        config: Optional project config dictionary.

    Returns:
        A cleaned and validated transcript segment.

    Raises:
        TypeError: If segment is not a dictionary or fields have invalid types.
        ValueError: If required fields are missing or timestamp values are invalid.
    """

    if not isinstance(segment, dict):
        raise TypeError("segment must be a dictionary")

    required_fields = ["text", "start_time", "end_time"]
    allow_negative_timestamps = False
    require_end_time_after_start_time = True
    coerce_timestamps_to_float = True

    if config is not None:
        transcript_config = config.get("transcript", {})
        validation_config = config.get("validation", {})

        required_fields = transcript_config.get(
            "required_segment_fields",
            required_fields,
        )

        allow_negative_timestamps = validation_config.get(
            "allow_negative_timestamps",
            False,
        )

        require_end_time_after_start_time = validation_config.get(
            "require_end_time_after_start_time",
            True,
        )

        coerce_timestamps_to_float = validation_config.get(
            "coerce_timestamps_to_float",
            True,
        )

    for field in required_fields:
        if field not in segment:
            raise ValueError(f"missing required field: {field}")

    text_raw = segment["text"]
    if not isinstance(text_raw, str):
        raise TypeError("text must be a string")

    start_time = segment["start_time"]
    end_time = segment["end_time"]

    if not isinstance(start_time, (int, float)):
        raise TypeError("start_time must be a number")

    if not isinstance(end_time, (int, float)):
        raise TypeError("end_time must be a number")

    if not allow_negative_timestamps and start_time < 0:
        raise ValueError("start_time cannot be negative")

    if require_end_time_after_start_time and end_time <= start_time:
        raise ValueError("end_time must be greater than start_time")

    cleaned_text = clean_text(text_raw, config)

    if coerce_timestamps_to_float:
        start_time = float(start_time)
        end_time = float(end_time)

    validated_segment = {
        "text": text_raw,
        "cleaned_text": cleaned_text,
        "start_time": start_time,
        "end_time": end_time,
    }

    if "char_start" in segment or "char_end" in segment:
        if "char_start" not in segment:
            raise ValueError("missing required offset field: char_start")
        if "char_end" not in segment:
            raise ValueError("missing required offset field: char_end")

        char_start = segment["char_start"]
        char_end = segment["char_end"]

        if not isinstance(char_start, int):
            raise TypeError("char_start must be an integer")

        if not isinstance(char_end, int):
            raise TypeError("char_end must be an integer")

        if char_start < 0:
            raise ValueError("char_start cannot be negative")

        if char_end <= char_start:
            raise ValueError("char_end must be greater than char_start")

        validated_segment["char_start"] = char_start
        validated_segment["char_end"] = char_end
    
    return validated_segment
