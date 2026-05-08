import pytest

from src.argument.argument_models import TranscriptChunk
from src.argument.source_alignment_validator import (
    build_full_source_text_from_segments,
    validate_chunk_source_alignment,
)


def make_segments() -> list[dict]:
    return [
        {
            "segment_id": "seg_0001",
            "source_text": "The key point is that retrieval can fail silently. ",
            "char_start": 0,
            "char_end": 51,
            "start_seconds": 0.0,
            "end_seconds": 8.0,
        },
        {
            "segment_id": "seg_0002",
            "source_text": "For example, a chunk can miss important context. ",
            "char_start": 51,
            "char_end": 100,
            "start_seconds": 8.0,
            "end_seconds": 16.0,
        },
        {
            "segment_id": "seg_0003",
            "source_text": "However, overlap helps preserve meaning.",
            "char_start": 100,
            "char_end": 140,
            "start_seconds": 16.0,
            "end_seconds": 24.0,
        },
    ]


def make_chunk(
    chunk_id: str = "chunk_0001",
    source_text: str = "The key point is that retrieval can fail silently. ",
    char_start: int = 0,
    char_end: int = 51,
) -> TranscriptChunk:
    return TranscriptChunk(
        chunk_id=chunk_id,
        source_text=source_text,
        clean_text=source_text.strip(),
        char_start=char_start,
        char_end=char_end,
        start_seconds=0.0,
        end_seconds=8.0,
        segment_ids=["seg_0001"],
        chunk_type="transcript_window",
    )


def test_build_full_source_text_from_segments_joins_source_text_in_order():
    segments = make_segments()

    full_source_text = build_full_source_text_from_segments(segments)

    expected = (
        "The key point is that retrieval can fail silently. "
        "For example, a chunk can miss important context. "
        "However, overlap helps preserve meaning."
    )

    assert full_source_text == expected


def test_build_full_source_text_rejects_non_list_segments():
    with pytest.raises(TypeError, match="segments must be a list"):
        build_full_source_text_from_segments("not segments")


def test_build_full_source_text_rejects_non_dict_segment():
    with pytest.raises(TypeError, match="each segment must be a dictionary"):
        build_full_source_text_from_segments(["not a segment"])


def test_build_full_source_text_rejects_missing_source_text():
    segments = [
        {
            "segment_id": "seg_0001",
            "text": "Wrong key.",
        }
    ]

    with pytest.raises(ValueError, match="segment is missing source_text"):
        build_full_source_text_from_segments(segments)


def test_build_full_source_text_rejects_non_string_source_text():
    segments = [
        {
            "segment_id": "seg_0001",
            "source_text": 123,
        }
    ]

    with pytest.raises(TypeError, match="segment source_text must be a string"):
        build_full_source_text_from_segments(segments)


def test_validate_chunk_source_alignment_accepts_aligned_chunk():
    segments = make_segments()
    full_source_text = build_full_source_text_from_segments(segments)

    chunk = make_chunk(
        chunk_id="chunk_0001",
        source_text="The key point is that retrieval can fail silently. ",
        char_start=0,
        char_end=51,
    )

    metrics = validate_chunk_source_alignment(
        chunks=[chunk],
        full_source_text=full_source_text,
    )

    assert metrics["chunk_source_alignment_count"] == 1
    assert metrics["chunk_source_alignment_pass_count"] == 1
    assert metrics["chunk_source_alignment_fail_count"] == 0
    assert metrics["chunk_source_alignment_pass_rate"] == 1.0
    assert metrics["misaligned_chunks"] == []


def test_validate_chunk_source_alignment_accepts_multi_segment_chunk():
    segments = make_segments()
    full_source_text = build_full_source_text_from_segments(segments)

    source_text = (
        "The key point is that retrieval can fail silently. "
        "For example, a chunk can miss important context. "
    )

    chunk = make_chunk(
        chunk_id="chunk_0001",
        source_text=source_text,
        char_start=0,
        char_end=100,
    )

    metrics = validate_chunk_source_alignment(
        chunks=[chunk],
        full_source_text=full_source_text,
    )

    assert metrics["chunk_source_alignment_count"] == 1
    assert metrics["chunk_source_alignment_pass_count"] == 1
    assert metrics["chunk_source_alignment_fail_count"] == 0
    assert metrics["chunk_source_alignment_pass_rate"] == 1.0


def test_validate_chunk_source_alignment_detects_misaligned_chunk_text():
    segments = make_segments()
    full_source_text = build_full_source_text_from_segments(segments)

    chunk = make_chunk(
        chunk_id="chunk_0001",
        source_text="This text does not match the original transcript slice.",
        char_start=0,
        char_end=51,
    )

    metrics = validate_chunk_source_alignment(
        chunks=[chunk],
        full_source_text=full_source_text,
    )

    assert metrics["chunk_source_alignment_count"] == 1
    assert metrics["chunk_source_alignment_pass_count"] == 0
    assert metrics["chunk_source_alignment_fail_count"] == 1
    assert metrics["chunk_source_alignment_pass_rate"] == 0.0
    assert len(metrics["misaligned_chunks"]) == 1

    misaligned = metrics["misaligned_chunks"][0]

    assert misaligned["chunk_id"] == "chunk_0001"
    assert misaligned["char_start"] == 0
    assert misaligned["char_end"] == 51
    assert misaligned["expected_text"] == "This text does not match the original transcript slice."
    assert misaligned["actual_text"] == "The key point is that retrieval can fail silently. "


def test_validate_chunk_source_alignment_detects_misaligned_offsets():
    segments = make_segments()
    full_source_text = build_full_source_text_from_segments(segments)

    chunk = make_chunk(
        chunk_id="chunk_0001",
        source_text="The key point is that retrieval can fail silently. ",
        char_start=1,
        char_end=52,
    )

    metrics = validate_chunk_source_alignment(
        chunks=[chunk],
        full_source_text=full_source_text,
    )

    assert metrics["chunk_source_alignment_fail_count"] == 1
    assert metrics["chunk_source_alignment_pass_rate"] == 0.0
    assert metrics["misaligned_chunks"][0]["chunk_id"] == "chunk_0001"


def test_validate_chunk_source_alignment_handles_empty_chunks():
    metrics = validate_chunk_source_alignment(
        chunks=[],
        full_source_text="Some transcript text.",
    )

    assert metrics["chunk_source_alignment_count"] == 0
    assert metrics["chunk_source_alignment_pass_count"] == 0
    assert metrics["chunk_source_alignment_fail_count"] == 0
    assert metrics["chunk_source_alignment_pass_rate"] == 1.0
    assert metrics["misaligned_chunks"] == []


def test_validate_chunk_source_alignment_rejects_non_list_chunks():
    with pytest.raises(TypeError, match="chunks must be a list"):
        validate_chunk_source_alignment(
            chunks="not chunks",
            full_source_text="Some transcript text.",
        )


def test_validate_chunk_source_alignment_rejects_non_string_full_source_text():
    with pytest.raises(TypeError, match="full_source_text must be a string"):
        validate_chunk_source_alignment(
            chunks=[],
            full_source_text=123,
        )


def test_validate_chunk_source_alignment_rejects_non_chunk_item():
    with pytest.raises(TypeError, match="each chunk must be a TranscriptChunk"):
        validate_chunk_source_alignment(
            chunks=[{"chunk_id": "chunk_0001"}],
            full_source_text="Some transcript text.",
        )