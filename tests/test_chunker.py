import pytest

from src.argument.chunker import chunk_transcript_segments


def make_segments():
    return [
        {
            "segment_id": "seg_0001",
            "source_text": "This is the first segment. ",
            "clean_text": "This is the first segment.",
            "char_start": 0,
            "char_end": 27,
            "start_seconds": 0.0,
            "end_seconds": 5.0,
        },
        {
            "segment_id": "seg_0002",
            "source_text": "This is the second segment. ",
            "clean_text": "This is the second segment.",
            "char_start": 27,
            "char_end": 55,
            "start_seconds": 5.0,
            "end_seconds": 10.0,
        },
        {
            "segment_id": "seg_0003",
            "source_text": "This is the third segment. ",
            "clean_text": "This is the third segment.",
            "char_start": 55,
            "char_end": 82,
            "start_seconds": 10.0,
            "end_seconds": 15.0,
        },
        {
            "segment_id": "seg_0004",
            "source_text": "This is the fourth segment. ",
            "clean_text": "This is the fourth segment.",
            "char_start": 82,
            "char_end": 110,
            "start_seconds": 15.0,
            "end_seconds": 20.0,
        },
    ]


def test_chunk_transcript_segments_returns_chunks():
    segments = make_segments()

    chunks = chunk_transcript_segments(
        segments=segments,
        max_chunk_chars=60,
        min_chunk_chars=30,
        overlap_segments=1,
    )

    assert len(chunks) > 0
    assert chunks[0].chunk_id == "chunk_0001"
    assert chunks[0].chunk_type == "transcript_window"


def test_chunk_preserves_source_text():
    segments = make_segments()

    chunks = chunk_transcript_segments(
        segments=segments,
        max_chunk_chars=60,
        min_chunk_chars=30,
        overlap_segments=0,
    )

    first_chunk = chunks[0]

    expected_source_text = (
        segments[0]["source_text"]
        + segments[1]["source_text"]
    )

    assert first_chunk.source_text == expected_source_text


def test_chunk_preserves_offsets():
    segments = make_segments()

    chunks = chunk_transcript_segments(
        segments=segments,
        max_chunk_chars=60,
        min_chunk_chars=30,
        overlap_segments=0,
    )

    first_chunk = chunks[0]

    assert first_chunk.char_start == segments[0]["char_start"]
    assert first_chunk.char_end == segments[1]["char_end"]


def test_chunk_preserves_timestamps():
    segments = make_segments()

    chunks = chunk_transcript_segments(
        segments=segments,
        max_chunk_chars=60,
        min_chunk_chars=30,
        overlap_segments=0,
    )

    first_chunk = chunks[0]

    assert first_chunk.start_seconds == segments[0]["start_seconds"]
    assert first_chunk.end_seconds == segments[1]["end_seconds"]


def test_chunk_preserves_segment_ids():
    segments = make_segments()

    chunks = chunk_transcript_segments(
        segments=segments,
        max_chunk_chars=60,
        min_chunk_chars=30,
        overlap_segments=0,
    )

    first_chunk = chunks[0]

    assert first_chunk.segment_ids == ["seg_0001", "seg_0002"]


def test_chunk_uses_segment_overlap():
    segments = make_segments()

    chunks = chunk_transcript_segments(
        segments=segments,
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
        max_chunk_chars=60,
        min_chunk_chars=30,
        overlap_segments=1,
    )

    assert chunks == []


def test_rejects_non_list_segments():
    with pytest.raises(TypeError, match="segments must be a list"):
        chunk_transcript_segments(
            segments="not a list",
            max_chunk_chars=60,
            min_chunk_chars=30,
            overlap_segments=1,
        )


def test_rejects_invalid_max_chunk_chars():
    with pytest.raises(ValueError, match="max_chunk_chars must be greater than 0"):
        chunk_transcript_segments(
            segments=[],
            max_chunk_chars=0,
            min_chunk_chars=30,
            overlap_segments=1,
        )


def test_rejects_invalid_min_chunk_chars():
    with pytest.raises(ValueError, match="min_chunk_chars must be greater than 0"):
        chunk_transcript_segments(
            segments=[],
            max_chunk_chars=60,
            min_chunk_chars=0,
            overlap_segments=1,
        )


def test_rejects_min_chunk_chars_greater_than_max_chunk_chars():
    with pytest.raises(ValueError, match="min_chunk_chars cannot be greater than max_chunk_chars"):
        chunk_transcript_segments(
            segments=[],
            max_chunk_chars=60,
            min_chunk_chars=100,
            overlap_segments=1,
        )


def test_rejects_negative_overlap_segments():
    with pytest.raises(ValueError, match="overlap_segments cannot be negative"):
        chunk_transcript_segments(
            segments=[],
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

    chunks = chunk_transcript_segments(
        segments=segments,
        max_chunk_chars=60,
        min_chunk_chars=30,
        overlap_segments=0,
    )

    assert chunks[0].segment_ids == ["seg_alt_0001"]