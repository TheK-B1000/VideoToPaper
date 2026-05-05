import json
from pathlib import Path

import pytest

from src.argument.argument_map_builder import build_argument_map
from src.argument.argument_models import TranscriptChunk
from src.core.claim_inventory_config import CANONICAL_CLAIM_TYPES
from src.pipelines.claim_inventory_pipeline import run_claim_inventory_pipeline


def _write_json(path, obj):
    path.write_text(json.dumps(obj), encoding="utf-8")


def _write_minimal_argument_config(
    path: Path,
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
    if claim_inventory is not None:
        data["claim_inventory"] = claim_inventory
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_claim_inventory_run_log_records_pipeline_metrics(tmp_path):
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
    logs_dir = tmp_path / "runs"
    config_path = tmp_path / "used_config.json"

    _write_minimal_argument_config(
        config_path,
        claim_inventory={
            "enabled": True,
            "drop_non_verbatim_claims": True,
            "require_embed_url": True,
            "allowed_claim_types": sorted(CANONICAL_CLAIM_TYPES),
            "output_path": str(output_path),
        },
    )

    _write_json(chunks_path, {"chunks": [chunk.to_dict()]})
    _write_json(
        argument_map_path,
        {"stage": "argument_structure", "argument_map": argument_map, "validation": {}},
    )

    run_claim_inventory_pipeline(
        embed_base_url="https://www.youtube-nocookie.com/embed/ABC123",
        config_path=config_path,
        argument_map_path=argument_map_path,
        chunks_path=chunks_path,
        output_path=output_path,
        logs_dir=logs_dir,
    )

    log_files = list(logs_dir.glob("*.json"))
    assert len(log_files) == 1

    run_log = json.loads(log_files[0].read_text(encoding="utf-8"))

    assert run_log["pipeline_name"] == "claim_inventory"
    assert run_log["status"] == "success"
    assert run_log["config_path"] == str(config_path)
    assert run_log["input_path"] == str(chunks_path)
    assert run_log["output_path"] == str(output_path)

    assert run_log["input_paths"] == {
        "chunks": str(chunks_path),
        "argument_map": str(argument_map_path),
    }

    metrics = run_log["metrics"]
    assert metrics["claim_inventory_enabled"] is True
    assert metrics["argument_derived_candidate_count"] == 1
    assert metrics["candidate_claim_count"] == 1
    assert metrics["accepted_claim_count"] == 1
    assert metrics["dropped_claim_count"] == 0
    assert metrics["claim_type_counts"] == {"empirical_technical": 1}
    assert metrics["verification_strategy_counts"] == {"literature_review": 1}

    assert run_log["errors"] == []


def test_claim_inventory_run_log_records_failure(tmp_path):
    logs_dir = tmp_path / "runs"
    output_path = tmp_path / "claim_inventory.json"
    missing_chunks = tmp_path / "no_chunks.json"
    argument_map_path = tmp_path / "argument_map.json"
    config_path = tmp_path / "argument_config.json"
    _write_minimal_argument_config(config_path)
    _write_json(argument_map_path, {"argument_map": {"map_type": "heuristic_argument_map"}})

    with pytest.raises(FileNotFoundError):
        run_claim_inventory_pipeline(
            embed_base_url="https://www.youtube-nocookie.com/embed/ABC123",
            config_path=config_path,
            chunks_path=missing_chunks,
            argument_map_path=argument_map_path,
            output_path=output_path,
            logs_dir=logs_dir,
        )

    log_files = list(logs_dir.glob("*.json"))
    assert len(log_files) == 1

    run_log = json.loads(log_files[0].read_text(encoding="utf-8"))

    assert run_log["pipeline_name"] == "claim_inventory"
    assert run_log["status"] == "failed"
    assert len(run_log["errors"]) == 1
    assert "message" in run_log["errors"][0]
    assert run_log["errors"][0]["message"]
