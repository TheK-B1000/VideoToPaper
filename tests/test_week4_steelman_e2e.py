import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.pipelines.run_steelman_pipeline import run_steelman_pipeline


@pytest.fixture(autouse=True)
def allow_real_llm_calls_env(monkeypatch):
    monkeypatch.setenv("ALLOW_REAL_LLM_CALLS", "true")


def _week4_budget(tmp_path: Path) -> dict:
    # Mirrors prod-ish knobs plus keys required by load_config / cost_guard.
    return {
        "mode": "free_only",
        "daily_budget_usd": 0.0,
        "monthly_budget_usd": 0.0,
        "allow_free_tier_calls": True,
        "llm_enabled": True,
        "dry_run": False,
        "max_llm_calls_per_run": 5,
        "max_input_tokens_per_call": 20_000,
        "max_output_tokens_per_call": 1200,
        "max_total_tokens_per_run": 100_000,
        "max_estimated_cost_usd_per_run": 10.0,
        "max_estimated_cost_usd_per_day": 1000.0,
        "max_estimated_cost_usd_per_month": 10_000.0,
        "max_estimated_cost_usd_per_call": 2.0,
        "allowed_models": ["gemini-2.5-flash-lite"],
        "model_pricing": {},
        "max_prompt_chars": 12000,
        "max_llm_retries_per_call": 1,
        "budget_persistence_dir": str(tmp_path / "budget"),
        "fail_closed": True,
    }


def _write_minimal_argument_config(
    tmp_path: Path,
    *,
    chunks_path: Path,
    argument_map_path: Path,
    claim_inventory_path: Path,
    speaker_perspective_path: Path,
    speaker_perspective: dict,
) -> Path:
    (tmp_path / "budget").mkdir(parents=True, exist_ok=True)
    (tmp_path / "reg_stub.json").write_text("{}", encoding="utf-8")

    config_path = tmp_path / "argument_config.json"
    config_path.write_text(
        json.dumps(
            {
                "stage": "argument_structure",
                "input_path": "data/x.json",
                "output_paths": {
                    "chunks": str(chunks_path.resolve()),
                    "argument_map": str(argument_map_path.resolve()),
                },
                "chunking": {},
                "anchors": {},
                "llm": {},
                "safety": {},
                "budget": _week4_budget(tmp_path),
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


def test_week4_steelman_e2e_with_grounded_claims_and_mocked_llm(tmp_path):
    chunks_path = tmp_path / "chunks.json"
    argument_map_path = tmp_path / "argument_map.json"
    claim_inventory_path = tmp_path / "claim_inventory.json"
    speaker_perspective_path = tmp_path / "speaker_perspective.json"
    logs_dir = tmp_path / "logs"

    chunks_path.write_text(
        json.dumps(
            {
                "chunks": [
                    {
                        "chunk_id": "chunk_001",
                        "source_text": "Reinforcement learning agents learn from rewards.",
                        "clean_text": "Reinforcement learning agents learn from rewards.",
                        "char_start": 0,
                        "char_end": 51,
                        "start_seconds": 12.0,
                        "end_seconds": 18.0,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    argument_map_path.write_text(
        json.dumps(
            {
                "argument_map": {
                    "thesis": (
                        "The speaker argues that reinforcement learning depends on "
                        "reward feedback."
                    ),
                    "supporting_points": [
                        {
                            "claim": "Reinforcement learning agents learn from rewards.",
                            "qualifications": [
                                "the exact reward design affects what the agent learns"
                            ],
                            "anchor_moments": [
                                {
                                    "type": "verbal_claim",
                                    "chunk_id": "chunk_001",
                                    "start": 12.0,
                                    "end": 18.0,
                                }
                            ],
                        }
                    ],
                    "fallback_supporting_points_used": True,
                }
            }
        ),
        encoding="utf-8",
    )

    claim_inventory_path.write_text(
        json.dumps(
            {
                "claim_count": 1,
                "claims": [
                    {
                        "claim_id": "claim_001",
                        "verbatim_quote": (
                            "Reinforcement learning agents learn from rewards."
                        ),
                        "anchor_chunk": "chunk_001",
                        "char_offset_start": 0,
                        "char_offset_end": 51,
                        "anchor_clip": {
                            "start": 12.0,
                            "end": 18.0,
                        },
                        "claim_type": "empirical_technical",
                        "verification_strategy": "literature_review",
                        "embed_url": (
                            "https://www.youtube-nocookie.com/embed/-U81ZCDFEhg"
                            "?start=12&end=18"
                        ),
                    }
                ],
                "summary": {"empirical_technical": 1},
            }
        ),
        encoding="utf-8",
    )

    config_path = _write_minimal_argument_config(
        tmp_path,
        chunks_path=chunks_path,
        argument_map_path=argument_map_path,
        claim_inventory_path=claim_inventory_path,
        speaker_perspective_path=speaker_perspective_path,
        speaker_perspective={
            "enabled": True,
            "use_llm": True,
            "output_path": str(speaker_perspective_path),
            "llm": {
                "provider": "gemini",
                "model": "gemini-2.5-flash-lite",
                "max_output_tokens": 500,
                "max_claims_per_call": 5,
                "fallback_on_guard_rejection": True,
            },
        },
    )

    mocked_llm_response = json.dumps(
        {
            "narrative_blocks": [
                {
                    "text": (
                        "The speaker presents reinforcement learning as a process "
                        "where agents improve by learning from reward feedback."
                    ),
                    "verbatim_anchors": ["claim_001"],
                    "embedded_clip": "claim_001",
                }
            ]
        }
    )

    with patch(
        "src.pipelines.run_steelman_pipeline.safe_llm_call",
        return_value=mocked_llm_response,
    ) as mocked_safe_llm_call:
        written = run_steelman_pipeline(
            config_path=config_path,
            logs_dir=logs_dir,
        )

    assert written == speaker_perspective_path
    assert speaker_perspective_path.exists()
    mocked_safe_llm_call.assert_called_once()

    payload = json.loads(speaker_perspective_path.read_text(encoding="utf-8"))

    assert payload["stage"] == "speaker_perspective"
    assert payload["enabled"] is True
    assert payload["claim_count"] == 1
    assert payload["section_title"] == "The Speaker's Perspective"
    assert payload["self_recognition_check"] == "passed"

    assert payload["narrative_blocks"] == [
        {
            "text": (
                "The speaker presents reinforcement learning as a process "
                "where agents improve by learning from reward feedback."
            ),
            "verbatim_anchors": ["claim_001"],
            "embedded_clip": "claim_001",
        },
        {
            "text": (
                "The speaker also qualifies the argument: "
                "the exact reward design affects what the agent learns"
            ),
            "verbatim_anchors": ["claim_001"],
            "embedded_clip": "claim_001",
        },
    ]

    run_log_path = next(logs_dir.glob("*.json"))
    run_log = json.loads(run_log_path.read_text(encoding="utf-8"))

    assert run_log["pipeline_name"] == "speaker_perspective"
    assert run_log["status"] == "success"
    assert run_log["metrics"]["llm_mode_attempted"] is True
    assert run_log["metrics"]["llm_mode_used"] is True
    assert run_log["metrics"]["fallback_used"] is False
    assert run_log["metrics"]["fallback_reason"] == ""


def test_week4_steelman_e2e_falls_back_on_malformed_llm_response(tmp_path):
    argument_map_path = tmp_path / "argument_map.json"
    claim_inventory_path = tmp_path / "claim_inventory.json"
    speaker_perspective_path = tmp_path / "speaker_perspective.json"
    logs_dir = tmp_path / "logs"
    chunks_path = tmp_path / "chunks_stub.json"
    chunks_path.write_text("{}", encoding="utf-8")

    argument_map_path.write_text(
        json.dumps(
            {
                "argument_map": {
                    "thesis": (
                        "The speaker argues that reinforcement learning depends on "
                        "reward feedback."
                    ),
                    "supporting_points": [
                        {
                            "claim": "Reinforcement learning agents learn from rewards.",
                            "qualifications": [],
                            "anchor_moments": [
                                {
                                    "type": "verbal_claim",
                                    "chunk_id": "chunk_001",
                                    "start": 12.0,
                                    "end": 18.0,
                                }
                            ],
                        }
                    ],
                }
            }
        ),
        encoding="utf-8",
    )

    claim_inventory_path.write_text(
        json.dumps(
            {
                "claim_count": 1,
                "claims": [
                    {
                        "claim_id": "claim_001",
                        "verbatim_quote": (
                            "Reinforcement learning agents learn from rewards."
                        ),
                        "anchor_chunk": "chunk_001",
                        "anchor_clip": {
                            "start": 12.0,
                            "end": 18.0,
                        },
                        "claim_type": "empirical_technical",
                        "verification_strategy": "literature_review",
                        "embed_url": (
                            "https://www.youtube-nocookie.com/embed/-U81ZCDFEhg"
                            "?start=12&end=18"
                        ),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    config_path = _write_minimal_argument_config(
        tmp_path,
        chunks_path=chunks_path,
        argument_map_path=argument_map_path,
        claim_inventory_path=claim_inventory_path,
        speaker_perspective_path=speaker_perspective_path,
        speaker_perspective={
            "enabled": True,
            "use_llm": True,
            "output_path": str(speaker_perspective_path),
            "llm": {
                "provider": "gemini",
                "model": "gemini-2.5-flash-lite",
                "max_output_tokens": 500,
                "max_claims_per_call": 5,
                "fallback_on_guard_rejection": True,
            },
        },
    )

    with patch(
        "src.pipelines.run_steelman_pipeline.safe_llm_call",
        return_value="not-json",
    ):
        written = run_steelman_pipeline(
            config_path=config_path,
            logs_dir=logs_dir,
        )

    assert written == speaker_perspective_path
    payload = json.loads(speaker_perspective_path.read_text(encoding="utf-8"))

    assert payload["claim_count"] == 1
    assert payload["self_recognition_check"] == "passed"
    assert payload["narrative_blocks"][0]["text"] == (
        "The speaker emphasizes the following point: "
        "\u201cReinforcement learning agents learn from rewards.\u201d"
    )

    run_log = json.loads(next(logs_dir.glob("*.json")).read_text(encoding="utf-8"))

    assert run_log["metrics"]["llm_mode_attempted"] is True
    assert run_log["metrics"]["llm_mode_used"] is False
    assert run_log["metrics"]["fallback_used"] is True
    assert run_log["metrics"]["fallback_reason"] == "llm_response_parse_failed"
