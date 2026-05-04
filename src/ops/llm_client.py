from typing import Callable, Any

from src.ops.cost_guard import (
    CostGuardState,
    assert_llm_call_allowed,
    record_llm_usage,
)


def safe_llm_call(
    prompt_text: str,
    expected_output_tokens: int,
    budget_config: dict,
    state: CostGuardState,
    input_cost_per_1m_tokens: float,
    output_cost_per_1m_tokens: float,
    llm_callable: Callable[..., dict],
    **llm_kwargs: Any,
) -> dict:
    """
    Safely perform an LLM call using the required gateway order:

    1. Run assert_llm_call_allowed before any external I/O.
    2. Only call the vendor/API through this wrapper.
    3. Record usage after the response.
    4. Prefer API-reported actual usage/cost when available.

    The llm_callable is injected so tests can use a fake function instead of
    making real network requests.
    """

    preflight = assert_llm_call_allowed(
        prompt_text=prompt_text,
        expected_output_tokens=expected_output_tokens,
        budget_config=budget_config,
        state=state,
        input_cost_per_1m_tokens=input_cost_per_1m_tokens,
        output_cost_per_1m_tokens=output_cost_per_1m_tokens,
    )

    response = llm_callable(
        prompt_text=prompt_text,
        expected_output_tokens=expected_output_tokens,
        **llm_kwargs,
    )

    usage = response.get("usage", {})

    actual_input_tokens = usage.get(
        "input_tokens",
        preflight["input_tokens"],
    )

    actual_output_tokens = usage.get(
        "output_tokens",
        preflight["expected_output_tokens"],
    )

    actual_cost_usd = usage.get(
        "cost_usd",
        preflight["estimated_call_cost_usd"],
    )

    record_llm_usage(
        state=state,
        input_tokens=actual_input_tokens,
        output_tokens=actual_output_tokens,
        estimated_cost_usd=actual_cost_usd,
    )

    return response