import json
from pathlib import Path

from src.pipelines.run_steelman_pipeline import (
    DEFAULT_SPEAKER_PERSPECTIVE_PATH,
    run_steelman_pipeline,
)


def _minimal_argument_config(
    tmp_path: Path,
    *,
    claim_inventory_path: Path,
    argument_map_path: Path,
    speaker_output_path: Path,
) -> Path:
    cfg = tmp_path / "argument_config.json"
    cfg.write_text(
        json.dumps(
            {
                "stage": "argument_structure",
                "input_path": "data/x.json",
                "output_paths": {
                    "chunks": str(tmp_path / "chunks_stub.json"),
                    "argument_map": str(argument_map_path.resolve()),
                },
                "chunking": {},
                "anchors": {},
                "llm": {},
                "safety": {},
                "claim_inventory": {
                    "enabled": True,
                    "drop_non_verbatim_claims": True,
                    "require_embed_url": False,
                    "allowed_claim_types": [],
                    "output_path": str(claim_inventory_path.resolve()),
                    "embed_base_url": None,
                    "source_registry_path": str(tmp_path / "reg_stub.json"),
                },
                "speaker_perspective": {
                    "enabled": True,
                    "output_path": str(speaker_output_path.resolve()),
                },
            }
        ),
        encoding="utf-8",
    )
    return cfg


def test_run_steelman_pipeline_writes_json(tmp_path):
    claim_path = tmp_path / "claim_inventory.json"
    argument_path = tmp_path / "argument_map.json"
    out_path = tmp_path / "speaker_perspective.json"

    claim_path.write_text(
        json.dumps(
            {
                "claim_count": 1,
                "claims": [
                    {
                        "claim_id": "claim_001",
                        "verbatim_quote": "hello world",
                        "anchor_chunk": "chunk_001",
                        "char_offset_start": 0,
                        "char_offset_end": 11,
                        "anchor_clip": {"start": 1.0, "end": 2.0},
                        "claim_type": "empirical_technical",
                        "verification_strategy": "literature_review",
                        "embed_url": "https://www.youtube-nocookie.com/embed/X?v=1",
                    }
                ],
                "summary": {},
            }
        ),
        encoding="utf-8",
    )

    argument_path.write_text(
        json.dumps(
            {
                "stage": "argument_structure",
                "argument_map": {
                    "map_type": "heuristic_argument_map",
                    "qualifications": [],
                    "supporting_points": [],
                    "thesis_candidates": [],
                    "examples": [],
                    "summary_claims": [],
                },
            }
        ),
        encoding="utf-8",
    )

    cfg = _minimal_argument_config(
        tmp_path,
        claim_inventory_path=claim_path,
        argument_map_path=argument_path,
        speaker_output_path=out_path,
    )

    returned = run_steelman_pipeline(
        config_path=cfg,
        logs_dir=tmp_path / "runs",
    )

    assert returned == out_path
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["stage"] == "speaker_perspective"
    assert payload["enabled"] is True
    assert payload["claim_count"] == 1
    assert len(payload["narrative_blocks"]) == 1
    assert payload["narrative_blocks"][0]["verbatim_anchors"] == ["claim_001"]
    assert payload["input_paths"]["claim_inventory"] == str(claim_path)


def test_steelman_disabled_writes_empty_section(tmp_path):
    claim_path = tmp_path / "claim_inventory.json"
    argument_path = tmp_path / "argument_map.json"
    out_path = tmp_path / "speaker_perspective.json"

    claim_path.write_text(
        json.dumps({"claim_count": 0, "claims": [], "summary": {}}),
        encoding="utf-8",
    )
    argument_path.write_text(
        json.dumps(
            {
                "argument_map": {
                    "map_type": "heuristic_argument_map",
                    "qualifications": [],
                    "supporting_points": [],
                    "thesis_candidates": [],
                    "examples": [],
                    "summary_claims": [],
                },
            }
        ),
        encoding="utf-8",
    )

    cfg = tmp_path / "argument_config.json"
    cfg.write_text(
        json.dumps(
            {
                "stage": "argument_structure",
                "input_path": "data/x.json",
                "output_paths": {"argument_map": str(argument_path)},
                "chunking": {},
                "anchors": {},
                "llm": {},
                "safety": {},
                "claim_inventory": {
                    "enabled": True,
                    "drop_non_verbatim_claims": True,
                    "require_embed_url": False,
                    "allowed_claim_types": [],
                    "output_path": str(claim_path),
                    "embed_base_url": None,
                    "source_registry_path": str(tmp_path / "reg_stub.json"),
                },
                "speaker_perspective": {
                    "enabled": False,
                    "output_path": str(out_path),
                },
            }
        ),
        encoding="utf-8",
    )

    run_steelman_pipeline(config_path=cfg, logs_dir=tmp_path / "runs")

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["enabled"] is False
    assert payload["narrative_blocks"] == []


def test_default_output_matches_processed_path():
    assert DEFAULT_SPEAKER_PERSPECTIVE_PATH.name == "speaker_perspective.json"
