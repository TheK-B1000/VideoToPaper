from src.argument.argument_models import TranscriptChunk


def validate_chunks(chunks: list[TranscriptChunk]) -> dict:
    """
    Validate transcript chunks and return safety metrics.

    This does not mutate or fix chunks. It only checks whether the chunks
    are safe enough for downstream argument extraction and citation work.

    Args:
        chunks: List of TranscriptChunk objects.

    Returns:
        Dictionary of validation metrics.
    """
    if not isinstance(chunks, list):
        raise TypeError("chunks must be a list")

    if not chunks:
        return {
            "chunk_count": 0,
            "valid_chunk_count": 0,
            "invalid_chunk_count": 0,
            "chunk_offset_validation_pass_rate": 1.0,
            "chunk_timestamp_validation_pass_rate": 1.0,
            "chunk_segment_id_validation_pass_rate": 1.0,
            "chunk_source_text_validation_pass_rate": 1.0,
            "invalid_chunks": [],
        }

    invalid_chunks = []

    offset_pass_count = 0
    timestamp_pass_count = 0
    segment_id_pass_count = 0
    source_text_pass_count = 0

    for chunk in chunks:
        chunk_result = validate_chunk(chunk)

        if chunk_result["offsets_valid"]:
            offset_pass_count += 1

        if chunk_result["timestamps_valid"]:
            timestamp_pass_count += 1

        if chunk_result["segment_ids_valid"]:
            segment_id_pass_count += 1

        if chunk_result["source_text_valid"]:
            source_text_pass_count += 1

        if not chunk_result["valid"]:
            invalid_chunks.append(chunk_result)

    chunk_count = len(chunks)
    invalid_chunk_count = len(invalid_chunks)
    valid_chunk_count = chunk_count - invalid_chunk_count

    return {
        "chunk_count": chunk_count,
        "valid_chunk_count": valid_chunk_count,
        "invalid_chunk_count": invalid_chunk_count,
        "chunk_offset_validation_pass_rate": offset_pass_count / chunk_count,
        "chunk_timestamp_validation_pass_rate": timestamp_pass_count / chunk_count,
        "chunk_segment_id_validation_pass_rate": segment_id_pass_count / chunk_count,
        "chunk_source_text_validation_pass_rate": source_text_pass_count / chunk_count,
        "invalid_chunks": invalid_chunks,
    }


def validate_chunk(chunk: TranscriptChunk) -> dict:
    """
    Validate a single TranscriptChunk.

    Args:
        chunk: TranscriptChunk object.

    Returns:
        Dictionary describing whether the chunk is valid and why.
    """
    if not isinstance(chunk, TranscriptChunk):
        raise TypeError("chunk must be a TranscriptChunk")

    offsets_valid = (
        isinstance(chunk.char_start, int)
        and isinstance(chunk.char_end, int)
        and chunk.char_start >= 0
        and chunk.char_end >= chunk.char_start
    )

    timestamps_valid = (
        isinstance(chunk.start_seconds, (int, float))
        and isinstance(chunk.end_seconds, (int, float))
        and chunk.start_seconds >= 0
        and chunk.end_seconds >= chunk.start_seconds
    )

    segment_ids_valid = (
        isinstance(chunk.segment_ids, list)
        and len(chunk.segment_ids) > 0
        and all(isinstance(segment_id, str) and segment_id.strip() for segment_id in chunk.segment_ids)
    )

    source_text_valid = (
        isinstance(chunk.source_text, str)
        and bool(chunk.source_text)
    )

    valid = (
        offsets_valid
        and timestamps_valid
        and segment_ids_valid
        and source_text_valid
    )

    errors = []

    if not offsets_valid:
        errors.append("invalid_offsets")

    if not timestamps_valid:
        errors.append("invalid_timestamps")

    if not segment_ids_valid:
        errors.append("invalid_segment_ids")

    if not source_text_valid:
        errors.append("invalid_source_text")

    return {
        "chunk_id": chunk.chunk_id,
        "valid": valid,
        "offsets_valid": offsets_valid,
        "timestamps_valid": timestamps_valid,
        "segment_ids_valid": segment_ids_valid,
        "source_text_valid": source_text_valid,
        "errors": errors,
    }