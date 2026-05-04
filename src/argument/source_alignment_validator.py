from src.argument.argument_models import TranscriptChunk


def build_full_source_text_from_segments(segments: list[dict]) -> str:
    """
    Build the full source transcript text from ordered transcript segments.

    This assumes the segments are already in transcript order.
    """
    if not isinstance(segments, list):
        raise TypeError("segments must be a list")

    source_parts = []

    for segment in segments:
        if not isinstance(segment, dict):
            raise TypeError("each segment must be a dictionary")

        if "source_text" not in segment:
            raise ValueError("segment is missing source_text")

        if not isinstance(segment["source_text"], str):
            raise TypeError("segment source_text must be a string")

        source_parts.append(segment["source_text"])

    return "".join(source_parts)


def validate_chunk_source_alignment(
    chunks: list[TranscriptChunk],
    full_source_text: str,
) -> dict:
    """
    Validate that each chunk's char offsets resolve exactly to its source_text.

    Args:
        chunks: TranscriptChunk objects.
        full_source_text: Full raw/source transcript text.

    Returns:
        Alignment validation metrics.
    """
    if not isinstance(chunks, list):
        raise TypeError("chunks must be a list")

    if not isinstance(full_source_text, str):
        raise TypeError("full_source_text must be a string")

    if not chunks:
        return {
            "chunk_source_alignment_count": 0,
            "chunk_source_alignment_pass_count": 0,
            "chunk_source_alignment_fail_count": 0,
            "chunk_source_alignment_pass_rate": 1.0,
            "misaligned_chunks": [],
        }

    misaligned_chunks = []

    for chunk in chunks:
        if not isinstance(chunk, TranscriptChunk):
            raise TypeError("each chunk must be a TranscriptChunk")

        extracted_text = full_source_text[chunk.char_start:chunk.char_end]
        aligned = extracted_text == chunk.source_text

        if not aligned:
            misaligned_chunks.append(
                {
                    "chunk_id": chunk.chunk_id,
                    "char_start": chunk.char_start,
                    "char_end": chunk.char_end,
                    "expected_text": chunk.source_text,
                    "actual_text": extracted_text,
                }
            )

    chunk_count = len(chunks)
    fail_count = len(misaligned_chunks)
    pass_count = chunk_count - fail_count

    return {
        "chunk_source_alignment_count": chunk_count,
        "chunk_source_alignment_pass_count": pass_count,
        "chunk_source_alignment_fail_count": fail_count,
        "chunk_source_alignment_pass_rate": pass_count / chunk_count,
        "misaligned_chunks": misaligned_chunks,
    }