import json
import tempfile
from unittest.mock import patch

from src.ops.cost_guard import CostGuardState, LlmGuardRefusal
from src.pipelines.steelman_llm import try_steelman_llm_drafts


def _budget_config():
    return {
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
        "max_prompt_chars": 500_000,
        "max_llm_retries_per_call": 1,
        "budget_persistence_dir": tempfile.mkdtemp(prefix="vtp_steelman_llm_"),
        "fail_closed": True,
    }


def _claims():
    return [
        {
            "claim_id": "claim_001",
            "verbatim_quote": "agents change the environment while learning",
            "claim_type": "empirical_technical",
            "embed_url": "https://www.youtube-nocookie.com/embed/ABC123?start=12&end=18",
        }
    ]


def _argument_map():
    return {
        "thesis": "The speaker argues that multi-agent learning is unstable.",
        "supporting_points": [
            {
                "claim": "Agents change the environment while learning.",
                "qualifications": ["some methods reduce this instability"],
            }
        ],
    }


def _llm_settings():
    return {
        "provider": "gemini",
        "model": "gemini-2.5-flash-lite",
        "max_output_tokens": 500,
        "max_claims_per_call": 6,
        "fallback_on_guard_rejection": True,
    }


def _ledger_context():
    return {"pipeline_name": "steelman_llm_test", "run_id": "run-test-001"}


def test_try_steelman_llm_drafts_success_uses_safe_llm_call():
    payload = {
        "narrative_blocks": [
            {
                "text": (
                    "The speaker frames multi-agent learning as unstable because "
                    "agents change the environment while learning."
                ),
                "verbatim_anchors": ["claim_001"],
                "embedded_clip": "claim_001",
            }
        ]
    }
    mocked_response = {"text": json.dumps(payload)}

    with patch(
        "src.pipelines.steelman_llm.safe_llm_call",
        return_value=mocked_response,
    ) as mocked_safe_call:
        drafted, reason = try_steelman_llm_drafts(
            claims=_claims(),
            argument_map=_argument_map(),
            llm_settings=_llm_settings(),
            budget_config=_budget_config(),
            guard_state=CostGuardState(),
            ledger_context=_ledger_context(),
            llm_callable=lambda **_: {"text": "unused_under_patch"},
        )

    mocked_safe_call.assert_called_once()
    kwargs = mocked_safe_call.call_args.kwargs
    assert kwargs["model"] == "gemini-2.5-flash-lite"
    assert kwargs["expected_output_tokens"] == 500
    assert "claim_001" in kwargs["prompt_text"]

    assert reason is None
    assert drafted is not None
    assert drafted[0]["text"].startswith("The speaker frames multi-agent learning")


def test_try_steelman_llm_drafts_llm_callable_none():
    drafted, reason = try_steelman_llm_drafts(
        claims=_claims(),
        argument_map=_argument_map(),
        llm_settings=_llm_settings(),
        budget_config=_budget_config(),
        guard_state=CostGuardState(),
        ledger_context=_ledger_context(),
        llm_callable=None,
    )
    assert drafted is None
    assert reason == "llm_callable_not_configured"


def test_try_steelman_llm_drafts_guard_refusal_llm_guard_refusal():
    refusal = LlmGuardRefusal(
        "model_not_allowed",
        "Model is not allowed.",
    )
    with patch(
        "src.pipelines.steelman_llm.safe_llm_call",
        side_effect=refusal,
    ):
        drafted, reason = try_steelman_llm_drafts(
            claims=_claims(),
            argument_map=_argument_map(),
            llm_settings=_llm_settings(),
            budget_config=_budget_config(),
            guard_state=CostGuardState(),
            ledger_context=_ledger_context(),
            llm_callable=lambda **_: {"text": "{}"},
        )
    assert drafted is None
    assert reason is not None
    assert reason.startswith("guard_rejected:")


def test_try_steelman_llm_drafts_guard_refusal_plain_permission_error():
    with patch(
        "src.pipelines.steelman_llm.safe_llm_call",
        side_effect=PermissionError("plain permission error"),
    ):
        drafted, reason = try_steelman_llm_drafts(
            claims=_claims(),
            argument_map=_argument_map(),
            llm_settings=_llm_settings(),
            budget_config=_budget_config(),
            guard_state=CostGuardState(),
            ledger_context=_ledger_context(),
            llm_callable=lambda **_: {"text": "{}"},
        )
    assert drafted is None
    assert reason.startswith("guard_rejected:")


def test_try_steelman_llm_drafts_vendor_failure_after_guard():
    with patch(
        "src.pipelines.steelman_llm.safe_llm_call",
        side_effect=RuntimeError("network exploded"),
    ):
        drafted, reason = try_steelman_llm_drafts(
            claims=_claims(),
            argument_map=_argument_map(),
            llm_settings=_llm_settings(),
            budget_config=_budget_config(),
            guard_state=CostGuardState(),
            ledger_context=_ledger_context(),
            llm_callable=lambda **_: {"text": "{}"},
        )
    assert drafted is None
    assert reason.startswith("llm_failed:RuntimeError:")


def test_try_steelman_llm_drafts_malformed_json_in_response_text():
    with patch(
        "src.pipelines.steelman_llm.safe_llm_call",
        return_value={"text": "not json"},
    ):
        drafted, reason = try_steelman_llm_drafts(
            claims=_claims(),
            argument_map=_argument_map(),
            llm_settings=_llm_settings(),
            budget_config=_budget_config(),
            guard_state=CostGuardState(),
            ledger_context=_ledger_context(),
            llm_callable=lambda **_: {"text": "not json"},
        )
    assert drafted is None
    assert reason is not None
    assert reason.startswith("parse_failed:")


def test_try_steelman_llm_drafts_parse_success_preserves_llm_anchors_no_inventory_validation():
    """
    try_steelman_llm_drafts parses JSON only; anchor validity vs claim_inventory
    is enforced in run_steelman_pipeline via build_steelman_section.
    """
    payload = {
        "narrative_blocks": [
            {
                "text": "The speaker says something unsupported.",
                "verbatim_anchors": ["fake_claim_999"],
                "embedded_clip": "fake_claim_999",
            }
        ]
    }
    text = json.dumps(payload)
    with patch(
        "src.pipelines.steelman_llm.safe_llm_call",
        return_value={"text": text},
    ):
        drafted, reason = try_steelman_llm_drafts(
            claims=_claims(),
            argument_map=_argument_map(),
            llm_settings=_llm_settings(),
            budget_config=_budget_config(),
            guard_state=CostGuardState(),
            ledger_context=_ledger_context(),
            llm_callable=lambda **_: {"text": text},
        )
    assert reason is None
    assert drafted is not None
    assert drafted[0]["verbatim_anchors"] == ["fake_claim_999"]
