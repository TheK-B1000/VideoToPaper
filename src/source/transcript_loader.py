from src.data.json_store import load_json

def build_source_text(raw_segments: list) -> str:
    """
    Build one source transcript string from raw transcript segments.

    Args:
        raw_segments: A list of transcript segment dictionaries.

    Returns:
        A single source transcript string.

    Raises:
        TypeError: If raw_segments is not a list.
        ValueError: If a segment is missing text.
    """
    if not isinstance(raw_segments, list):
        raise TypeError("raw_segments must be a list")
    
    source_parts = []

    for segment in raw_segments:
        if not isinstance(segment, dict):
            raise TypeError("each segment must be a dictionary")
        
        if "text" not in segment:
            raise ValueError("each segment must contain text")
        
        text = segment["text"]

        if not isinstance(text, str):
            raise TypeError("text must be a string")
        
        source_parts.append(text)
    return " ".join(source_parts)


def add_character_offsets(raw_segments: list) -> tuple[list, str]:
    """
    Add character offsets to transcript segments.

    Args:
        raw_segments: A list of transcript segment dictionaries.

    Returns:
        A tuple containing:
        - list of segments with char_start and char_end
        - source transcript text

    Raises:
        TypeError: If raw_segments is not a list.
    """
    if not isinstance(raw_segments, list):
        raise TypeError("raw_segments must be a list")
    
    offset_segments = []
    source_parts = []
    cursor = 0

    for index, segment in enumerate(raw_segments):
        if not isinstance(segment, dict):
            raise TypeError("each segment must be a dictionary")
        
        if "text" not in segment:
            raise ValueError("each segment must contain text")
        
        text = segment["text"]

        if not isinstance(text, str):
            raise TypeError("text must be a string")

        if index > 0:
            source_parts.append(" ")
            cursor += 1
        
        char_start = cursor
        source_parts.append(text)
        cursor += len(text)
        char_end = cursor

        offset_segment = dict(segment)
        offset_segment["char_start"] = char_start
        offset_segment["char_end"] = char_end

        offset_segments.append(offset_segment)
    
    source_text = "".join(source_parts)

    return offset_segments, source_text


def load_transcript(path: str) -> dict:
    """
    Load a transcript JSON file and add source text plus character offsets.

    Args:
        path: Path to the raw transcript JSON file.

    Returns:
        A dictionary containing:
        - source_text
        - segments

    Raises:
        TypeError: If path is not a string.
        ValueError: If transcript JSON is not a list.
    """
    raw_segments = load_json(path)

    if not isinstance(raw_segments, list):
        raise ValueError("transcript file must contain a list of segments")

    offset_segments, source_text = add_character_offsets(raw_segments)

    return {
        "source_text": source_text,
        "segments": offset_segments
    }