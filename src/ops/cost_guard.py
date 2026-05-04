from dataclasses import dataclass


@dataclass
class CostGuardState:
    """
    Tracks LLM usage during a single pipeline run.
    """
    llm_call_count: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_estimated_cost_usd: float = 0.0


def estimate_tokens(text: str) -> int:
    """
    Estimate token count from text.

    This is intentionally conservative. A rough common estimate is
    1 token ≈ 4 characters for English text.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    if not text:
        return 0

    return max(1, len(text) // 4)


def estimate_llm_cost_usd(
    input_tokens: int,
    output_tokens: int,
    input_cost_per_1m_tokens: float,
    output_cost_per_1m_tokens: float,
) -> float:
    """
    Estimate LLM call cost using per-million-token pricing.
    """
    if input_tokens < 0:
        raise ValueError("input_tokens cannot be negative")

    if output_tokens < 0:
        raise ValueError("output_tokens cannot be negative")

    if input_cost_per_1m_tokens < 0:
        raise ValueError("input_cost_per_1m_tokens cannot be negative")

    if output_cost_per_1m_tokens < 0:
        raise ValueError("output_cost_per_1m_tokens cannot be negative")

    input_cost = (input_tokens / 1_000_000) * input_cost_per_1m_tokens
    output_cost = (output_tokens / 1_000_000) * output_cost_per_1m_tokens

    return input_cost + output_cost


def assert_llm_call_allowed(
    prompt_text: str,
    expected_output_tokens: int,
    budget_config: dict,
    state: CostGuardState,
    input_cost_per_1m_tokens: float,
    output_cost_per_1m_tokens: float,
) -> dict:
    """
    Validate whether a future LLM call is allowed under the run budget.

    This function should be called before any API request is made.

    Args:
        prompt_text: Full text that would be sent to the LLM.
        expected_output_tokens: Maximum expected output tokens for the call.
        budget_config: Budget section from config.
        state: Current CostGuardState for this pipeline run.
        input_cost_per_1m_tokens: Model input price per 1M tokens.
        output_cost_per_1m_tokens: Model output price per 1M tokens.

    Returns:
        A dictionary with estimated usage/cost for the proposed call.

    Raises:
        PermissionError: If the LLM is disabled, dry-run is enabled, or budget is exceeded.
        ValueError: If budget settings are invalid.
    """
    if not isinstance(budget_config, dict):
        raise TypeError("budget_config must be a dictionary")

    if not isinstance(state, CostGuardState):
        raise TypeError("state must be a CostGuardState")

    required_keys = [
        "llm_enabled",
        "dry_run",
        "max_llm_calls_per_run",
        "max_input_tokens_per_call",
        "max_output_tokens_per_call",
        "max_total_tokens_per_run",
        "max_estimated_cost_usd_per_run",
        "fail_closed",
    ]

    missing_keys = [
        key for key in required_keys
        if key not in budget_config
    ]

    if missing_keys:
        raise ValueError(f"budget_config missing required keys: {missing_keys}")

    if budget_config.get("fail_closed", True) is not True:
        raise ValueError("fail_closed must be true for safety")

    input_tokens = estimate_tokens(prompt_text)
    output_tokens = expected_output_tokens

    if output_tokens < 0:
        raise ValueError("expected_output_tokens cannot be negative")

    estimated_call_cost = estimate_llm_cost_usd(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        input_cost_per_1m_tokens=input_cost_per_1m_tokens,
        output_cost_per_1m_tokens=output_cost_per_1m_tokens,
    )

    projected_call_count = state.llm_call_count + 1
    projected_total_tokens = (
        state.total_input_tokens
        + state.total_output_tokens
        + input_tokens
        + output_tokens
    )
    projected_cost = state.total_estimated_cost_usd + estimated_call_cost

    if not budget_config["llm_enabled"]:
        raise PermissionError("LLM calls are disabled by config")

    if budget_config["dry_run"]:
        raise PermissionError("LLM dry_run is enabled; refusing real API call")

    if projected_call_count > budget_config["max_llm_calls_per_run"]:
        raise PermissionError("LLM call limit exceeded for this run")

    if input_tokens > budget_config["max_input_tokens_per_call"]:
        raise PermissionError("LLM input token limit exceeded for this call")

    if output_tokens > budget_config["max_output_tokens_per_call"]:
        raise PermissionError("LLM output token limit exceeded for this call")

    if projected_total_tokens > budget_config["max_total_tokens_per_run"]:
        raise PermissionError("LLM total token limit exceeded for this run")

    if projected_cost > budget_config["max_estimated_cost_usd_per_run"]:
        raise PermissionError("LLM estimated cost limit exceeded for this run")

    return {
        "allowed": True,
        "input_tokens": input_tokens,
        "expected_output_tokens": output_tokens,
        "estimated_call_cost_usd": estimated_call_cost,
        "projected_call_count": projected_call_count,
        "projected_total_tokens": projected_total_tokens,
        "projected_cost_usd": projected_cost,
    }


def record_llm_usage(
    state: CostGuardState,
    input_tokens: int,
    output_tokens: int,
    estimated_cost_usd: float,
) -> CostGuardState:
    """
    Update cost guard state after a successful LLM call.
    """
    if not isinstance(state, CostGuardState):
        raise TypeError("state must be a CostGuardState")

    if input_tokens < 0:
        raise ValueError("input_tokens cannot be negative")

    if output_tokens < 0:
        raise ValueError("output_tokens cannot be negative")

    if estimated_cost_usd < 0:
        raise ValueError("estimated_cost_usd cannot be negative")

    state.llm_call_count += 1
    state.total_input_tokens += input_tokens
    state.total_output_tokens += output_tokens
    state.total_estimated_cost_usd += estimated_cost_usd

    return state