"""
Week 4 steelman: optional LLM draft pass.

All provider traffic goes through :func:`src.ops.llm_client.safe_llm_call`.
This module does not call vendors directly.
"""

from __future__ import annotations

from typing import Any, Callable

from src.ops.cost_guard import CostGuardState
from src.ops.llm_client import safe_llm_call
from src.pipelines.steelman_prompt import build_steelman_prompt, parse_steelman_prompt_response

# Pre-flight pricing for gpt-4o-mini scale (USD per 1M tokens); approximate.
DEFAULT_INPUT_COST_PER_1M_TOKENS = 0.15
DEFAULT_OUTPUT_COST_PER_1M_TOKENS = 0.60


def try_steelman_llm_drafts(
    *,
    claims: list[dict[str, Any]],
    argument_map: dict[str, Any],
    llm_settings: dict[str, Any],
    budget_config: dict[str, Any],
    guard_state: CostGuardState,
    ledger_context: dict[str, Any],
    llm_callable: Callable[..., dict] | None,
    input_cost_per_1m_tokens: float = DEFAULT_INPUT_COST_PER_1M_TOKENS,
    output_cost_per_1m_tokens: float = DEFAULT_OUTPUT_COST_PER_1M_TOKENS,
) -> tuple[list[dict[str, Any]] | None, str | None]:
    """
    Attempt one guarded LLM call and return drafted narrative block dicts.

    On any guard rejection, vendor failure (after retries inside ``safe_llm_call``),
    missing callable, bad budget, or parse error: returns ``(None, reason)`` so the
    pipeline can fall back to the conservative steelman path without failing.
    """
    if llm_callable is None:
        return None, "llm_callable_not_configured"

    model = llm_settings["model"]
    max_out = int(llm_settings["max_output_tokens"])
    max_claims = int(llm_settings["max_claims_per_call"])

    if max_out <= 0:
        return None, "invalid_max_output_tokens"

    try:
        prompt = build_steelman_prompt(
            claim_inventory=claims,
            argument_map=argument_map,
            max_claims=max_claims,
        )
    except ValueError as exc:
        return None, f"prompt_build_failed:{exc}"

    try:
        response = safe_llm_call(
            prompt_text=prompt,
            expected_output_tokens=max_out,
            budget_config=budget_config,
            state=guard_state,
            input_cost_per_1m_tokens=input_cost_per_1m_tokens,
            output_cost_per_1m_tokens=output_cost_per_1m_tokens,
            llm_callable=llm_callable,
            model=model,
            ledger_context=ledger_context,
        )
    except PermissionError as exc:
        return None, f"guard_rejected:{exc}"
    except Exception as exc:
        return None, f"llm_failed:{type(exc).__name__}:{exc}"

    text = response.get("text")
    if not isinstance(text, str) or not text.strip():
        return None, "llm_response_missing_text"

    try:
        drafted = parse_steelman_prompt_response(text.strip())
    except ValueError as exc:
        return None, f"parse_failed:{exc}"

    return drafted, None
