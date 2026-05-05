from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Callable

from src.ops.budget_ledger import append_llm_ledger_entry
from src.ops.budget_persistence import record_spend_usd
from src.ops.cost_guard import (
    CostGuardState,
    LlmGuardRefusal,
    assert_llm_call_allowed,
    estimate_tokens,
    record_llm_usage,
)


def _resolve_gemini_api_key() -> str:
    for env_name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        key = os.environ.get(env_name, "").strip()
        if key:
            return key
    raise RuntimeError(
        "Set GEMINI_API_KEY or GOOGLE_API_KEY for speaker_perspective with "
        "provider=gemini (vendor runs only inside safe_llm_call)."
    )


def gemini_rest_llm_callable(
    *,
    prompt_text: str,
    expected_output_tokens: int,
    model: str,
    **_: Any,
) -> dict[str, Any]:
    """
    Gemini ``generateContent`` via REST (stdlib only). Intended for steelman smoke
    tests and small calls; must only be invoked through :func:`safe_llm_call`.
    """
    api_key = _resolve_gemini_api_key()
    model_id = urllib.parse.quote(model, safe="")
    query = urllib.parse.urlencode({"key": api_key})
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model_id}:generateContent?{query}"
    )
    payload: dict[str, Any] = {
        "contents": [{"parts": [{"text": prompt_text}]}],
        "generationConfig": {
            "maxOutputTokens": int(expected_output_tokens),
            "temperature": 0.0,
        },
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini HTTP {exc.code}: {detail}") from exc

    candidates = raw.get("candidates") or []
    text_chunks: list[str] = []
    for cand in candidates:
        content = cand.get("content") or {}
        for part in content.get("parts") or []:
            t = part.get("text")
            if isinstance(t, str):
                text_chunks.append(t)
    text_out = "".join(text_chunks).strip()
    if not text_out:
        raise RuntimeError(f"Gemini returned empty text: {raw!r}")

    usage_meta = raw.get("usageMetadata") or {}
    in_tok = int(usage_meta.get("promptTokenCount") or 0)
    out_tok = int(usage_meta.get("candidatesTokenCount") or 0)

    return {
        "text": text_out,
        "usage": {
            "input_tokens": in_tok if in_tok > 0 else None,
            "output_tokens": out_tok if out_tok > 0 else None,
            "cost_usd": 0.0,
        },
    }


def safe_llm_call(
    prompt_text: str,
    expected_output_tokens: int,
    budget_config: dict,
    state: CostGuardState,
    llm_callable: Callable[..., dict],
    *,
    model: str,
    ledger_context: dict[str, Any] | None = None,
    **llm_kwargs: Any,
) -> dict:
    """
    Safely perform an LLM call using the required gateway order:

    1. Validate prompt / budgets via ``assert_llm_call_allowed`` before external I/O.
    2. Invoke vendor/API through ``llm_callable`` with retries confined inside here.
    3. Record usage and persist daily/monthly spend (actual cost when provided).

    Retries wrap **only** ``llm_callable``, not the guard or accounting.

    The llm_callable is injected so tests can stub the vendor.
    """
    if expected_output_tokens <= 0:
        raise ValueError("expected_output_tokens must be greater than zero")

    ctx = ledger_context or {}
    ledger_dir_raw = budget_config.get("budget_persistence_dir") or ""
    ledger_dir = ledger_dir_raw.strip() if isinstance(ledger_dir_raw, str) else ""

    ts = datetime.now(timezone.utc).isoformat()

    try:
        preflight = assert_llm_call_allowed(
            prompt_text=prompt_text,
            expected_output_tokens=expected_output_tokens,
            budget_config=budget_config,
            state=state,
            model=model,
        )
    except PermissionError as exc:
        # permission_denied is the fallback bucket: a PermissionError reached the
        # ledger without a reason_code attached. Post-LlmGuardRefusal refactor this
        # should be unreachable from assert_llm_call_allowed; if it appears in logs,
        # investigate why a plain PermissionError is being raised somewhere upstream.
        guard_reason_code = (
            exc.reason_code if isinstance(exc, LlmGuardRefusal) else "permission_denied"
        )
        if ledger_dir:
            append_llm_ledger_entry(
                ledger_dir,
                {
                    "run_id": ctx.get("run_id"),
                    "timestamp": ts,
                    "pipeline_name": ctx.get("pipeline_name"),
                    "model": model,
                    "input_token_estimate": estimate_tokens(prompt_text),
                    "expected_output_tokens": expected_output_tokens,
                    "estimated_cost_usd": None,
                    "allowed": False,
                    "guard_reason_code": guard_reason_code,
                    "reason": str(exc),
                    "actual_input_tokens": None,
                    "actual_output_tokens": None,
                    "actual_cost_usd": None,
                },
            )
        raise

    max_retries = int(budget_config["max_llm_retries_per_call"])
    total_attempts = 1 + max(0, max_retries)

    last_error: BaseException | None = None
    response: dict | None = None

    for attempt in range(total_attempts):
        try:
            response = llm_callable(
                prompt_text=prompt_text,
                expected_output_tokens=expected_output_tokens,
                model=model,
                **llm_kwargs,
            )
            break
        except BaseException as exc:
            last_error = exc
            if attempt >= total_attempts - 1:
                if ledger_dir:
                    append_llm_ledger_entry(
                        ledger_dir,
                        {
                            "run_id": ctx.get("run_id"),
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "pipeline_name": ctx.get("pipeline_name"),
                            "model": model,
                            "input_token_estimate": preflight["input_tokens"],
                            "expected_output_tokens": expected_output_tokens,
                            "estimated_cost_usd": preflight[
                                "estimated_call_cost_usd"
                            ],
                            "allowed": True,
                            "reason": f"vendor_failure_after_{total_attempts}_attempts",
                            "actual_input_tokens": None,
                            "actual_output_tokens": None,
                            "actual_cost_usd": None,
                        },
                    )
                raise last_error

    assert response is not None

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

    if ledger_dir:
        record_spend_usd(ledger_dir, float(actual_cost_usd))
        append_llm_ledger_entry(
            ledger_dir,
            {
                "run_id": ctx.get("run_id"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "pipeline_name": ctx.get("pipeline_name"),
                "model": model,
                "input_token_estimate": preflight["input_tokens"],
                "expected_output_tokens": expected_output_tokens,
                "estimated_cost_usd": preflight["estimated_call_cost_usd"],
                "allowed": True,
                "reason": None,
                "actual_input_tokens": actual_input_tokens,
                "actual_output_tokens": actual_output_tokens,
                "actual_cost_usd": actual_cost_usd,
            },
        )

    return response
