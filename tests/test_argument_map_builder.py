import pytest

from src.argument.argument_map_builder import build_argument_map
from src.argument.argument_models import TranscriptChunk


def make_chunk(
    chunk_id: str = "chunk_0001",
    source_text: str = "The key point is that retrieval can fail silently.",
    char_start: int = 0,
) -> TranscriptChunk:
    return TranscriptChunk(
        chunk_id=chunk_id,
        source_text=source_text,
        clean_text=source_text.strip(),
        char_start=char_start,
        char_end=char_start + len(source_text),
        start_seconds=10.0,
        end_seconds=20.0,
        segment_ids=["seg_0001"],
        chunk_type="transcript_window",
    )


def make_anchor(
    anchor_id: str = "anchor_0001",
    chunk_id: str = "chunk_0001",
    anchor_type: str = "verbal_claim",
    source_text: str = "The key point is",
    char_start: int = 0,
    char_end: int = 16,
    start_seconds: float = 10.0,
    end_seconds: float = 20.0,
) -> dict:
    return {
        "anchor_id": anchor_id,
        "chunk_id": chunk_id,
        "type": anchor_type,
        "source_text": source_text,
        "char_start": char_start,
        "char_end": char_end,
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "confidence": "heuristic",
        "signal": source_text.lower(),
    }


def test_build_argument_map_returns_basic_structure():
    chunks = [make_chunk()]
    anchors = [make_anchor()]

    argument_map = build_argument_map(chunks=chunks, anchors=anchors)

    assert argument_map["map_type"] == "heuristic_argument_map"
    assert argument_map["chunk_count"] == 1
    assert argument_map["anchor_count"] == 1
    assert "thesis_candidates" in argument_map
    assert "supporting_points" in argument_map
    assert "qualifications" in argument_map
    assert "examples" in argument_map
    assert "summary_claims" in argument_map


def test_build_argument_map_maps_verbal_claim_to_supporting_point():
    chunks = [make_chunk()]
    anchors = [
        make_anchor(
            anchor_id="anchor_0001",
            anchor_type="verbal_claim",
            source_text="The key point is",
        )
    ]

    argument_map = build_argument_map(chunks=chunks, anchors=anchors)

    assert len(argument_map["supporting_points"]) == 1

    item = argument_map["supporting_points"][0]

    assert item["item_id"] == "supporting_point_0001"
    assert item["item_type"] == "supporting_point"
    assert item["anchor_id"] == "anchor_0001"
    assert item["chunk_id"] == "chunk_0001"
    assert item["source_text"] == "The key point is"
    assert item["context_text"] == chunks[0].source_text
    assert item["confidence"] == "heuristic"


def test_build_argument_map_maps_definition_to_supporting_point():
    chunks = [make_chunk()]
    anchors = [
        make_anchor(
            anchor_id="anchor_0001",
            anchor_type="definition",
            source_text="when I say",
        )
    ]

    argument_map = build_argument_map(chunks=chunks, anchors=anchors)

    assert len(argument_map["supporting_points"]) == 1
    assert argument_map["supporting_points"][0]["item_type"] == "definition"


def test_build_argument_map_maps_qualification():
    chunks = [make_chunk()]
    anchors = [
        make_anchor(
            anchor_id="anchor_0001",
            anchor_type="qualification",
            source_text="however",
        )
    ]

    argument_map = build_argument_map(chunks=chunks, anchors=anchors)

    assert len(argument_map["qualifications"]) == 1
    assert argument_map["qualifications"][0]["item_type"] == "qualification"
    assert argument_map["qualifications"][0]["anchor_id"] == "anchor_0001"


def test_build_argument_map_maps_example():
    chunks = [make_chunk()]
    anchors = [
        make_anchor(
            anchor_id="anchor_0001",
            anchor_type="example",
            source_text="for example",
        )
    ]

    argument_map = build_argument_map(chunks=chunks, anchors=anchors)

    assert len(argument_map["examples"]) == 1
    assert argument_map["examples"][0]["item_type"] == "example"


def test_build_argument_map_maps_summary_claim_to_summary_and_thesis_candidate():
    chunks = [make_chunk()]
    anchors = [
        make_anchor(
            anchor_id="anchor_0001",
            anchor_type="summary_claim",
            source_text="in summary",
        )
    ]

    argument_map = build_argument_map(chunks=chunks, anchors=anchors)

    assert len(argument_map["summary_claims"]) == 1
    assert len(argument_map["thesis_candidates"]) == 1

    summary_item = argument_map["summary_claims"][0]
    thesis_item = argument_map["thesis_candidates"][0]

    assert summary_item["item_type"] == "summary_claim"
    assert thesis_item["item_type"] == "summary_claim"
    assert thesis_item["anchor_id"] == "anchor_0001"


def test_build_argument_map_ignores_unknown_anchor_type():
    chunks = [make_chunk()]
    anchors = [
        make_anchor(
            anchor_id="anchor_0001",
            anchor_type="unknown_type",
            source_text="mysterious signal",
        )
    ]

    argument_map = build_argument_map(chunks=chunks, anchors=anchors)

    assert argument_map["anchor_count"] == 1
    assert argument_map["supporting_points"] == []
    assert argument_map["qualifications"] == []
    assert argument_map["examples"] == []
    assert argument_map["summary_claims"] == []
    assert argument_map["thesis_candidates"] == []


def test_build_argument_map_handles_empty_anchors():
    chunks = [make_chunk()]
    anchors = []

    argument_map = build_argument_map(chunks=chunks, anchors=anchors)

    assert argument_map["chunk_count"] == 1
    assert argument_map["anchor_count"] == 0
    assert argument_map["supporting_points"] == []
    assert argument_map["qualifications"] == []
    assert argument_map["examples"] == []
    assert argument_map["summary_claims"] == []
    assert argument_map["thesis_candidates"] == []


def test_build_argument_map_handles_missing_chunk_reference_with_empty_context():
    chunks = [make_chunk(chunk_id="chunk_0001")]
    anchors = [
        make_anchor(
            anchor_id="anchor_0001",
            chunk_id="chunk_missing",
            anchor_type="verbal_claim",
            source_text="the key point is",
        )
    ]

    argument_map = build_argument_map(chunks=chunks, anchors=anchors)

    item = argument_map["supporting_points"][0]

    assert item["chunk_id"] == "chunk_missing"
    assert item["context_text"] == ""


def test_build_argument_map_rejects_non_list_chunks():
    with pytest.raises(TypeError, match="chunks must be a list"):
        build_argument_map(
            chunks="not chunks",
            anchors=[],
        )


def test_build_argument_map_rejects_non_list_anchors():
    with pytest.raises(TypeError, match="anchors must be a list"):
        build_argument_map(
            chunks=[],
            anchors="not anchors",
        )


def test_build_argument_map_rejects_non_chunk_item():
    with pytest.raises(TypeError, match="each chunk must be a TranscriptChunk"):
        build_argument_map(
            chunks=[{"chunk_id": "chunk_0001"}],
            anchors=[],
        )


def test_build_argument_map_rejects_non_dict_anchor():
    chunks = [make_chunk()]

    with pytest.raises(TypeError, match="each anchor must be a dictionary"):
        build_argument_map(
            chunks=chunks,
            anchors=["not an anchor"],
        )


def test_build_argument_item_preserves_offsets_and_timing():
    chunks = [make_chunk()]
    anchors = [
        make_anchor(
            anchor_id="anchor_0007",
            anchor_type="verbal_claim",
            source_text="this matters because",
            char_start=25,
            char_end=45,
            start_seconds=12.5,
            end_seconds=18.0,
        )
    ]

    argument_map = build_argument_map(chunks=chunks, anchors=anchors)
    item = argument_map["supporting_points"][0]

    assert item["item_id"] == "supporting_point_0007"
    assert item["char_start"] == 25
    assert item["char_end"] == 45
    assert item["start_seconds"] == 12.5
    assert item["end_seconds"] == 18.0