import pytest

from src.argument.argument_models import TranscriptChunk
from src.argument.chunk_validator import validate_chunk, validate_chunks


def make_valid_chunk() -> TranscriptChunk:
    return TranscriptChunk(
        chunk_id="chunk_0001",
        source_text="This is a valid transcript chunk.",
        clean_text="This is a valid transcript chunk.",
        char_start=0,
        char_end=33,
        start_seconds=0.0,
        end_seconds=10.0,
        segment_ids=["seg_0001", "seg_0002"],
        chunk_type="transcript_window",
    )


def test_validate_chunk_accepts_valid_chunk():
    chunk = make_valid_chunk()

    result = validate_chunk(chunk)

    assert result["chunk_id"] == "chunk_0001"
    assert result["valid"] is True
    assert result["offsets_valid"] is True
    assert result["timestamps_valid"] is True
    assert result["segment_ids_valid"] is True
    assert result["source_text_valid"] is True
    assert result["errors"] == []


def test_validate_chunk_rejects_non_chunk():
    with pytest.raises(TypeError, match="chunk must be a TranscriptChunk"):
        validate_chunk({"chunk_id": "chunk_0001"})


def test_validate_chunk_detects_invalid_offsets():
    chunk = make_valid_chunk()
    chunk.char_start = 50
    chunk.char_end = 10

    result = validate_chunk(chunk)

    assert result["valid"] is False
    assert result["offsets_valid"] is False
    assert "invalid_offsets" in result["errors"]


def test_validate_chunk_detects_invalid_timestamps():
    chunk = make_valid_chunk()
    chunk.start_seconds = 20.0
    chunk.end_seconds = 10.0

    result = validate_chunk(chunk)

    assert result["valid"] is False
    assert result["timestamps_valid"] is False
    assert "invalid_timestamps" in result["errors"]


def test_validate_chunk_detects_missing_segment_ids():
    chunk = make_valid_chunk()
    chunk.segment_ids = []

    result = validate_chunk(chunk)

    assert result["valid"] is False
    assert result["segment_ids_valid"] is False
    assert "invalid_segment_ids" in result["errors"]


def test_validate_chunk_detects_blank_segment_id():
    chunk = make_valid_chunk()
    chunk.segment_ids = ["seg_0001", "   "]

    result = validate_chunk(chunk)

    assert result["valid"] is False
    assert result["segment_ids_valid"] is False
    assert "invalid_segment_ids" in result["errors"]


def test_validate_chunk_detects_empty_source_text():
    chunk = make_valid_chunk()
    chunk.source_text = ""

    result = validate_chunk(chunk)

    assert result["valid"] is False
    assert result["source_text_valid"] is False
    assert "invalid_source_text" in result["errors"]


def test_validate_chunks_returns_metrics_for_valid_chunks():
    chunks = [
        make_valid_chunk(),
        TranscriptChunk(
            chunk_id="chunk_0002",
            source_text="Another valid chunk.",
            clean_text="Another valid chunk.",
            char_start=34,
            char_end=54,
            start_seconds=10.0,
            end_seconds=20.0,
            segment_ids=["seg_0003"],
            chunk_type="transcript_window",
        ),
    ]

    metrics = validate_chunks(chunks)

    assert metrics["chunk_count"] == 2
    assert metrics["valid_chunk_count"] == 2
    assert metrics["invalid_chunk_count"] == 0
    assert metrics["chunk_offset_validation_pass_rate"] == 1.0
    assert metrics["chunk_timestamp_validation_pass_rate"] == 1.0
    assert metrics["chunk_segment_id_validation_pass_rate"] == 1.0
    assert metrics["chunk_source_text_validation_pass_rate"] == 1.0
    assert metrics["invalid_chunks"] == []


def test_validate_chunks_returns_metrics_for_invalid_chunks():
    valid_chunk = make_valid_chunk()

    invalid_chunk = make_valid_chunk()
    invalid_chunk.chunk_id = "chunk_0002"
    invalid_chunk.char_start = 100
    invalid_chunk.char_end = 50

    metrics = validate_chunks([valid_chunk, invalid_chunk])

    assert metrics["chunk_count"] == 2
    assert metrics["valid_chunk_count"] == 1
    assert metrics["invalid_chunk_count"] == 1
    assert metrics["chunk_offset_validation_pass_rate"] == 0.5
    assert metrics["chunk_timestamp_validation_pass_rate"] == 1.0
    assert metrics["invalid_chunks"][0]["chunk_id"] == "chunk_0002"
    assert "invalid_offsets" in metrics["invalid_chunks"][0]["errors"]


def test_validate_chunks_empty_list_returns_clean_metrics():
    metrics = validate_chunks([])

    assert metrics["chunk_count"] == 0
    assert metrics["valid_chunk_count"] == 0
    assert metrics["invalid_chunk_count"] == 0
    assert metrics["chunk_offset_validation_pass_rate"] == 1.0
    assert metrics["chunk_timestamp_validation_pass_rate"] == 1.0
    assert metrics["chunk_segment_id_validation_pass_rate"] == 1.0
    assert metrics["chunk_source_text_validation_pass_rate"] == 1.0
    assert metrics["invalid_chunks"] == []


def test_validate_chunks_rejects_non_list():
    with pytest.raises(TypeError, match="chunks must be a list"):
        validate_chunks("not a list")