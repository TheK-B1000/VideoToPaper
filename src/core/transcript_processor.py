from src.data.validators import validate_segment

def process_transcript(raw_transcript: list, config=None) -> list:
    """
    Process a raw transcript into cleaned, validated transcript segments.

    Args:
        raw_transcript: A list of raw transcript segment dictionaries.
        config: Optional project config dictionary.

    Returns:
        A list of cleaned and validated transcript segment dictionaries.

    Raises:
        TypeError: If raw_transcript is not a list.
        ValueError: If the transcript is empty or any segment is invalid.
    """
    if not isinstance(raw_transcript, list):
        raise TypeError("raw_transcript must be a list")

    if not raw_transcript:
        raise ValueError("raw_transcript cannot be empty")

    cleaned_segments = []

    for segment in raw_transcript:
        validated = validate_segment(segment, config)
        out = {
            "text": validated["text"],
            "cleaned_text": validated["cleaned_text"],
            "start_time": validated["start_time"],
            "end_time": validated["end_time"],
        }
        if "char_start" in validated:
            out["char_start"] = validated["char_start"]
            out["char_end"] = validated["char_end"]
        cleaned_segments.append(out)

    return cleaned_segments
