import pytest

from src.argument.chunker import chunk_transcript_segments


def make_segments_and_full_source() -> tuple[str, list[dict]]:
    """
    Four caption-style segments separated by single spaces in the canonical transcript.

    Segment ``source_text`` values omit those separators; offsets match ``full_source_text``.
    """
    texts = [
        "This is the first segment.",
        "This is the second segment.",
        "This is the third segment.",
        "This is the fourth segment.",
    ]
    segments: list[dict] = []
    cursor = 0
    full_parts: list[str] = []
    for index, text in enumerate(texts):
        full_parts.append(text)
        char_start = cursor
        char_end = cursor + len(text)
        segments.append(
            {
                "segment_id": f"seg_{index + 1:04d}",
                "source_text": text,
                "clean_text": text,
                "char_start": char_start,
                "char_end": char_end,
                "start_seconds": float(index * 5),
                "end_seconds": float((index + 1) * 5),
            }
        )
        cursor = char_end
        if index < len(texts) - 1:
            full_parts.append(" ")
            cursor += 1

    full_source_text = "".join(full_parts)
    assert len(full_source_text) == segments[-1]["char_end"]
    return full_source_text, segments


def test_chunk_transcript_segments_returns_chunks():
    full_source_text, segments = make_segments_and_full_source()

    chunks = chunk_transcript_segments(
        segments=segments,
        full_source_text=full_source_text,
        max_chunk_chars=60,
        min_chunk_chars=30,
        overlap_segments=1,
    )

    assert len(chunks) > 0
    assert chunks[0].chunk_id == "chunk_0001"
    assert chunks[0].chunk_type == "transcript_window"


def test_chunk_preserves_source_text_with_inter_segment_spaces():
    full_source_text, segments = make_segments_and_full_source()

    chunks = chunk_transcript_segments(
        segments=segments,
        full_source_text=full_source_text,
        max_chunk_chars=60,
        min_chunk_chars=30,
        overlap_segments=0,
    )

    first_chunk = chunks[0]
    expected = full_source_text[
        segments[0]["char_start"] : segments[1]["char_end"]
    ]
    assert first_chunk.source_text == expected
    assert "first segment. This is the second" in first_chunk.source_text


def test_chunk_preserves_offsets():
    full_source_text, segments = make_segments_and_full_source()

    chunks = chunk_transcript_segments(
        segments=segments,
        full_source_text=full_source_text,
        max_chunk_chars=60,
        min_chunk_chars=30,
        overlap_segments=0,
    )

    first_chunk = chunks[0]

    assert first_chunk.char_start == segments[0]["char_start"]
    assert first_chunk.char_end == segments[1]["char_end"]


def test_chunk_preserves_timestamps():
    full_source_text, segments = make_segments_and_full_source()

    chunks = chunk_transcript_segments(
        segments=segments,
        full_source_text=full_source_text,
        max_chunk_chars=60,
        min_chunk_chars=30,
        overlap_segments=0,
    )

    first_chunk = chunks[0]

    assert first_chunk.start_seconds == segments[0]["start_seconds"]
    assert first_chunk.end_seconds == segments[1]["end_seconds"]


def test_chunk_preserves_segment_ids():
    full_source_text, segments = make_segments_and_full_source()

    chunks = chunk_transcript_segments(
        segments=segments,
        full_source_text=full_source_text,
        max_chunk_chars=60,
        min_chunk_chars=30,
        overlap_segments=0,
    )

    first_chunk = chunks[0]

    assert first_chunk.segment_ids == ["seg_0001", "seg_0002"]


def test_chunk_uses_segment_overlap():
    full_source_text, segments = make_segments_and_full_source()

    chunks = chunk_transcript_segments(
        segments=segments,
        full_source_text=full_source_text,
        max_chunk_chars=60,
        min_chunk_chars=30,
        overlap_segments=1,
    )

    assert len(chunks) >= 2

    first_chunk_last_segment = chunks[0].segment_ids[-1]
    second_chunk_first_segment = chunks[1].segment_ids[0]

    assert first_chunk_last_segment == second_chunk_first_segment


def test_empty_segments_returns_empty_list():
    chunks = chunk_transcript_segments(
        segments=[],
        full_source_text="",
        max_chunk_chars=60,
        min_chunk_chars=30,
        overlap_segments=1,
    )

    assert chunks == []


def test_rejects_non_list_segments():
    with pytest.raises(TypeError, match="segments must be a list"):
        chunk_transcript_segments(
            segments="not a list",
            full_source_text="",
            max_chunk_chars=60,
            min_chunk_chars=30,
            overlap_segments=1,
        )


def test_rejects_invalid_max_chunk_chars():
    with pytest.raises(ValueError, match="max_chunk_chars must be greater than 0"):
        chunk_transcript_segments(
            segments=[],
            full_source_text="",
            max_chunk_chars=0,
            min_chunk_chars=30,
            overlap_segments=1,
        )


def test_rejects_invalid_min_chunk_chars():
    with pytest.raises(ValueError, match="min_chunk_chars must be greater than 0"):
        chunk_transcript_segments(
            segments=[],
            full_source_text="",
            max_chunk_chars=60,
            min_chunk_chars=0,
            overlap_segments=1,
        )


def test_rejects_min_chunk_chars_greater_than_max_chunk_chars():
    with pytest.raises(ValueError, match="min_chunk_chars cannot be greater than max_chunk_chars"):
        chunk_transcript_segments(
            segments=[],
            full_source_text="",
            max_chunk_chars=60,
            min_chunk_chars=100,
            overlap_segments=1,
        )


def test_rejects_negative_overlap_segments():
    with pytest.raises(ValueError, match="overlap_segments cannot be negative"):
        chunk_transcript_segments(
            segments=[],
            full_source_text="",
            max_chunk_chars=60,
            min_chunk_chars=30,
            overlap_segments=-1,
        )


def test_rejects_segment_missing_required_key():
    bad_segments = [
        {
            "segment_id": "seg_0001",
            "source_text": "Missing offsets.",
            "char_start": 0,
            "start_seconds": 0.0,
            "end_seconds": 5.0,
        }
    ]

    with pytest.raises(ValueError, match="Segment is missing required keys"):
        chunk_transcript_segments(
            segments=bad_segments,
            full_source_text="Missing offsets.",
            max_chunk_chars=60,
            min_chunk_chars=30,
            overlap_segments=1,
        )


def test_rejects_segment_missing_id():
    bad_segments = [
        {
            "source_text": "Missing segment ID.",
            "clean_text": "Missing segment ID.",
            "char_start": 0,
            "char_end": 19,
            "start_seconds": 0.0,
            "end_seconds": 5.0,
        }
    ]

    with pytest.raises(ValueError, match="Segment must contain either 'segment_id' or 'id'"):
        chunk_transcript_segments(
            segments=bad_segments,
            full_source_text="Missing segment ID.",
            max_chunk_chars=60,
            min_chunk_chars=30,
            overlap_segments=1,
        )


def test_rejects_invalid_offset_order():
    bad_segments = [
        {
            "segment_id": "seg_0001",
            "source_text": "Bad offsets.",
            "clean_text": "Bad offsets.",
            "char_start": 20,
            "char_end": 10,
            "start_seconds": 0.0,
            "end_seconds": 5.0,
        }
    ]

    with pytest.raises(ValueError, match="segment char_end cannot be less than char_start"):
        chunk_transcript_segments(
            segments=bad_segments,
            full_source_text="x" * 30,
            max_chunk_chars=60,
            min_chunk_chars=30,
            overlap_segments=1,
        )


def test_rejects_invalid_timestamp_order():
    bad_segments = [
        {
            "segment_id": "seg_0001",
            "source_text": "Bad timestamps.",
            "clean_text": "Bad timestamps.",
            "char_start": 0,
            "char_end": 15,
            "start_seconds": 10.0,
            "end_seconds": 5.0,
        }
    ]

    with pytest.raises(ValueError, match="segment end_seconds cannot be less than start_seconds"):
        chunk_transcript_segments(
            segments=bad_segments,
            full_source_text="Bad timestamps.",
            max_chunk_chars=60,
            min_chunk_chars=30,
            overlap_segments=1,
        )


def test_supports_id_when_segment_id_is_missing():
    segments = [
        {
            "id": "seg_alt_0001",
            "source_text": "This segment uses id instead of segment_id.",
            "clean_text": "This segment uses id instead of segment_id.",
            "char_start": 0,
            "char_end": 43,
            "start_seconds": 0.0,
            "end_seconds": 5.0,
        }
    ]

    full_source_text = "This segment uses id instead of segment_id."

    chunks = chunk_transcript_segments(
        segments=segments,
        full_source_text=full_source_text,
        max_chunk_chars=60,
        min_chunk_chars=30,
        overlap_segments=0,
    )

    assert chunks[0].segment_ids == ["seg_alt_0001"]
