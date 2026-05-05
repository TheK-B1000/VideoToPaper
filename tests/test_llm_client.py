import tempfile

import pytest

from src.ops.cost_guard import CostGuardState
from src.ops.llm_client import safe_llm_call


@pytest.fixture(autouse=True)
def allow_real_llm_env(monkeypatch):
    monkeypatch.setenv("ALLOW_REAL_LLM_CALLS", "true")


def make_budget_config(**overrides):
    config = {
        "llm_enabled": True,
        "dry_run": False,
        "max_llm_calls_per_run": 3,
        "max_input_tokens_per_call": 1_000,
        "max_output_tokens_per_call": 500,
        "max_total_tokens_per_run": 2_000,
        "max_estimated_cost_usd_per_run": 1.00,
        "max_estimated_cost_usd_per_day": 1000.0,
        "max_estimated_cost_usd_per_month": 10_000.0,
        "max_estimated_cost_usd_per_call": 1.0,
        "allowed_models": ["gpt-4o-mini"],
        "model_pricing": {
            "gpt-4o-mini": {
                "input_cost_per_1m_tokens": 0.15,
                "output_cost_per_1m_tokens": 0.60,
            },
        },
        "max_prompt_chars": 500_000,
        "max_llm_retries_per_call": 1,
        "budget_persistence_dir": tempfile.mkdtemp(prefix="vtp_budget_llm_"),
        "fail_closed": True,
    }

    config.update(overrides)
    return config


def fake_llm_callable(prompt_text, expected_output_tokens, **kwargs):
    return {
        "text": "Fake LLM response",
        "usage": {
            "input_tokens": 12,
            "output_tokens": 8,
            "cost_usd": 0.0001,
        },
    }


def test_safe_llm_call_returns_response():
    state = CostGuardState()
    budget_config = make_budget_config()

    response = safe_llm_call(
        prompt_text="Summarize this transcript.",
        expected_output_tokens=100,
        budget_config=budget_config,
        state=state,
        llm_callable=fake_llm_callable,
        model="gpt-4o-mini",
    )

    assert response["text"] == "Fake LLM response"


def test_safe_llm_call_records_actual_usage():
    state = CostGuardState()
    budget_config = make_budget_config()

    safe_llm_call(
        prompt_text="Summarize this transcript.",
        expected_output_tokens=100,
        budget_config=budget_config,
        state=state,
        llm_callable=fake_llm_callable,
        model="gpt-4o-mini",
    )

    assert state.llm_call_count == 1
    assert state.total_input_tokens == 12
    assert state.total_output_tokens == 8
    assert state.total_estimated_cost_usd == 0.0001


def test_safe_llm_call_rejects_non_positive_output_tokens():
    state = CostGuardState()
    budget_config = make_budget_config()

    with pytest.raises(ValueError, match="expected_output_tokens must be greater than zero"):
        safe_llm_call(
            prompt_text="Hi",
            expected_output_tokens=0,
            budget_config=budget_config,
            state=state,
            llm_callable=fake_llm_callable,
            model="gpt-4o-mini",
        )


def test_safe_llm_call_blocks_when_llm_disabled():
    state = CostGuardState()
    budget_config = make_budget_config(llm_enabled=False)

    with pytest.raises(PermissionError, match="LLM calls are disabled"):
        safe_llm_call(
            prompt_text="This should not run.",
            expected_output_tokens=100,
            budget_config=budget_config,
            state=state,
            llm_callable=fake_llm_callable,
            model="gpt-4o-mini",
        )

    assert state.llm_call_count == 0


def test_safe_llm_call_does_not_call_vendor_when_blocked():
    state = CostGuardState()
    budget_config = make_budget_config(dry_run=True)

    was_called = False

    def fake_vendor_that_should_not_run(prompt_text, expected_output_tokens, **kwargs):
        nonlocal was_called
        was_called = True
        return {"text": "Should not happen"}

    with pytest.raises(PermissionError, match="dry_run"):
        safe_llm_call(
            prompt_text="This should be blocked.",
            expected_output_tokens=100,
            budget_config=budget_config,
            state=state,
            llm_callable=fake_vendor_that_should_not_run,
            model="gpt-4o-mini",
        )

    assert was_called is False
    assert state.llm_call_count == 0


def test_safe_llm_call_falls_back_to_preflight_usage_when_actual_usage_missing():
    state = CostGuardState()
    budget_config = make_budget_config()

    def fake_llm_without_usage(prompt_text, expected_output_tokens, **kwargs):
        return {
            "text": "No usage metadata here",
        }

    response = safe_llm_call(
        prompt_text="abcd" * 20,
        expected_output_tokens=50,
        budget_config=budget_config,
        state=state,
        llm_callable=fake_llm_without_usage,
        model="gpt-4o-mini",
    )

    assert response["text"] == "No usage metadata here"
    assert state.llm_call_count == 1
    assert state.total_input_tokens > 0
    assert state.total_output_tokens == 50
    assert state.total_estimated_cost_usd > 0
