import pytest

from src.ops.cost_guard import (
    CostGuardState,
    assert_llm_call_allowed,
    estimate_llm_cost_usd,
    estimate_tokens,
    record_llm_usage,
)


def make_budget_config(
    llm_enabled: bool = True,
    dry_run: bool = False,
    max_llm_calls_per_run: int = 3,
    max_input_tokens_per_call: int = 100,
    max_output_tokens_per_call: int = 50,
    max_total_tokens_per_run: int = 200,
    max_estimated_cost_usd_per_run: float = 0.01,
    fail_closed: bool = True,
) -> dict:
    return {
        "llm_enabled": llm_enabled,
        "dry_run": dry_run,
        "max_llm_calls_per_run": max_llm_calls_per_run,
        "max_input_tokens_per_call": max_input_tokens_per_call,
        "max_output_tokens_per_call": max_output_tokens_per_call,
        "max_total_tokens_per_run": max_total_tokens_per_run,
        "max_estimated_cost_usd_per_run": max_estimated_cost_usd_per_run,
        "fail_closed": fail_closed,
    }


def test_estimate_tokens_returns_zero_for_empty_text():
    assert estimate_tokens("") == 0


def test_estimate_tokens_estimates_from_character_count():
    text = "a" * 40

    result = estimate_tokens(text)

    assert result == 10


def test_estimate_tokens_returns_at_least_one_for_short_text():
    assert estimate_tokens("hi") == 1


def test_estimate_tokens_rejects_non_string():
    with pytest.raises(TypeError, match="text must be a string"):
        estimate_tokens(123)


def test_estimate_llm_cost_usd_calculates_cost():
    cost = estimate_llm_cost_usd(
        input_tokens=1_000_000,
        output_tokens=1_000_000,
        input_cost_per_1m_tokens=0.15,
        output_cost_per_1m_tokens=0.60,
    )

    assert cost == pytest.approx(0.75)


def test_estimate_llm_cost_rejects_negative_input_tokens():
    with pytest.raises(ValueError, match="input_tokens cannot be negative"):
        estimate_llm_cost_usd(
            input_tokens=-1,
            output_tokens=0,
            input_cost_per_1m_tokens=0.15,
            output_cost_per_1m_tokens=0.60,
        )


def test_estimate_llm_cost_rejects_negative_output_tokens():
    with pytest.raises(ValueError, match="output_tokens cannot be negative"):
        estimate_llm_cost_usd(
            input_tokens=0,
            output_tokens=-1,
            input_cost_per_1m_tokens=0.15,
            output_cost_per_1m_tokens=0.60,
        )


def test_estimate_llm_cost_rejects_negative_input_price():
    with pytest.raises(ValueError, match="input_cost_per_1m_tokens cannot be negative"):
        estimate_llm_cost_usd(
            input_tokens=0,
            output_tokens=0,
            input_cost_per_1m_tokens=-0.15,
            output_cost_per_1m_tokens=0.60,
        )


def test_estimate_llm_cost_rejects_negative_output_price():
    with pytest.raises(ValueError, match="output_cost_per_1m_tokens cannot be negative"):
        estimate_llm_cost_usd(
            input_tokens=0,
            output_tokens=0,
            input_cost_per_1m_tokens=0.15,
            output_cost_per_1m_tokens=-0.60,
        )


def test_assert_llm_call_allowed_accepts_safe_call():
    state = CostGuardState()
    budget_config = make_budget_config()

    result = assert_llm_call_allowed(
        prompt_text="This is a short prompt.",
        expected_output_tokens=10,
        budget_config=budget_config,
        state=state,
        input_cost_per_1m_tokens=0.15,
        output_cost_per_1m_tokens=0.60,
    )

    assert result["allowed"] is True
    assert result["input_tokens"] > 0
    assert result["expected_output_tokens"] == 10
    assert result["projected_call_count"] == 1
    assert result["projected_total_tokens"] > 0
    assert result["projected_cost_usd"] >= 0


def test_assert_llm_call_allowed_blocks_when_llm_disabled():
    state = CostGuardState()
    budget_config = make_budget_config(llm_enabled=False)

    with pytest.raises(PermissionError, match="LLM calls are disabled by config"):
        assert_llm_call_allowed(
            prompt_text="This should not be sent.",
            expected_output_tokens=10,
            budget_config=budget_config,
            state=state,
            input_cost_per_1m_tokens=0.15,
            output_cost_per_1m_tokens=0.60,
        )


def test_assert_llm_call_allowed_blocks_dry_run():
    state = CostGuardState()
    budget_config = make_budget_config(dry_run=True)

    with pytest.raises(PermissionError, match="LLM dry_run is enabled"):
        assert_llm_call_allowed(
            prompt_text="This should only be estimated.",
            expected_output_tokens=10,
            budget_config=budget_config,
            state=state,
            input_cost_per_1m_tokens=0.15,
            output_cost_per_1m_tokens=0.60,
        )


def test_assert_llm_call_allowed_blocks_call_count_limit():
    state = CostGuardState(llm_call_count=3)
    budget_config = make_budget_config(max_llm_calls_per_run=3)

    with pytest.raises(PermissionError, match="LLM call limit exceeded for this run"):
        assert_llm_call_allowed(
            prompt_text="One call too many.",
            expected_output_tokens=10,
            budget_config=budget_config,
            state=state,
            input_cost_per_1m_tokens=0.15,
            output_cost_per_1m_tokens=0.60,
        )


def test_assert_llm_call_allowed_blocks_input_token_limit():
    state = CostGuardState()
    budget_config = make_budget_config(max_input_tokens_per_call=5)

    with pytest.raises(PermissionError, match="LLM input token limit exceeded for this call"):
        assert_llm_call_allowed(
            prompt_text="a" * 100,
            expected_output_tokens=10,
            budget_config=budget_config,
            state=state,
            input_cost_per_1m_tokens=0.15,
            output_cost_per_1m_tokens=0.60,
        )


def test_assert_llm_call_allowed_blocks_output_token_limit():
    state = CostGuardState()
    budget_config = make_budget_config(max_output_tokens_per_call=10)

    with pytest.raises(PermissionError, match="LLM output token limit exceeded for this call"):
        assert_llm_call_allowed(
            prompt_text="Short prompt.",
            expected_output_tokens=50,
            budget_config=budget_config,
            state=state,
            input_cost_per_1m_tokens=0.15,
            output_cost_per_1m_tokens=0.60,
        )


def test_assert_llm_call_allowed_blocks_total_token_limit():
    state = CostGuardState(
        llm_call_count=1,
        total_input_tokens=90,
        total_output_tokens=90,
        total_estimated_cost_usd=0.0,
    )
    budget_config = make_budget_config(max_total_tokens_per_run=200)

    with pytest.raises(PermissionError, match="LLM total token limit exceeded for this run"):
        assert_llm_call_allowed(
            prompt_text="a" * 80,
            expected_output_tokens=10,
            budget_config=budget_config,
            state=state,
            input_cost_per_1m_tokens=0.15,
            output_cost_per_1m_tokens=0.60,
        )


def test_assert_llm_call_allowed_blocks_estimated_cost_limit():
    state = CostGuardState()
    budget_config = make_budget_config(
        max_estimated_cost_usd_per_run=0.000001,
        max_input_tokens_per_call=1_000_000,
        max_output_tokens_per_call=1_000_000,
        max_total_tokens_per_run=2_000_000,
    )

    with pytest.raises(PermissionError, match="LLM estimated cost limit exceeded for this run"):
        assert_llm_call_allowed(
            prompt_text="a" * 4000,
            expected_output_tokens=1000,
            budget_config=budget_config,
            state=state,
            input_cost_per_1m_tokens=15.00,
            output_cost_per_1m_tokens=60.00,
        )


def test_assert_llm_call_allowed_rejects_missing_budget_keys():
    state = CostGuardState()
    budget_config = {
        "llm_enabled": True,
    }

    with pytest.raises(ValueError, match="budget_config missing required keys"):
        assert_llm_call_allowed(
            prompt_text="Short prompt.",
            expected_output_tokens=10,
            budget_config=budget_config,
            state=state,
            input_cost_per_1m_tokens=0.15,
            output_cost_per_1m_tokens=0.60,
        )


def test_assert_llm_call_allowed_rejects_fail_open_config():
    state = CostGuardState()
    budget_config = make_budget_config(fail_closed=False)

    with pytest.raises(ValueError, match="fail_closed must be true for safety"):
        assert_llm_call_allowed(
            prompt_text="Short prompt.",
            expected_output_tokens=10,
            budget_config=budget_config,
            state=state,
            input_cost_per_1m_tokens=0.15,
            output_cost_per_1m_tokens=0.60,
        )


def test_assert_llm_call_allowed_rejects_invalid_budget_config_type():
    state = CostGuardState()

    with pytest.raises(TypeError, match="budget_config must be a dictionary"):
        assert_llm_call_allowed(
            prompt_text="Short prompt.",
            expected_output_tokens=10,
            budget_config="not a dict",
            state=state,
            input_cost_per_1m_tokens=0.15,
            output_cost_per_1m_tokens=0.60,
        )


def test_assert_llm_call_allowed_rejects_invalid_state_type():
    budget_config = make_budget_config()

    with pytest.raises(TypeError, match="state must be a CostGuardState"):
        assert_llm_call_allowed(
            prompt_text="Short prompt.",
            expected_output_tokens=10,
            budget_config=budget_config,
            state={},
            input_cost_per_1m_tokens=0.15,
            output_cost_per_1m_tokens=0.60,
        )


def test_assert_llm_call_allowed_rejects_negative_expected_output_tokens():
    state = CostGuardState()
    budget_config = make_budget_config()

    with pytest.raises(ValueError, match="expected_output_tokens cannot be negative"):
        assert_llm_call_allowed(
            prompt_text="Short prompt.",
            expected_output_tokens=-1,
            budget_config=budget_config,
            state=state,
            input_cost_per_1m_tokens=0.15,
            output_cost_per_1m_tokens=0.60,
        )


def test_record_llm_usage_updates_state():
    state = CostGuardState()

    updated = record_llm_usage(
        state=state,
        input_tokens=100,
        output_tokens=25,
        estimated_cost_usd=0.001,
    )

    assert updated.llm_call_count == 1
    assert updated.total_input_tokens == 100
    assert updated.total_output_tokens == 25
    assert updated.total_estimated_cost_usd == pytest.approx(0.001)


def test_record_llm_usage_accumulates_state():
    state = CostGuardState()

    record_llm_usage(
        state=state,
        input_tokens=100,
        output_tokens=25,
        estimated_cost_usd=0.001,
    )

    updated = record_llm_usage(
        state=state,
        input_tokens=50,
        output_tokens=10,
        estimated_cost_usd=0.0005,
    )

    assert updated.llm_call_count == 2
    assert updated.total_input_tokens == 150
    assert updated.total_output_tokens == 35
    assert updated.total_estimated_cost_usd == pytest.approx(0.0015)


def test_record_llm_usage_rejects_invalid_state_type():
    with pytest.raises(TypeError, match="state must be a CostGuardState"):
        record_llm_usage(
            state={},
            input_tokens=100,
            output_tokens=25,
            estimated_cost_usd=0.001,
        )


def test_record_llm_usage_rejects_negative_input_tokens():
    state = CostGuardState()

    with pytest.raises(ValueError, match="input_tokens cannot be negative"):
        record_llm_usage(
            state=state,
            input_tokens=-1,
            output_tokens=25,
            estimated_cost_usd=0.001,
        )


def test_record_llm_usage_rejects_negative_output_tokens():
    state = CostGuardState()

    with pytest.raises(ValueError, match="output_tokens cannot be negative"):
        record_llm_usage(
            state=state,
            input_tokens=100,
            output_tokens=-1,
            estimated_cost_usd=0.001,
        )


def test_record_llm_usage_rejects_negative_cost():
    state = CostGuardState()

    with pytest.raises(ValueError, match="estimated_cost_usd cannot be negative"):
        record_llm_usage(
            state=state,
            input_tokens=100,
            output_tokens=25,
            estimated_cost_usd=-0.001,
        )