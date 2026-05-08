import json
from pathlib import Path

import pytest

from src.argument.argument_map_builder import build_argument_map
from src.argument.argument_models import TranscriptChunk
from src.core.claim_inventory_config import CANONICAL_CLAIM_TYPES
from src.pipelines.claim_inventory_pipeline import run_claim_inventory_pipeline


def _registry_stub_path(tmp_path: Path) -> str:
    return str(tmp_path / "registry_stub.json")


def _ci(core: dict, tmp_path: Path) -> dict:
    merged = dict(core)
    merged.setdefault("embed_base_url", None)
    merged.setdefault("source_registry_path", _registry_stub_path(tmp_path))
    return merged


def _write_json(path: Path, obj) -> None:
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


def _fixture_outputs(tmp_path: Path):
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
    _write_json(chunks_path, {"chunks": [chunk.to_dict()]})
    _write_json(
        argument_map_path,
        {"stage": "argument_structure", "argument_map": argument_map, "validation": {}},
    )
    return chunks_path, argument_map_path


def test_claim_inventory_output_path_from_config_overrides_kwarg(tmp_path):
    chunks_path, argument_map_path = _fixture_outputs(tmp_path)
    out_from_config = tmp_path / "inventory_from_config.json"
    out_from_kwarg = tmp_path / "inventory_from_kwarg.json"
    config_path = tmp_path / "argument_config.json"

    _write_minimal_argument_config(
        config_path,
        claim_inventory=_ci(
            {
                "enabled": True,
                "drop_non_verbatim_claims": True,
                "require_embed_url": True,
                "allowed_claim_types": sorted(CANONICAL_CLAIM_TYPES),
                "output_path": str(out_from_config),
            },
            tmp_path,
        ),
    )

    returned = run_claim_inventory_pipeline(
        embed_base_url="https://www.youtube-nocookie.com/embed/ABC123",
        config_path=config_path,
        argument_map_path=argument_map_path,
        chunks_path=chunks_path,
        output_path=out_from_kwarg,
        logs_dir=tmp_path / "runs",
    )

    assert returned == out_from_config
    assert out_from_config.exists()
    assert not out_from_kwarg.exists()


def test_claim_inventory_enabled_false_writes_empty_outputs(tmp_path):
    chunks_path, argument_map_path = _fixture_outputs(tmp_path)
    output_path = tmp_path / "claim_inventory.json"
    config_path = tmp_path / "argument_config.json"

    _write_minimal_argument_config(
        config_path,
        claim_inventory=_ci(
            {
                "enabled": False,
                "drop_non_verbatim_claims": True,
                "require_embed_url": True,
                "allowed_claim_types": sorted(CANONICAL_CLAIM_TYPES),
                "output_path": str(output_path),
            },
            tmp_path,
        ),
    )

    returned = run_claim_inventory_pipeline(
        embed_base_url=None,
        config_path=config_path,
        argument_map_path=argument_map_path,
        chunks_path=chunks_path,
        logs_dir=tmp_path / "runs",
    )

    assert returned == output_path
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["claim_count"] == 0
    assert payload["claims"] == []


def test_empty_allowed_claim_types_allows_all_canonical_claim_types(tmp_path):
    chunks_path, argument_map_path = _fixture_outputs(tmp_path)
    output_path = tmp_path / "claim_inventory.json"
    config_path = tmp_path / "argument_config.json"

    _write_minimal_argument_config(
        config_path,
        claim_inventory=_ci(
            {
                "enabled": True,
                "drop_non_verbatim_claims": True,
                "require_embed_url": True,
                "allowed_claim_types": [],
                "output_path": str(output_path),
            },
            tmp_path,
        ),
    )

    returned = run_claim_inventory_pipeline(
        embed_base_url="https://www.youtube-nocookie.com/embed/ABC123",
        config_path=config_path,
        argument_map_path=argument_map_path,
        chunks_path=chunks_path,
        logs_dir=tmp_path / "runs",
    )

    assert returned == output_path
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["claim_count"] == 1

    log_files = list((tmp_path / "runs").glob("*.json"))
    assert len(log_files) == 1
    run_log = json.loads(log_files[0].read_text(encoding="utf-8"))
    assert run_log["metrics"]["argument_derived_candidate_count"] == 1
    assert run_log["metrics"]["candidate_claim_count"] == 1


def test_allowed_claim_types_subset_keeps_only_listed_empirical_types(tmp_path):
    chunks_path, argument_map_path = _fixture_outputs(tmp_path)
    output_path = tmp_path / "claim_inventory.json"
    config_path = tmp_path / "argument_config.json"

    _write_minimal_argument_config(
        config_path,
        claim_inventory=_ci(
            {
                "enabled": True,
                "drop_non_verbatim_claims": True,
                "require_embed_url": True,
                "allowed_claim_types": ["empirical_technical", "empirical_scientific"],
                "output_path": str(output_path),
            },
            tmp_path,
        ),
    )

    run_claim_inventory_pipeline(
        embed_base_url="https://www.youtube-nocookie.com/embed/ABC123",
        config_path=config_path,
        argument_map_path=argument_map_path,
        chunks_path=chunks_path,
        logs_dir=tmp_path / "runs",
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["claim_count"] == 1
    assert payload["claims"][0]["claim_type"] == "empirical_technical"


def test_allowed_claim_types_excludes_non_matching_types(tmp_path):
    chunks_path, argument_map_path = _fixture_outputs(tmp_path)
    output_path = tmp_path / "claim_inventory.json"
    config_path = tmp_path / "argument_config.json"

    _write_minimal_argument_config(
        config_path,
        claim_inventory=_ci(
            {
                "enabled": True,
                "drop_non_verbatim_claims": True,
                "require_embed_url": True,
                "allowed_claim_types": ["interpretive"],
                "output_path": str(output_path),
            },
            tmp_path,
        ),
    )

    run_claim_inventory_pipeline(
        embed_base_url="https://www.youtube-nocookie.com/embed/ABC123",
        config_path=config_path,
        argument_map_path=argument_map_path,
        chunks_path=chunks_path,
        logs_dir=tmp_path / "runs",
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["claim_count"] == 0


def test_require_embed_url_enforces_nonempty_embed_base(tmp_path):
    chunks_path, argument_map_path = _fixture_outputs(tmp_path)
    output_path = tmp_path / "claim_inventory.json"
    config_path = tmp_path / "argument_config.json"

    _write_minimal_argument_config(
        config_path,
        claim_inventory=_ci(
            {
                "enabled": True,
                "drop_non_verbatim_claims": True,
                "require_embed_url": True,
                "allowed_claim_types": sorted(CANONICAL_CLAIM_TYPES),
                "output_path": str(output_path),
            },
            tmp_path,
        ),
    )

    with pytest.raises(ValueError, match="Could not resolve embed_base_url"):
        run_claim_inventory_pipeline(
            embed_base_url=None,
            config_path=config_path,
            argument_map_path=argument_map_path,
            chunks_path=chunks_path,
            logs_dir=tmp_path / "runs",
        )


def test_require_embed_url_false_allows_missing_embed_base(tmp_path):
    chunks_path, argument_map_path = _fixture_outputs(tmp_path)
    output_path = tmp_path / "claim_inventory.json"
    config_path = tmp_path / "argument_config.json"

    _write_minimal_argument_config(
        config_path,
        claim_inventory=_ci(
            {
                "enabled": True,
                "drop_non_verbatim_claims": True,
                "require_embed_url": False,
                "allowed_claim_types": sorted(CANONICAL_CLAIM_TYPES),
                "output_path": str(output_path),
            },
            tmp_path,
        ),
    )

    run_claim_inventory_pipeline(
        embed_base_url=None,
        config_path=config_path,
        argument_map_path=argument_map_path,
        chunks_path=chunks_path,
        logs_dir=tmp_path / "runs",
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["claim_count"] == 1
    assert "unknown" in payload["claims"][0]["embed_url"]
    log_files = list((tmp_path / "runs").glob("*.json"))
    run_log = json.loads(log_files[0].read_text(encoding="utf-8"))
    assert run_log["metrics"]["embed_base_url_source"] == "fallback_unknown"


def test_embed_resolution_prefers_registry_over_config_and_manual(tmp_path):
    chunks_path, argument_map_path = _fixture_outputs(tmp_path)
    output_path = tmp_path / "claim_inventory.json"
    config_path = tmp_path / "argument_config.json"

    registry_file = tmp_path / "week1_registry.json"
    reg_url = "https://www.youtube-nocookie.com/embed/from_registry"
    cfg_url = "https://www.youtube-nocookie.com/embed/from_config"
    manual_url = "https://www.youtube-nocookie.com/embed/from_manual"
    _write_json(registry_file, {"embed_base_url": reg_url})

    _write_minimal_argument_config(
        config_path,
        claim_inventory=_ci(
            {
                "enabled": True,
                "drop_non_verbatim_claims": True,
                "require_embed_url": True,
                "allowed_claim_types": sorted(CANONICAL_CLAIM_TYPES),
                "output_path": str(output_path),
                "embed_base_url": cfg_url,
                "source_registry_path": str(registry_file),
            },
            tmp_path,
        ),
    )

    run_claim_inventory_pipeline(
        embed_base_url=manual_url,
        config_path=config_path,
        argument_map_path=argument_map_path,
        chunks_path=chunks_path,
        logs_dir=tmp_path / "runs",
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["claims"][0]["embed_url"].startswith(reg_url)

    log_files = list((tmp_path / "runs").glob("*.json"))
    run_log = json.loads(log_files[0].read_text(encoding="utf-8"))
    assert run_log["metrics"]["embed_base_url_source"] == "registry"


def test_embed_resolution_prefers_config_over_manual_when_registry_missing(tmp_path):
    chunks_path, argument_map_path = _fixture_outputs(tmp_path)
    output_path = tmp_path / "claim_inventory.json"
    config_path = tmp_path / "argument_config.json"

    cfg_url = "https://www.youtube-nocookie.com/embed/from_config"
    manual_url = "https://www.youtube-nocookie.com/embed/from_manual"

    _write_minimal_argument_config(
        config_path,
        claim_inventory=_ci(
            {
                "enabled": True,
                "drop_non_verbatim_claims": True,
                "require_embed_url": True,
                "allowed_claim_types": sorted(CANONICAL_CLAIM_TYPES),
                "output_path": str(output_path),
                "embed_base_url": cfg_url,
            },
            tmp_path,
        ),
    )

    run_claim_inventory_pipeline(
        embed_base_url=manual_url,
        config_path=config_path,
        argument_map_path=argument_map_path,
        chunks_path=chunks_path,
        logs_dir=tmp_path / "runs",
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["claims"][0]["embed_url"].startswith(cfg_url)

    log_files = list((tmp_path / "runs").glob("*.json"))
    run_log = json.loads(log_files[0].read_text(encoding="utf-8"))
    assert run_log["metrics"]["embed_base_url_source"] == "config"


def test_embed_resolution_uses_manual_when_registry_and_config_missing(tmp_path):
    chunks_path, argument_map_path = _fixture_outputs(tmp_path)
    output_path = tmp_path / "claim_inventory.json"
    config_path = tmp_path / "argument_config.json"

    manual_url = "https://www.youtube-nocookie.com/embed/from_manual"

    _write_minimal_argument_config(
        config_path,
        claim_inventory=_ci(
            {
                "enabled": True,
                "drop_non_verbatim_claims": True,
                "require_embed_url": True,
                "allowed_claim_types": sorted(CANONICAL_CLAIM_TYPES),
                "output_path": str(output_path),
                "embed_base_url": None,
            },
            tmp_path,
        ),
    )

    run_claim_inventory_pipeline(
        embed_base_url=manual_url,
        config_path=config_path,
        argument_map_path=argument_map_path,
        chunks_path=chunks_path,
        logs_dir=tmp_path / "runs",
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["claims"][0]["embed_url"].startswith(manual_url)

    log_files = list((tmp_path / "runs").glob("*.json"))
    run_log = json.loads(log_files[0].read_text(encoding="utf-8"))
    assert run_log["metrics"]["embed_base_url_source"] == "manual"


def test_embed_resolution_loads_week1_registry_without_manual_embed(tmp_path):
    chunks_path, argument_map_path = _fixture_outputs(tmp_path)
    output_path = tmp_path / "claim_inventory.json"
    config_path = tmp_path / "argument_config.json"

    registry_file = tmp_path / "source_registry.json"
    reg_url = "https://www.youtube-nocookie.com/embed/week1_registry_id"
    _write_json(registry_file, {"embed_base_url": reg_url, "video_id": "week1_registry_id"})

    _write_minimal_argument_config(
        config_path,
        claim_inventory=_ci(
            {
                "enabled": True,
                "drop_non_verbatim_claims": True,
                "require_embed_url": True,
                "allowed_claim_types": sorted(CANONICAL_CLAIM_TYPES),
                "output_path": str(output_path),
                "embed_base_url": None,
                "source_registry_path": str(registry_file),
            },
            tmp_path,
        ),
    )

    run_claim_inventory_pipeline(
        config_path=config_path,
        argument_map_path=argument_map_path,
        chunks_path=chunks_path,
        logs_dir=tmp_path / "runs",
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["claims"][0]["embed_url"].startswith(reg_url)

    log_files = list((tmp_path / "runs").glob("*.json"))
    run_log = json.loads(log_files[0].read_text(encoding="utf-8"))
    assert run_log["metrics"]["embed_base_url_source"] == "registry"
