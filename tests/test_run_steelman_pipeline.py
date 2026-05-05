import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.pipelines.run_steelman_pipeline import (
    DEFAULT_SPEAKER_LLM_SETTINGS,
    DEFAULT_SPEAKER_PERSPECTIVE_PATH,
    _load_claim_inventory_claims,
    _speaker_perspective_settings,
    run_steelman_pipeline,
)


def test_speaker_perspective_settings_include_guarded_llm_defaults():
    settings = _speaker_perspective_settings({})

    assert settings["enabled"] is True
    assert settings["use_llm"] is False
    assert settings["output_path"] == str(DEFAULT_SPEAKER_PERSPECTIVE_PATH)
    assert settings["llm"] == {
        "model": "gpt-4o-mini",
        "max_output_tokens": 900,
        "max_claims_per_call": 12,
        "fallback_on_guard_rejection": True,
    }


def test_speaker_perspective_settings_accepts_valid_config():
    config = {
        "speaker_perspective": {
            "enabled": False,
            "output_path": "data/custom/speaker_perspective.json",
        }
    }

    settings = _speaker_perspective_settings(config)

    assert settings == {
        "enabled": False,
        "use_llm": False,
        "output_path": "data/custom/speaker_perspective.json",
        "llm": DEFAULT_SPEAKER_LLM_SETTINGS,
    }


def test_speaker_perspective_settings_accepts_guarded_llm_config():
    config = {
        "speaker_perspective": {
            "enabled": True,
            "use_llm": True,
            "output_path": "data/custom/speaker_perspective.json",
            "llm": {
                "model": "gpt-4o-mini",
                "max_output_tokens": 500,
                "max_claims_per_call": 6,
                "fallback_on_guard_rejection": True,
            },
        }
    }

    settings = _speaker_perspective_settings(config)

    assert settings["enabled"] is True
    assert settings["use_llm"] is True
    assert settings["output_path"] == "data/custom/speaker_perspective.json"
    assert settings["llm"] == {
        "model": "gpt-4o-mini",
        "max_output_tokens": 500,
        "max_claims_per_call": 6,
        "fallback_on_guard_rejection": True,
    }


def test_speaker_perspective_settings_rejects_non_boolean_enabled():
    config = {
        "speaker_perspective": {
            "enabled": "yes",
            "output_path": "data/custom/speaker_perspective.json",
        }
    }

    with pytest.raises(ValueError, match="speaker_perspective.enabled"):
        _speaker_perspective_settings(config)


def test_speaker_perspective_settings_rejects_empty_output_path():
    config = {
        "speaker_perspective": {
            "enabled": True,
            "output_path": "   ",
        }
    }

    with pytest.raises(ValueError, match="speaker_perspective.output_path"):
        _speaker_perspective_settings(config)


def test_speaker_perspective_settings_rejects_unknown_keys():
    config = {
        "speaker_perspective": {
            "enabled": True,
            "output_path": "data/custom/speaker_perspective.json",
            "mystery_box": True,
        }
    }

    with pytest.raises(ValueError, match="speaker_perspective unknown keys"):
        _speaker_perspective_settings(config)


def test_speaker_perspective_settings_rejects_non_boolean_use_llm():
    config = {
        "speaker_perspective": {
            "use_llm": "yes",
        }
    }

    with pytest.raises(ValueError, match="speaker_perspective.use_llm"):
        _speaker_perspective_settings(config)


def test_speaker_perspective_settings_rejects_invalid_llm_object():
    config = {
        "speaker_perspective": {
            "llm": "not an object",
        }
    }

    with pytest.raises(ValueError, match="speaker_perspective.llm must be an object"):
        _speaker_perspective_settings(config)


def test_speaker_perspective_settings_rejects_unknown_llm_keys():
    config = {
        "speaker_perspective": {
            "llm": {
                "model": "gpt-4o-mini",
                "temperature": 1.2,
            }
        }
    }

    with pytest.raises(ValueError, match="speaker_perspective.llm unknown keys"):
        _speaker_perspective_settings(config)


def test_speaker_perspective_settings_rejects_empty_llm_model():
    config = {
        "speaker_perspective": {
            "llm": {
                "model": "   ",
            }
        }
    }

    with pytest.raises(ValueError, match="speaker_perspective.llm.model"):
        _speaker_perspective_settings(config)


def test_speaker_perspective_settings_rejects_non_positive_max_output_tokens():
    config = {
        "speaker_perspective": {
            "llm": {
                "max_output_tokens": 0,
            }
        }
    }

    with pytest.raises(ValueError, match="max_output_tokens"):
        _speaker_perspective_settings(config)


def test_speaker_perspective_settings_rejects_non_positive_max_claims_per_call():
    config = {
        "speaker_perspective": {
            "llm": {
                "max_claims_per_call": 0,
            }
        }
    }

    with pytest.raises(ValueError, match="max_claims_per_call"):
        _speaker_perspective_settings(config)


def test_speaker_perspective_settings_rejects_non_boolean_fallback_flag():
    config = {
        "speaker_perspective": {
            "llm": {
                "fallback_on_guard_rejection": "true",
            }
        }
    }

    with pytest.raises(ValueError, match="fallback_on_guard_rejection"):
        _speaker_perspective_settings(config)


def test_load_claim_inventory_claims_reads_claims_list(tmp_path):
    claim_inventory_path = tmp_path / "claim_inventory.json"
    claim_inventory_path.write_text(
        json.dumps(
            {
                "claims": [
                    {
                        "claim_id": "claim_001",
                        "verbatim_quote": "This is a test claim.",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    claims = _load_claim_inventory_claims(claim_inventory_path)

    assert claims == [
        {
            "claim_id": "claim_001",
            "verbatim_quote": "This is a test claim.",
        }
    ]


def test_load_claim_inventory_claims_raises_for_missing_file(tmp_path):
    missing_path = tmp_path / "missing_claim_inventory.json"

    with pytest.raises(FileNotFoundError, match="claim inventory not found"):
        _load_claim_inventory_claims(missing_path)


def test_load_claim_inventory_claims_raises_when_claims_missing(tmp_path):
    claim_inventory_path = tmp_path / "claim_inventory.json"
    claim_inventory_path.write_text(
        json.dumps({"not_claims": []}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="must contain a list field 'claims'"):
        _load_claim_inventory_claims(claim_inventory_path)


def test_load_claim_inventory_claims_raises_when_claims_not_list(tmp_path):
    claim_inventory_path = tmp_path / "claim_inventory.json"
    claim_inventory_path.write_text(
        json.dumps({"claims": "not a list"}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="must contain a list field 'claims'"):
        _load_claim_inventory_claims(claim_inventory_path)


def _minimal_argument_config(
    tmp_path: Path,
    *,
    claim_inventory_path: Path,
    argument_map_path: Path,
    speaker_output_path: Path,
    speaker_perspective: dict | None = None,
) -> Path:
    cfg = tmp_path / "argument_config.json"
    sp = speaker_perspective or {
        "enabled": True,
        "output_path": str(speaker_output_path.resolve()),
    }
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
                "speaker_perspective": sp,
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
    assert payload["steelman_llm"] == {
        "use_llm": False,
        "llm_requested": False,
        "llm_executed": False,
    }
    assert payload["claim_count"] == 1
    assert len(payload["narrative_blocks"]) == 1
    assert payload["narrative_blocks"][0]["verbatim_anchors"] == ["claim_001"]
    assert payload["input_paths"]["claim_inventory"] == str(claim_path)

    run_log = json.loads(
        list((tmp_path / "runs").glob("*.json"))[0].read_text(encoding="utf-8")
    )
    m = run_log["metrics"]
    assert m["speaker_perspective_use_llm"] is False
    assert m["speaker_perspective_llm_requested"] is False
    assert m["speaker_perspective_llm_executed"] is False
    assert m["llm_mode_attempted"] is False
    assert m["llm_mode_used"] is False
    assert m["fallback_used"] is False
    assert m["fallback_reason"] == ""


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
    assert payload["steelman_llm"]["llm_requested"] is False
    assert payload["steelman_llm"]["llm_executed"] is False
    assert payload["narrative_blocks"] == []


def test_run_steelman_pipeline_use_llm_true_falls_back_without_llm_call(tmp_path):
    claim_inventory_path = tmp_path / "claim_inventory.json"
    argument_map_path = tmp_path / "argument_map.json"
    output_path = tmp_path / "speaker_perspective.json"
    logs_dir = tmp_path / "logs"

    cfg = _minimal_argument_config(
        tmp_path,
        claim_inventory_path=claim_inventory_path,
        argument_map_path=argument_map_path,
        speaker_output_path=output_path,
        speaker_perspective={
            "enabled": True,
            "use_llm": True,
            "output_path": str(output_path),
            "llm": {
                "model": "gpt-4o-mini",
                "max_output_tokens": 500,
                "max_claims_per_call": 6,
                "fallback_on_guard_rejection": True,
            },
        },
    )

    argument_map_path.write_text(
        json.dumps(
            {
                "argument_map": {
                    "thesis": "The speaker argues that multi-agent learning is unstable.",
                    "qualifications": [],
                    "supporting_points": [
                        {
                            "claim": "Agents change the environment while learning.",
                            "qualifications": [
                                "some methods reduce this instability",
                            ],
                            "anchor_moments": [
                                {
                                    "type": "verbal_claim",
                                    "start": 12.0,
                                    "end": 18.0,
                                }
                            ],
                        }
                    ],
                    "thesis_candidates": [],
                    "examples": [],
                    "summary_claims": [],
                },
            }
        ),
        encoding="utf-8",
    )

    claim_inventory_path.write_text(
        json.dumps(
            {
                "claims": [
                    {
                        "claim_id": "claim_001",
                        "verbatim_quote": "agents change the environment while learning",
                        "anchor_chunk": "chunk_001",
                        "char_offset_start": 0,
                        "char_offset_end": 43,
                        "anchor_clip": {
                            "start": 12.0,
                            "end": 18.0,
                        },
                        "claim_type": "empirical_technical",
                        "verification_strategy": "literature_review",
                        "embed_url": (
                            "https://www.youtube-nocookie.com/embed/ABC123"
                            "?start=12&end=18"
                        ),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    def boom(**kwargs):
        raise AssertionError("safe_llm_call must not run in placeholder mode")

    with patch("src.ops.llm_client.safe_llm_call", side_effect=boom):
        written = run_steelman_pipeline(
            config_path=cfg,
            logs_dir=logs_dir,
        )

    assert written == output_path
    assert output_path.exists()

    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["stage"] == "speaker_perspective"
    assert payload["enabled"] is True
    assert payload["claim_count"] == 1
    assert payload["self_recognition_check"] == "passed"
    assert payload["narrative_blocks"][0]["verbatim_anchors"] == ["claim_001"]
    assert payload["steelman_llm"] == {
        "use_llm": True,
        "llm_requested": True,
        "llm_executed": False,
    }
    assert "some methods reduce this instability" in " ".join(
        block["text"] for block in payload["narrative_blocks"]
    )

    log_files = list(logs_dir.glob("*.json"))
    assert len(log_files) == 1

    run_log = json.loads(log_files[0].read_text(encoding="utf-8"))

    assert run_log["status"] == "success"
    assert run_log["metrics"]["speaker_perspective_use_llm"] is True
    assert run_log["metrics"]["speaker_perspective_llm_requested"] is True
    assert run_log["metrics"]["speaker_perspective_llm_executed"] is False
    assert run_log["metrics"]["speaker_perspective_llm_max_output_tokens"] == 500
    assert run_log["metrics"]["speaker_perspective_llm_max_claims_per_call"] == 6
    assert run_log["metrics"]["llm_mode_attempted"] is True
    assert run_log["metrics"]["llm_mode_used"] is False
    assert run_log["metrics"]["fallback_used"] is True
    assert run_log["metrics"]["fallback_reason"] == "llm_not_implemented"


def _integration_argument_config_for_load_config(
    tmp_path: Path,
    *,
    claim_inventory_path: Path,
    argument_map_path: Path,
    output_path: Path,
    speaker_perspective: dict,
) -> Path:
    """Minimal valid ``argument_config.json`` for integration-style tests."""
    config_path = tmp_path / "argument_config.json"
    config_path.write_text(
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
                "speaker_perspective": speaker_perspective,
            }
        ),
        encoding="utf-8",
    )
    return config_path


def test_run_speaker_perspective_pipeline_use_llm_true_records_fallback_state(tmp_path):
    argument_map_path = tmp_path / "argument_map.json"
    claim_inventory_path = tmp_path / "claim_inventory.json"
    output_path = tmp_path / "speaker_perspective.json"
    logs_dir = tmp_path / "logs"

    config_path = _integration_argument_config_for_load_config(
        tmp_path,
        claim_inventory_path=claim_inventory_path,
        argument_map_path=argument_map_path,
        output_path=output_path,
        speaker_perspective={
            "enabled": True,
            "use_llm": True,
            "output_path": str(output_path),
            "llm": {
                "model": "gpt-4o-mini",
                "max_output_tokens": 500,
                "max_claims_per_call": 6,
                "fallback_on_guard_rejection": True,
            },
        },
    )

    argument_map_path.write_text(
        json.dumps(
            {
                "argument_map": {
                    "thesis": (
                        "The speaker argues that multi-agent learning is unstable."
                    ),
                    "qualifications": [],
                    "supporting_points": [
                        {
                            "claim": "Agents change the environment while learning.",
                            "qualifications": [
                                "some methods reduce this instability",
                            ],
                            "anchor_moments": [
                                {
                                    "type": "verbal_claim",
                                    "start": 12.0,
                                    "end": 18.0,
                                }
                            ],
                        }
                    ],
                    "thesis_candidates": [],
                    "examples": [],
                    "summary_claims": [],
                },
            }
        ),
        encoding="utf-8",
    )

    claim_inventory_path.write_text(
        json.dumps(
            {
                "claims": [
                    {
                        "claim_id": "claim_001",
                        "verbatim_quote": (
                            "agents change the environment while learning"
                        ),
                        "anchor_chunk": "chunk_001",
                        "char_offset_start": 0,
                        "char_offset_end": 43,
                        "anchor_clip": {
                            "start": 12.0,
                            "end": 18.0,
                        },
                        "claim_type": "empirical_technical",
                        "verification_strategy": "literature_review",
                        "embed_url": (
                            "https://www.youtube-nocookie.com/embed/ABC123"
                            "?start=12&end=18"
                        ),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    written = run_steelman_pipeline(
        config_path=config_path,
        logs_dir=logs_dir,
    )

    assert written == output_path
    assert output_path.exists()

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["self_recognition_check"] == "passed"

    log_files = list(logs_dir.glob("*.json"))
    assert len(log_files) == 1

    run_log = json.loads(log_files[0].read_text(encoding="utf-8"))

    assert run_log["status"] == "success"
    assert run_log["metrics"]["speaker_perspective_use_llm"] is True
    assert run_log["metrics"]["llm_mode_attempted"] is True
    assert run_log["metrics"]["llm_mode_used"] is False
    assert run_log["metrics"]["fallback_used"] is True
    assert run_log["metrics"]["fallback_reason"] == "llm_not_implemented"


def test_run_speaker_perspective_pipeline_use_llm_false_records_no_fallback(tmp_path):
    argument_map_path = tmp_path / "argument_map.json"
    claim_inventory_path = tmp_path / "claim_inventory.json"
    output_path = tmp_path / "speaker_perspective.json"
    logs_dir = tmp_path / "logs"

    config_path = _integration_argument_config_for_load_config(
        tmp_path,
        claim_inventory_path=claim_inventory_path,
        argument_map_path=argument_map_path,
        output_path=output_path,
        speaker_perspective={
            "enabled": True,
            "use_llm": False,
            "output_path": str(output_path),
        },
    )

    argument_map_path.write_text(
        json.dumps(
            {
                "argument_map": {
                    "thesis": (
                        "The speaker argues that multi-agent learning is unstable."
                    ),
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

    claim_inventory_path.write_text(
        json.dumps(
            {
                "claims": [
                    {
                        "claim_id": "claim_001",
                        "verbatim_quote": (
                            "agents change the environment while learning"
                        ),
                        "anchor_chunk": "chunk_001",
                        "char_offset_start": 0,
                        "char_offset_end": 43,
                        "anchor_clip": {"start": 1.0, "end": 2.0},
                        "claim_type": "empirical_technical",
                        "verification_strategy": "literature_review",
                        "embed_url": "https://example.com/embed",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    run_steelman_pipeline(
        config_path=config_path,
        logs_dir=logs_dir,
    )

    log_files = list(logs_dir.glob("*.json"))
    assert len(log_files) == 1

    run_log = json.loads(log_files[0].read_text(encoding="utf-8"))

    assert run_log["status"] == "success"
    assert run_log["metrics"]["speaker_perspective_use_llm"] is False
    assert run_log["metrics"]["llm_mode_attempted"] is False
    assert run_log["metrics"]["llm_mode_used"] is False
    assert run_log["metrics"]["fallback_used"] is False
    assert run_log["metrics"]["fallback_reason"] == ""


def test_default_output_matches_processed_path():
    assert DEFAULT_SPEAKER_PERSPECTIVE_PATH.name == "speaker_perspective.json"
