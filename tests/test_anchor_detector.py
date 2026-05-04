import pytest

from src.argument.anchor_detector import detect_anchor_moments
from src.argument.argument_models import TranscriptChunk


def make_chunk(
    chunk_id: str = "chunk_0001",
    source_text: str = "The key point is that transcript evidence needs anchors.",
    char_start: int = 0,
    char_end: int | None = None,
) -> TranscriptChunk:
    if char_end is None:
        char_end = char_start + len(source_text)

    return TranscriptChunk(
        chunk_id=chunk_id,
        source_text=source_text,
        clean_text=source_text.strip(),
        char_start=char_start,
        char_end=char_end,
        start_seconds=10.0,
        end_seconds=20.0,
        segment_ids=["seg_0001"],
        chunk_type="transcript_window",
    )


def test_detect_anchor_moments_finds_verbal_claim():
    chunk = make_chunk(
        source_text="The key point is that reinforcement learning needs careful evaluation.",
        char_start=100,
    )

    anchors = detect_anchor_moments([chunk])

    assert len(anchors) == 1
    assert anchors[0]["anchor_id"] == "anchor_0001"
    assert anchors[0]["chunk_id"] == "chunk_0001"
    assert anchors[0]["type"] == "verbal_claim"
    assert anchors[0]["source_text"] == "The key point is"
    assert anchors[0]["char_start"] == 100
    assert anchors[0]["char_end"] == 116
    assert anchors[0]["start_seconds"] == 10.0
    assert anchors[0]["end_seconds"] == 20.0
    assert anchors[0]["confidence"] == "heuristic"
    assert anchors[0]["signal"] == "the key point is"


def test_detect_anchor_moments_finds_example():
    chunk = make_chunk(
        source_text="For example, a bad chunk can split the speaker's qualification.",
        char_start=50,
    )

    anchors = detect_anchor_moments([chunk])

    assert len(anchors) == 1
    assert anchors[0]["type"] == "example"
    assert anchors[0]["source_text"] == "For example"
    assert anchors[0]["char_start"] == 50


def test_detect_anchor_moments_finds_qualification():
    chunk = make_chunk(
        source_text="However, this claim depends on the context.",
        char_start=25,
    )

    anchors = detect_anchor_moments([chunk])

    assert len(anchors) == 1
    assert anchors[0]["type"] == "qualification"
    assert anchors[0]["source_text"] == "However"


def test_detect_anchor_moments_finds_summary_claim():
    chunk = make_chunk(
        source_text="In summary, the system needs audit trails.",
        char_start=10,
    )

    anchors = detect_anchor_moments([chunk])

    assert len(anchors) == 1
    assert anchors[0]["type"] == "summary_claim"
    assert anchors[0]["source_text"] == "In summary"


def test_detect_anchor_moments_respects_allowed_types():
    chunk = make_chunk(
        source_text="For example, this matters because bad retrieval can fail silently.",
        char_start=0,
    )

    anchors = detect_anchor_moments(
        chunks=[chunk],
        allowed_types=["example"],
    )

    assert len(anchors) == 1
    assert anchors[0]["type"] == "example"


def test_detect_anchor_moments_returns_empty_when_no_patterns_match():
    chunk = make_chunk(
        source_text="The transcript continues with normal background context.",
        char_start=0,
    )

    anchors = detect_anchor_moments([chunk])

    assert anchors == []


def test_detect_anchor_moments_is_case_insensitive():
    chunk = make_chunk(
        source_text="THE KEY POINT IS that case should not matter.",
        char_start=0,
    )

    anchors = detect_anchor_moments([chunk])

    assert len(anchors) == 1
    assert anchors[0]["source_text"] == "THE KEY POINT IS"


def test_detect_anchor_moments_finds_multiple_anchors_in_one_chunk():
    chunk = make_chunk(
        source_text=(
            "The key point is that citations need anchors. "
            "For example, every quote should link to a timestamp."
        ),
        char_start=0,
    )

    anchors = detect_anchor_moments([chunk])

    assert len(anchors) == 2
    assert anchors[0]["type"] == "verbal_claim"
    assert anchors[1]["type"] == "example"


def test_detect_anchor_moments_finds_anchors_across_multiple_chunks():
    chunk_1 = make_chunk(
        chunk_id="chunk_0001",
        source_text="The key point is that the first chunk matters.",
        char_start=0,
    )

    chunk_2 = make_chunk(
        chunk_id="chunk_0002",
        source_text="For example, the second chunk may contain evidence.",
        char_start=100,
    )

    anchors = detect_anchor_moments([chunk_1, chunk_2])

    assert len(anchors) == 2
    assert anchors[0]["anchor_id"] == "anchor_0001"
    assert anchors[1]["anchor_id"] == "anchor_0002"
    assert anchors[1]["chunk_id"] == "chunk_0002"
    assert anchors[1]["char_start"] == 100


def test_detect_anchor_moments_rejects_non_list_chunks():
    with pytest.raises(TypeError, match="chunks must be a list"):
        detect_anchor_moments("not a list")


def test_detect_anchor_moments_rejects_non_chunk_item():
    with pytest.raises(TypeError, match="each chunk must be a TranscriptChunk"):
        detect_anchor_moments([{"chunk_id": "chunk_0001"}])


def test_detect_anchor_moments_rejects_invalid_allowed_types():
    chunk = make_chunk()

    with pytest.raises(TypeError, match="allowed_types must be a list or None"):
        detect_anchor_moments(
            chunks=[chunk],
            allowed_types="verbal_claim",
        )


def test_detect_anchor_moments_supports_custom_patterns():
    chunk = make_chunk(
        source_text="Critical idea: this system should preserve offsets.",
        char_start=0,
    )

    anchors = detect_anchor_moments(
        chunks=[chunk],
        allowed_types=["verbal_claim"],
        patterns={
            "verbal_claim": ["critical idea:"],
        },
    )

    assert len(anchors) == 1
    assert anchors[0]["type"] == "verbal_claim"
    assert anchors[0]["source_text"] == "Critical idea:"
    assert anchors[0]["signal"] == "critical idea:"


def test_detect_anchor_moments_rejects_invalid_patterns_type():
    chunk = make_chunk()

    with pytest.raises(TypeError, match="patterns must be a dictionary"):
        detect_anchor_moments(
            chunks=[chunk],
            patterns=["the key point is"],
        )


def test_detect_anchor_moments_rejects_invalid_pattern_entry():
    chunk = make_chunk()

    with pytest.raises(TypeError, match="each pattern entry must be a list of strings"):
        detect_anchor_moments(
            chunks=[chunk],
            patterns={
                "verbal_claim": "the key point is",
            },
        )


def test_detect_anchor_moments_rejects_non_string_pattern_phrase():
    chunk = make_chunk()

    with pytest.raises(TypeError, match="anchor pattern phrases must be strings"):
        detect_anchor_moments(
            chunks=[chunk],
            patterns={
                "verbal_claim": [123],
            },
        )