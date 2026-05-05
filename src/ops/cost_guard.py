from dataclasses import dataclass
import os
import re
from pathlib import Path

from src.ops.budget_persistence import load_daily_spend_usd, load_monthly_spend_usd


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
    Estimate token count from text for pre-flight budget checks only.

    Uses a rough heuristic (≈ 4 characters per token). Good enough for an
    early safety net; for tighter limits, prefer the tokenizer for the actual
    deployment model and use those counts in ``assert_llm_call_allowed``.

    Post-call accounting should use usage reported by the API via
    ``record_llm_usage``, not this estimate alone.
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


class LlmGuardRefusal(PermissionError):
    """
    Policy refusal from the LLM cost guard with a stable ``reason_code`` for
    ledger rows and alerting (distinct from human-readable ``str(exc)``).

    Examples of ``reason_code``: ``no_pricing``, ``model_not_allowed``,
    ``per_call_cost_exceeded``, ``dry_run_enabled``.
    """

    __slots__ = ("reason_code",)

    def __init__(self, reason_code: str, message: str) -> None:
        super().__init__(message)
        self.reason_code = reason_code


# Built-in per-model rates (USD per 1M tokens). Merged with ``budget_config["model_pricing"]``;
# config entries override these for the same model id.
#
# Keep vendor-specific *paid* defaults out of here—those belong in ``model_pricing`` so prod
# rates are explicit and tests can use fixture pricing without inheriting wrong numbers.
BUILTIN_MODEL_PRICING: dict[str, dict[str, float]] = {
    "gemini-2.5-flash-lite": {
        "input_cost_per_1m_tokens": 0.0,
        "output_cost_per_1m_tokens": 0.0,
    },
}


def _normalize_model_pricing_row(entry: object, *, label: str) -> dict[str, float]:
    if not isinstance(entry, dict):
        raise ValueError(f"{label}: pricing entry must be an object")

    out: dict[str, float] = {}
    for key in ("input_cost_per_1m_tokens", "output_cost_per_1m_tokens"):
        if key not in entry:
            raise ValueError(f"{label}: missing {key}")
        raw = entry[key]
        if not isinstance(raw, (int, float)):
            raise ValueError(f"{label}: {key} must be a number")
        val = float(raw)
        if val < 0:
            raise ValueError(f"{label}: {key} cannot be negative")
        out[key] = val
    return out


def merged_model_pricing_table(budget_config: dict) -> dict[str, dict[str, float]]:
    """
    Return effective ``model_id -> {input_cost_per_1m_tokens, output_cost_per_1m_tokens}``.

    Starts from :data:`BUILTIN_MODEL_PRICING`, then applies ``budget_config["model_pricing"]``
    overrides (full replace per model id).

    Dict insertion order is builtins first, then each config key in JSON/object order.
    No guard logic depends on iteration order; use only for stable display/logging on
    supported Python versions (dict order is guaranteed 3.7+).
    """
    raw = budget_config["model_pricing"]
    if not isinstance(raw, dict):
        raise ValueError("budget_config.model_pricing must be a dictionary")

    merged: dict[str, dict[str, float]] = {
        name: dict(row) for name, row in BUILTIN_MODEL_PRICING.items()
    }
    for name, entry in raw.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("budget_config.model_pricing keys must be non-empty strings")
        sid = name.strip()
        merged[sid] = _normalize_model_pricing_row(
            entry, label=f"budget_config.model_pricing[{sid!r}]"
        )
    return merged


def resolve_model_pricing_for_call(model: str, budget_config: dict) -> tuple[float, float]:
    """
    Resolve input/output per-1M-token USD rates for ``model`` from merged pricing.

    Raises:
        LlmGuardRefusal: ``model`` is absent from the merged table (refuse unpriced calls).
        ValueError: ``budget_config.model_pricing`` or an entry is malformed.
    """
    table = merged_model_pricing_table(budget_config)
    key = model.strip()
    if key not in table:
        raise LlmGuardRefusal(
            "no_pricing",
            "Refusing LLM call: no pricing for model "
            f"{key!r}; add budget.model_pricing[{key!r}] or use a model in the "
            "built-in pricing registry",
        )
    row = table[key]
    return row["input_cost_per_1m_tokens"], row["output_cost_per_1m_tokens"]


LLM_KILL_SWITCH_FILENAME = ".llm_kill_switch"


def kill_switch_active(root: Path | None = None) -> bool:
    """Return True if ``.llm_kill_switch`` exists under ``root`` (default: cwd)."""
    base = root if root is not None else Path.cwd()
    return (base / LLM_KILL_SWITCH_FILENAME).exists()


def assert_real_llm_armed() -> None:
    """Require explicit env arming before real (non-dry-run) LLM calls."""
    if os.getenv("ALLOW_REAL_LLM_CALLS", "").strip().lower() != "true":
        raise LlmGuardRefusal(
            "real_llm_not_armed",
            "Real LLM calls are not armed (set environment ALLOW_REAL_LLM_CALLS=true)",
        )


def validate_prompt_for_llm(prompt_text: str, budget_config: dict) -> None:
    """
    Reject prompts that are oversized, leak key-like material, or carry huge blobs.
    Fail-closed for citation pipelines that should send chunks, not full dumps.
    """
    if not isinstance(prompt_text, str):
        raise TypeError("prompt_text must be a string")

    max_chars = budget_config.get("max_prompt_chars")
    if not isinstance(max_chars, int) or max_chars <= 0:
        raise ValueError("budget_config.max_prompt_chars must be a positive integer")

    if len(prompt_text) > max_chars:
        raise LlmGuardRefusal(
            "prompt_exceeds_max_chars",
            f"prompt exceeds max_prompt_chars ({max_chars}); refusing LLM call",
        )

    if budget_config.get("reject_prompt_api_key_like_strings", True):
        if re.search(r"sk-[a-zA-Z0-9]{16,}", prompt_text):
            raise LlmGuardRefusal(
                "prompt_contains_api_key_like_string",
                "prompt appears to contain an API-key-like substring; refusing LLM call",
            )

    max_blob = budget_config.get("max_base64_like_line_chars", 4000)
    if isinstance(max_blob, int) and max_blob > 0:
        for line in prompt_text.splitlines():
            stripped = line.strip()
            if len(stripped) >= max_blob and re.fullmatch(
                r"[A-Za-z0-9+/=\s]+", stripped
            ):
                raise LlmGuardRefusal(
                    "prompt_contains_long_base64_line",
                    "prompt contains a very long base64-like line; refusing LLM call",
                )

    for needle in budget_config.get("reject_prompt_substrings", []) or []:
        if isinstance(needle, str) and needle and needle in prompt_text:
            raise LlmGuardRefusal(
                "prompt_contains_forbidden_substring",
                f"prompt contains forbidden substring {needle!r}; refusing LLM call",
            )


def assert_llm_call_allowed(
    prompt_text: str,
    expected_output_tokens: int,
    budget_config: dict,
    state: CostGuardState,
    *,
    model: str | None = None,
    kill_switch_root: Path | None = None,
) -> dict:
    """
    Validate whether a future LLM call is allowed under run, day, and month budgets.

    Per-token pricing is taken only from ``budget_config["model_pricing"]`` merged with
    built-in defaults (:data:`BUILTIN_MODEL_PRICING`), keyed by ``model``.

    Call **before** any vendor I/O. Requires explicit env arming for real calls.

    Raises:
        LlmGuardRefusal: Policy / budget / kill-switch / prompt rejection (subclass of
            ``PermissionError`` with ``reason_code``).
        ValueError: Invalid configuration or token counts.
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
        "max_estimated_cost_usd_per_day",
        "max_estimated_cost_usd_per_month",
        "max_estimated_cost_usd_per_call",
        "allowed_models",
        "model_pricing",
        "max_prompt_chars",
        "max_llm_retries_per_call",
        "budget_persistence_dir",
        "fail_closed",
    ]

    missing_keys = [key for key in required_keys if key not in budget_config]

    if missing_keys:
        raise ValueError(f"budget_config missing required keys: {missing_keys}")

    if budget_config.get("fail_closed", True) is not True:
        raise ValueError("fail_closed must be true for safety")

    if kill_switch_active(kill_switch_root):
        raise LlmGuardRefusal(
            "kill_switch_active",
            "LLM kill switch is active (.llm_kill_switch present)",
        )

    if not budget_config["llm_enabled"]:
        raise LlmGuardRefusal("llm_disabled", "LLM calls are disabled by config")

    validate_prompt_for_llm(prompt_text, budget_config)

    if expected_output_tokens <= 0:
        raise ValueError("expected_output_tokens must be greater than zero")

    allowed_raw = budget_config["allowed_models"]
    if not isinstance(allowed_raw, list) or not all(
        isinstance(x, str) for x in allowed_raw
    ):
        raise ValueError("allowed_models must be a list of strings")

    allowed_norm = [x.strip() for x in allowed_raw if x.strip()]
    if not allowed_norm:
        raise LlmGuardRefusal(
            "allowed_models_empty",
            "allowed_models is empty; no LLM model is permitted",
        )

    if model is None or not str(model).strip():
        raise LlmGuardRefusal(
            "model_required",
            "model is required and must be a non-empty string",
        )

    model_clean = model.strip()
    if model_clean not in allowed_norm:
        raise LlmGuardRefusal(
            "model_not_allowed",
            f"Model not allowed: {model_clean}",
        )

    in_price, out_price = resolve_model_pricing_for_call(model_clean, budget_config)

    input_tokens = estimate_tokens(prompt_text)
    output_tokens = expected_output_tokens

    estimated_call_cost = estimate_llm_cost_usd(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        input_cost_per_1m_tokens=in_price,
        output_cost_per_1m_tokens=out_price,
    )

    if estimated_call_cost > budget_config["max_estimated_cost_usd_per_call"]:
        raise LlmGuardRefusal(
            "per_call_cost_exceeded",
            "LLM estimated cost limit exceeded for this call "
            f"({estimated_call_cost:.6f} > "
            f"{budget_config['max_estimated_cost_usd_per_call']})",
        )

    persistence_dir = budget_config.get("budget_persistence_dir") or ""
    will_attempt_real = (
        bool(budget_config["llm_enabled"]) and not bool(budget_config["dry_run"])
    )

    if (
        will_attempt_real
        and isinstance(persistence_dir, str)
        and persistence_dir.strip()
    ):
        daily = load_daily_spend_usd(persistence_dir)
        monthly = load_monthly_spend_usd(persistence_dir)
        day_cap = float(budget_config["max_estimated_cost_usd_per_day"])
        month_cap = float(budget_config["max_estimated_cost_usd_per_month"])
        if daily + estimated_call_cost > day_cap:
            raise LlmGuardRefusal(
                "daily_cost_cap_exceeded",
                "LLM estimated daily cost limit exceeded for this call",
            )
        if monthly + estimated_call_cost > month_cap:
            raise LlmGuardRefusal(
                "monthly_cost_cap_exceeded",
                "LLM estimated monthly cost limit exceeded for this call",
            )

    projected_call_count = state.llm_call_count + 1
    projected_total_tokens = (
        state.total_input_tokens
        + state.total_output_tokens
        + input_tokens
        + output_tokens
    )
    projected_cost = state.total_estimated_cost_usd + estimated_call_cost

    if projected_call_count > budget_config["max_llm_calls_per_run"]:
        raise LlmGuardRefusal(
            "max_calls_per_run_exceeded",
            "LLM call limit exceeded for this run",
        )

    if input_tokens > budget_config["max_input_tokens_per_call"]:
        raise LlmGuardRefusal(
            "input_tokens_per_call_exceeded",
            "LLM input token limit exceeded for this call",
        )

    if output_tokens > budget_config["max_output_tokens_per_call"]:
        raise LlmGuardRefusal(
            "output_tokens_per_call_exceeded",
            "LLM output token limit exceeded for this call",
        )

    if projected_total_tokens > budget_config["max_total_tokens_per_run"]:
        raise LlmGuardRefusal(
            "total_tokens_per_run_exceeded",
            "LLM total token limit exceeded for this run",
        )

    if projected_cost > budget_config["max_estimated_cost_usd_per_run"]:
        raise LlmGuardRefusal(
            "run_cost_cap_exceeded",
            "LLM estimated cost limit exceeded for this run",
        )

    if budget_config["dry_run"]:
        raise LlmGuardRefusal(
            "dry_run_enabled",
            "LLM dry_run is enabled; refusing real API call",
        )

    assert_real_llm_armed()

    return {
        "allowed": True,
        "input_tokens": input_tokens,
        "expected_output_tokens": output_tokens,
        "estimated_call_cost_usd": estimated_call_cost,
        "projected_call_count": projected_call_count,
        "projected_total_tokens": projected_total_tokens,
        "projected_cost_usd": projected_cost,
        "model": model_clean,
    }


def record_llm_usage(
    state: CostGuardState,
    input_tokens: int,
    output_tokens: int,
    estimated_cost_usd: float,
) -> CostGuardState:
    """
    Update cost guard state after a successful LLM call.

    Prefer **actual** ``input_tokens``, ``output_tokens``, and cost (USD) from
    the vendor response when available. The parameter name ``estimated_cost_usd``
    is historical; real integrations should pass billed or usage-derived cost
    here—not pre-call guesses alone.
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