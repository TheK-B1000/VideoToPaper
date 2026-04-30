from src.argument.argument_models import TranscriptChunk


def chunk_transcript_segments(
    segments: list[dict],
    max_chunk_chars: int = 1200,
    min_chunk_chars: int = 400,
    overlap_segments: int = 1,
) -> list[TranscriptChunk]:
    """
    Group transcript segments into larger chunks while preserving source offsets,
    timestamps, and original segment IDs.

    This chunker is deterministic and safe for citation work:
    - It never rewrites source_text.
    - It preserves raw char_start / char_end offsets.
    - It preserves video start/end timing.
    - It supports segment-level overlap for future RAG retrieval.
    """
    _validate_chunking_inputs(
        segments=segments,
        max_chunk_chars=max_chunk_chars,
        min_chunk_chars=min_chunk_chars,
        overlap_segments=overlap_segments,
    )

    if not segments:
        return []

    chunks: list[TranscriptChunk] = []
    current_segments: list[dict] = []
    current_char_count = 0

    for segment in segments:
        _validate_segment(segment)

        segment_text = segment["source_text"]
        segment_length = len(segment_text)

        should_flush = (
            current_segments
            and current_char_count + segment_length > max_chunk_chars
            and current_char_count >= min_chunk_chars
        )

        if should_flush:
            chunks.append(
                _build_chunk(
                    chunk_number=len(chunks) + 1,
                    segments=current_segments,
                )
            )

            current_segments = _get_overlap_segments(
                current_segments,
                overlap_segments,
            )
            current_char_count = sum(
                len(overlap_segment["source_text"])
                for overlap_segment in current_segments
            )

        current_segments.append(segment)
        current_char_count += segment_length

    if current_segments:
        chunks.append(
            _build_chunk(
                chunk_number=len(chunks) + 1,
                segments=current_segments,
            )
        )

    return chunks


def _build_chunk(chunk_number: int, segments: list[dict]) -> TranscriptChunk:
    """
    Build one TranscriptChunk from a group of transcript segments.
    """
    if not segments:
        raise ValueError("Cannot build a chunk from an empty segment list")

    chunk_id = f"chunk_{chunk_number:04d}"

    source_text = "".join(
        segment["source_text"]
        for segment in segments
    )

    clean_text = " ".join(
        segment.get("clean_text", segment["source_text"])
        for segment in segments
    ).strip()

    char_start = segments[0]["char_start"]
    char_end = segments[-1]["char_end"]

    start_seconds = segments[0]["start_seconds"]
    end_seconds = segments[-1]["end_seconds"]

    segment_ids = [
        _get_segment_id(segment)
        for segment in segments
    ]

    return TranscriptChunk(
        chunk_id=chunk_id,
        source_text=source_text,
        clean_text=clean_text,
        char_start=char_start,
        char_end=char_end,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        segment_ids=segment_ids,
        chunk_type="transcript_window",
    )


def _get_overlap_segments(
    segments: list[dict],
    overlap_segments: int,
) -> list[dict]:
    """
    Return the last N segments from the current chunk so the next chunk
    has local context.

    Segment-level overlap is safer than character-level overlap because it
    preserves timestamp and offset boundaries.
    """
    if overlap_segments <= 0:
        return []

    return segments[-overlap_segments:]


def _get_segment_id(segment: dict) -> str:
    """
    Get a stable segment ID from a transcript segment.

    Supports either 'segment_id' or 'id' so the chunker is tolerant of small
    schema differences.
    """
    if "segment_id" in segment:
        return segment["segment_id"]

    if "id" in segment:
        return segment["id"]

    raise KeyError("Segment must contain either 'segment_id' or 'id'")


def _validate_chunking_inputs(
    segments: list[dict],
    max_chunk_chars: int,
    min_chunk_chars: int,
    overlap_segments: int,
) -> None:
    """
    Validate chunking arguments before chunking starts.
    """
    if not isinstance(segments, list):
        raise TypeError("segments must be a list")

    if not isinstance(max_chunk_chars, int):
        raise TypeError("max_chunk_chars must be an integer")

    if not isinstance(min_chunk_chars, int):
        raise TypeError("min_chunk_chars must be an integer")

    if not isinstance(overlap_segments, int):
        raise TypeError("overlap_segments must be an integer")

    if max_chunk_chars <= 0:
        raise ValueError("max_chunk_chars must be greater than 0")

    if min_chunk_chars <= 0:
        raise ValueError("min_chunk_chars must be greater than 0")

    if min_chunk_chars > max_chunk_chars:
        raise ValueError("min_chunk_chars cannot be greater than max_chunk_chars")

    if overlap_segments < 0:
        raise ValueError("overlap_segments cannot be negative")


def _validate_segment(segment: dict) -> None:
    """
    Validate the minimum fields needed to safely chunk a transcript segment.
    """
    if not isinstance(segment, dict):
        raise TypeError("Each segment must be a dictionary")

    required_keys = [
        "source_text",
        "char_start",
        "char_end",
        "start_seconds",
        "end_seconds",
    ]

    missing_keys = [
        key for key in required_keys
        if key not in segment
    ]

    if missing_keys:
        raise ValueError(f"Segment is missing required keys: {missing_keys}")

    if "segment_id" not in segment and "id" not in segment:
        raise ValueError("Segment must contain either 'segment_id' or 'id'")

    if not isinstance(segment["source_text"], str):
        raise TypeError("segment source_text must be a string")

    if not isinstance(segment["char_start"], int):
        raise TypeError("segment char_start must be an integer")

    if not isinstance(segment["char_end"], int):
        raise TypeError("segment char_end must be an integer")

    if segment["char_start"] < 0:
        raise ValueError("segment char_start cannot be negative")

    if segment["char_end"] < segment["char_start"]:
        raise ValueError("segment char_end cannot be less than char_start")

    if segment["end_seconds"] < segment["start_seconds"]:
        raise ValueError("segment end_seconds cannot be less than start_seconds")