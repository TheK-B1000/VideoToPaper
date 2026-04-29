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
        cleaned_segment = validate_segment(segment, config)
        cleaned_segments.append(cleaned_segment)

    return cleaned_segments