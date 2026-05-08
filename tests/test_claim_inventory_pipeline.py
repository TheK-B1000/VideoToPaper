import json
from pathlib import Path

from src.argument.argument_map_builder import build_argument_map
from src.argument.argument_models import TranscriptChunk
from src.core.claim_inventory_config import CANONICAL_CLAIM_TYPES
from src.pipelines.claim_inventory_pipeline import (
    build_source_text_by_chunk_id,
    candidate_claims_from_argument_map,
    load_argument_map_document,
    load_chunks_payload,
    run_claim_inventory_pipeline,
)


def _write_json(path, obj):
    path.write_text(json.dumps(obj), encoding="utf-8")


def _write_minimal_argument_config(
    path: Path,
    *,
    tmp_path: Path | None = None,
    output_path: Path | None = None,
    claim_inventory: dict | None = None,
) -> Path:
    data = {
        "stage": "argument_structure",
        "input_path": "data/x.json",
        "output_paths": {},
        "chunking": {},
        "anchors": {},
        "llm": {},
        "safety": {},
    }
    if claim_inventory is None:
        assert tmp_path is not None and output_path is not None
        claim_inventory = {
            "enabled": True,
            "drop_non_verbatim_claims": True,
            "require_embed_url": True,
            "allowed_claim_types": sorted(CANONICAL_CLAIM_TYPES),
            "output_path": str(output_path),
            "embed_base_url": None,
            "source_registry_path": str(tmp_path / "registry_stub.json"),
        }
    data["claim_inventory"] = claim_inventory
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_run_claim_inventory_pipeline_writes_claim_inventory_and_returns_path(tmp_path):
    chunk = TranscriptChunk(
        chunk_id="chunk_0001",
        source_text="The key point is that retrieval can fail silently.",
        clean_text="The key point is that retrieval can fail silently.",
        char_start=0,
        char_end=54,
        start_seconds=10.0,
        end_seconds=20.0,
        segment_ids=["seg_0001"],
        chunk_type="transcript_window",
    )
    anchor = {
        "anchor_id": "anchor_0001",
        "chunk_id": "chunk_0001",
        "type": "verbal_claim",
        "source_text": "The key point is",
        "char_start": 0,
        "char_end": 16,
        "start_seconds": 10.0,
        "end_seconds": 20.0,
        "confidence": "heuristic",
        "signal": "the key point is",
    }

    argument_map = build_argument_map(chunks=[chunk], anchors=[anchor])

    chunks_path = tmp_path / "chunks.json"
    argument_map_path = tmp_path / "argument_map.json"
    output_path = tmp_path / "claim_inventory.json"
    config_path = tmp_path / "argument_config.json"
    _write_minimal_argument_config(
        config_path,
        tmp_path=tmp_path,
        output_path=output_path,
    )

    _write_json(
        chunks_path,
        {"chunks": [chunk.to_dict()]},
    )
    _write_json(
        argument_map_path,
        {
            "stage": "argument_structure",
            "argument_map": argument_map,
            "validation": {},
        },
    )

    embed_base = "https://www.youtube-nocookie.com/embed/ABC123"

    logs_dir = tmp_path / "runs"

    returned = run_claim_inventory_pipeline(
        embed_base_url=embed_base,
        config_path=config_path,
        argument_map_path=argument_map_path,
        chunks_path=chunks_path,
        output_path=output_path,
        logs_dir=logs_dir,
    )

    assert returned == output_path
    assert output_path.exists()

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["claim_count"] == 1
    assert payload["claims"][0]["claim_id"] == "supporting_point_0001"
    assert payload["claims"][0]["verbatim_quote"] == "The key point is"
    assert payload["summary"]["has_empirical_claims"] is True


def test_candidate_claims_use_chunk_local_offsets_when_chunk_char_start_nonzero():
    chunk = TranscriptChunk(
        chunk_id="chunk_0001",
        source_text="The key point is that retrieval can fail silently.",
        clean_text="The key point is that retrieval can fail silently.",
        char_start=100,
        char_end=100 + 54,
        start_seconds=10.0,
        end_seconds=20.0,
        segment_ids=["seg_0001"],
        chunk_type="transcript_window",
    )
    anchor = {
        "anchor_id": "anchor_0001",
        "chunk_id": "chunk_0001",
        "type": "verbal_claim",
        "source_text": "The key point is",
        "char_start": 100,
        "char_end": 116,
        "start_seconds": 10.0,
        "end_seconds": 20.0,
        "confidence": "heuristic",
        "signal": "the key point is",
    }
    argument_map = build_argument_map(chunks=[chunk], anchors=[anchor])
    chunks_by_id = {chunk.chunk_id: chunk.to_dict()}

    candidates = candidate_claims_from_argument_map(argument_map, chunks_by_id)

    assert len(candidates) == 1
    assert candidates[0]["char_offset_start"] == 0
    assert candidates[0]["char_offset_end"] == 16


def test_build_source_text_by_chunk_id_maps_chunk_ids():
    chunks = [
        {"chunk_id": "chunk_0001", "source_text": "alpha"},
        {"chunk_id": "chunk_0002", "source_text": "beta"},
    ]
    assert build_source_text_by_chunk_id(chunks) == {
        "chunk_0001": "alpha",
        "chunk_0002": "beta",
    }


def test_load_argument_map_document_accepts_bare_heuristic_map(tmp_path):
    inner = {"map_type": "heuristic_argument_map", "supporting_points": []}
    path = tmp_path / "bare.json"
    _write_json(path, inner)
    assert load_argument_map_document(path) == inner


def test_load_chunks_payload_reads_chunks_list(tmp_path):
    path = tmp_path / "chunks.json"
    _write_json(path, {"chunks": [{"chunk_id": "chunk_0001"}]})
    assert load_chunks_payload(path) == [{"chunk_id": "chunk_0001"}]
