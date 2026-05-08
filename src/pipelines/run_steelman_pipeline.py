"""
Week 4: persist Speaker's Perspective (steelman) artifact next to Week 3 inventory.

Reads ``claim_inventory.json`` and Week 2 ``argument_map.json``, runs
:func:`build_steelman_section`, writes ``data/processed/speaker_perspective.json``
(or configured path).

When ``use_llm`` is true, attempts :func:`src.ops.llm_client.safe_llm_call` with
``build_steelman_prompt`` / ``parse_steelman_prompt_response`` and falls back to
conservative output on any failure.

CLI: ``python -m src.pipelines.run_steelman_pipeline``
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

from src.core.config import load_config
from src.ops.cost_guard import CostGuardState
from src.ops.llm_client import gemini_rest_llm_callable, safe_llm_call
from src.ops.run_tracker import (
    create_run_log,
    finish_run_log,
    record_error,
    record_metric,
    save_run_log,
)
from src.pipelines.claim_inventory_pipeline import (
    DEFAULT_ARGUMENT_MAP_PATH,
    DEFAULT_CLAIM_INVENTORY_PATH,
    _resolve_week2_input_path,
    _resolved_claim_inventory_settings,
    load_argument_map_document,
)
from src.pipelines.steelman_prompt import (
    build_steelman_prompt,
    parse_steelman_prompt_response,
)
from src.pipelines.steelman_pipeline import build_steelman_section

DEFAULT_SPEAKER_PERSPECTIVE_PATH = Path("data/processed/speaker_perspective.json")

DEFAULT_SPEAKER_LLM_SETTINGS = {
    "model": "gpt-4o-mini",
    "max_output_tokens": 900,
    "max_claims_per_call": 12,
    "fallback_on_guard_rejection": True,
}


def _speaker_perspective_settings(config: dict[str, Any]) -> dict[str, Any]:
    """Defaults when ``speaker_perspective`` is missing from argument config."""
    defaults = {
        "enabled": True,
        "output_path": str(DEFAULT_SPEAKER_PERSPECTIVE_PATH),
        "use_llm": False,
        "llm": dict(DEFAULT_SPEAKER_LLM_SETTINGS),
    }

    section = config.get("speaker_perspective")
    if not isinstance(section, dict):
        return defaults

    out = {
        "enabled": defaults["enabled"],
        "output_path": defaults["output_path"],
        "use_llm": defaults["use_llm"],
        "llm": dict(defaults["llm"]),
    }

    if "enabled" in section:
        if not isinstance(section["enabled"], bool):
            raise ValueError("speaker_perspective.enabled must be a boolean")
        out["enabled"] = section["enabled"]

    if "output_path" in section:
        op = section["output_path"]
        if not isinstance(op, str) or not op.strip():
            raise ValueError("speaker_perspective.output_path must be a non-empty string")
        out["output_path"] = op.strip()

    if "use_llm" in section:
        if not isinstance(section["use_llm"], bool):
            raise ValueError("speaker_perspective.use_llm must be a boolean")
        out["use_llm"] = section["use_llm"]

    if "llm" in section:
        llm_section = section["llm"]
        if not isinstance(llm_section, dict):
            raise ValueError("speaker_perspective.llm must be an object")

        allowed_llm_keys = {
            "provider",
            "model",
            "max_output_tokens",
            "max_claims_per_call",
            "fallback_on_guard_rejection",
        }

        extra_llm = set(llm_section.keys()) - allowed_llm_keys
        if extra_llm:
            raise ValueError(
                f"speaker_perspective.llm unknown keys: {sorted(extra_llm)}"
            )

        if "provider" in llm_section:
            provider = llm_section["provider"]
            if not isinstance(provider, str) or not provider.strip():
                raise ValueError(
                    "speaker_perspective.llm.provider must be a non-empty string"
                )
            out["llm"]["provider"] = provider.strip()

        if "model" in llm_section:
            model = llm_section["model"]
            if not isinstance(model, str) or not model.strip():
                raise ValueError("speaker_perspective.llm.model must be a non-empty string")
            out["llm"]["model"] = model.strip()

        if "max_output_tokens" in llm_section:
            max_output_tokens = llm_section["max_output_tokens"]
            if not isinstance(max_output_tokens, int) or max_output_tokens <= 0:
                raise ValueError(
                    "speaker_perspective.llm.max_output_tokens must be a positive integer"
                )
            out["llm"]["max_output_tokens"] = max_output_tokens

        if "max_claims_per_call" in llm_section:
            max_claims_per_call = llm_section["max_claims_per_call"]
            if not isinstance(max_claims_per_call, int) or max_claims_per_call <= 0:
                raise ValueError(
                    "speaker_perspective.llm.max_claims_per_call must be a positive integer"
                )
            out["llm"]["max_claims_per_call"] = max_claims_per_call

        if "fallback_on_guard_rejection" in llm_section:
            fallback = llm_section["fallback_on_guard_rejection"]
            if not isinstance(fallback, bool):
                raise ValueError(
                    "speaker_perspective.llm.fallback_on_guard_rejection must be a boolean"
                )
            out["llm"]["fallback_on_guard_rejection"] = fallback

    extra = set(section.keys()) - {
        "enabled",
        "output_path",
        "use_llm",
        "llm",
    }

    if extra:
        raise ValueError(f"speaker_perspective unknown keys: {sorted(extra)}")

    return out


def _steelman_llm_payload_placeholder(
    *,
    use_llm: bool,
    llm_requested: bool,
    llm_executed: bool,
) -> dict[str, Any]:
    """Artifact mirror of logged LLM posture."""
    return {
        "use_llm": use_llm,
        "llm_requested": llm_requested,
        "llm_executed": llm_executed,
    }


def _record_llm_fallback_state(
    run_log: dict[str, Any],
    *,
    attempted: bool,
    used: bool,
    fallback_used: bool,
    fallback_reason: str,
) -> None:
    """Distinguish LLM success, fallback, and ``use_llm: false`` in monitors."""
    record_metric(run_log, "llm_mode_attempted", attempted)
    record_metric(run_log, "llm_mode_used", used)
    record_metric(run_log, "fallback_used", fallback_used)
    record_metric(run_log, "fallback_reason", fallback_reason)


def _steelman_llm_vendor_not_configured(**kwargs: Any) -> dict[str, Any]:
    raise RuntimeError("Steelman LLM vendor callable is not configured")


def _response_text_from_llm_result(response: Any) -> str:
    if isinstance(response, str):
        return response
    if isinstance(response, dict):
        text = response.get("text")
        return text if isinstance(text, str) else ""
    return ""


def _build_steelman_section_with_guarded_llm(
    *,
    claim_inventory: list[dict[str, Any]],
    argument_map: dict[str, Any],
    llm_settings: dict[str, Any],
    budget_config: dict[str, Any],
    ledger_context: dict[str, Any],
    llm_callable: Callable[..., dict] | None,
) -> tuple[dict[str, Any], str]:
    """
    Attempt LLM-assisted steelmanning through :func:`safe_llm_call` only.

    Returns ``(section, fallback_reason)``. ``fallback_reason`` is ``\"\"`` when
    the LLM path produces a passing section.
    """
    conservative = build_steelman_section(
        claim_inventory=claim_inventory,
        argument_map=argument_map,
    )

    if not budget_config:
        return conservative, "missing_budget_config"

    prompt = build_steelman_prompt(
        claim_inventory=claim_inventory,
        argument_map=argument_map,
        max_claims=llm_settings["max_claims_per_call"],
    )

    vendor = llm_callable if llm_callable is not None else _steelman_llm_vendor_not_configured

    try:
        response = safe_llm_call(
            prompt_text=prompt,
            expected_output_tokens=int(llm_settings["max_output_tokens"]),
            budget_config=budget_config,
            state=CostGuardState(),
            llm_callable=vendor,
            model=llm_settings["model"],
            ledger_context=ledger_context,
        )
    except Exception:
        return conservative, "llm_call_failed"

    response_text = _response_text_from_llm_result(response)
    try:
        drafted_blocks = parse_steelman_prompt_response(response_text)
    except ValueError:
        return conservative, "llm_response_parse_failed"

    section = build_steelman_section(
        claim_inventory=claim_inventory,
        argument_map=argument_map,
        drafted_blocks=drafted_blocks,
    )

    if section["self_recognition_check"] != "passed":
        return conservative, "llm_response_validation_failed"

    return section, ""


def _resolve_claim_inventory_input_path(
    full_config: dict[str, Any],
    explicit: str | Path | None,
) -> Path:
    if explicit is not None:
        return Path(explicit)
    ci = _resolved_claim_inventory_settings(full_config, DEFAULT_CLAIM_INVENTORY_PATH)
    return Path(ci["output_path"])


def _load_claim_inventory_claims(claim_inventory_path: Path) -> list[dict[str, Any]]:
    if not claim_inventory_path.is_file():
        raise FileNotFoundError(f"claim inventory not found: {claim_inventory_path}")

    data = json.loads(claim_inventory_path.read_text(encoding="utf-8"))
    claims = data.get("claims")
    if not isinstance(claims, list):
        raise ValueError("claim_inventory payload must contain a list field 'claims'")

    return claims


def _resolve_steelman_vendor_callable(
    sp: dict[str, Any],
    explicit: Callable[..., dict] | None,
) -> Callable[..., dict] | None:
    """
    Pick a vendor ``llm_callable`` for steelman when not injected (tests pass explicit).

    ``provider: gemini`` uses :func:`src.ops.llm_client.gemini_rest_llm_callable`
    (requires ``GEMINI_API_KEY`` or ``GOOGLE_API_KEY``).
    """
    if explicit is not None:
        return explicit
    if not sp.get("use_llm"):
        return None
    llm = sp.get("llm")
    if not isinstance(llm, dict):
        return None
    provider = str(llm.get("provider", "")).strip().lower()
    if provider == "gemini":
        return gemini_rest_llm_callable
    return None


def run_steelman_pipeline(
    *,
    config_path: str | Path = Path("configs/argument_config.json"),
    claim_inventory_path: str | Path | None = None,
    argument_map_path: str | Path | None = None,
    output_path: str | Path | None = None,
    logs_dir: str | Path = Path("logs/runs"),
    llm_callable: Callable[..., dict] | None = None,
) -> Path:
    """
    Build and save ``speaker_perspective.json``.

    Input paths default from the same ``argument_config.json`` as Week 3:
    ``claim_inventory.output_path`` and ``output_paths.argument_map``.

    Optional ``llm_callable`` is passed through to :func:`safe_llm_call` (vendor
    shim). When omitted, a stub raises unless ``safe_llm_call`` is mocked in tests.
    """
    config_p = Path(config_path)
    full_config = load_config(config_p)

    sp = _speaker_perspective_settings(full_config)
    output_path_p = Path(output_path) if output_path is not None else Path(sp["output_path"])

    claim_resolved = _resolve_claim_inventory_input_path(
        full_config,
        claim_inventory_path,
    )
    argument_resolved = _resolve_week2_input_path(
        full_config,
        output_paths_key="argument_map",
        explicit=argument_map_path,
        fallback=DEFAULT_ARGUMENT_MAP_PATH,
    )

    claim_resolved_s = str(claim_resolved)
    argument_resolved_s = str(argument_resolved)

    run_log = create_run_log(
        config_path=str(config_p),
        input_path=claim_resolved_s,
        output_path=str(output_path_p),
        pipeline_name="speaker_perspective",
    )
    run_log["input_paths"] = {
        "claim_inventory": claim_resolved_s,
        "argument_map": argument_resolved_s,
    }

    record_metric(run_log, "speaker_perspective_enabled", sp["enabled"])
    record_metric(run_log, "speaker_perspective_use_llm", sp["use_llm"])
    record_metric(run_log, "speaker_perspective_llm_model", sp["llm"]["model"])
    record_metric(
        run_log,
        "speaker_perspective_llm_max_output_tokens",
        sp["llm"]["max_output_tokens"],
    )
    record_metric(
        run_log,
        "speaker_perspective_llm_max_claims_per_call",
        sp["llm"]["max_claims_per_call"],
    )

    try:
        if not sp["enabled"]:
            payload_disabled = {
                "stage": "speaker_perspective",
                "enabled": False,
                "input_paths": run_log["input_paths"],
                "steelman_llm": _steelman_llm_payload_placeholder(
                    use_llm=sp["use_llm"],
                    llm_requested=False,
                    llm_executed=False,
                ),
                "section_title": "",
                "narrative_blocks": [],
                "qualifications_preserved": [],
                "self_recognition_check": "failed",
            }
            output_path_p.parent.mkdir(parents=True, exist_ok=True)
            output_path_p.write_text(
                json.dumps(payload_disabled, indent=2),
                encoding="utf-8",
            )
            record_metric(run_log, "speaker_perspective_llm_requested", False)
            record_metric(run_log, "speaker_perspective_llm_executed", False)
            _record_llm_fallback_state(
                run_log,
                attempted=False,
                used=False,
                fallback_used=False,
                fallback_reason="",
            )
            record_metric(run_log, "claim_count", 0)
            record_metric(run_log, "narrative_block_count", 0)
            finish_run_log(run_log, status="success")
            save_run_log(run_log, str(Path(logs_dir)))
            return output_path_p

        claims = _load_claim_inventory_claims(claim_resolved)
        argument_inner = load_argument_map_document(argument_resolved)

        resolved_llm_callable = _resolve_steelman_vendor_callable(sp, llm_callable)

        if sp["use_llm"]:
            record_metric(run_log, "speaker_perspective_llm_requested", True)
            budget_cfg = full_config.get("budget")
            budget_dict = budget_cfg if isinstance(budget_cfg, dict) else {}

            section, fallback_reason = _build_steelman_section_with_guarded_llm(
                claim_inventory=claims,
                argument_map=argument_inner,
                llm_settings=sp["llm"],
                budget_config=budget_dict,
                ledger_context={
                    "run_id": run_log["run_id"],
                    "pipeline_name": run_log["pipeline_name"],
                },
                llm_callable=resolved_llm_callable,
            )
            llm_used = fallback_reason == ""
            record_metric(run_log, "speaker_perspective_llm_executed", llm_used)
            llm_requested = True
            _record_llm_fallback_state(
                run_log,
                attempted=True,
                used=llm_used,
                fallback_used=fallback_reason != "",
                fallback_reason=fallback_reason,
            )
        else:
            record_metric(run_log, "speaker_perspective_llm_requested", False)
            record_metric(run_log, "speaker_perspective_llm_executed", False)

            section = build_steelman_section(
                claim_inventory=claims,
                argument_map=argument_inner,
            )
            llm_requested = False
            fallback_reason = ""
            _record_llm_fallback_state(
                run_log,
                attempted=False,
                used=False,
                fallback_used=False,
                fallback_reason="",
            )

        llm_executed = bool(sp["use_llm"] and fallback_reason == "")

        payload = {
            "stage": "speaker_perspective",
            "enabled": True,
            "input_paths": run_log["input_paths"],
            "claim_count": len(claims),
            "steelman_llm": _steelman_llm_payload_placeholder(
                use_llm=sp["use_llm"],
                llm_requested=llm_requested,
                llm_executed=llm_executed,
            ),
            **section,
        }

        output_path_p.parent.mkdir(parents=True, exist_ok=True)
        output_path_p.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        record_metric(run_log, "claim_count", len(claims))
        record_metric(
            run_log,
            "narrative_block_count",
            len(section["narrative_blocks"]),
        )
        finish_run_log(run_log, status="success")

    except Exception as error:
        record_error(run_log, str(error))
        finish_run_log(run_log, status="failed")
        save_run_log(run_log, str(Path(logs_dir)))
        raise

    save_run_log(run_log, str(Path(logs_dir)))
    return output_path_p


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Week 4 (steelman): build speaker_perspective.json from claim_inventory "
            "and argument_map."
        ),
    )
    parser.add_argument(
        "--config-path",
        default="configs/argument_config.json",
        help="Argument-structure JSON (Week 2 paths + optional speaker_perspective block).",
    )
    parser.add_argument(
        "--claim-inventory-path",
        default=None,
        help=(
            "claim_inventory.json from Week 3. Default: claim_inventory.output_path "
            "in config."
        ),
    )
    parser.add_argument(
        "--argument-map-path",
        default=None,
        help=(
            "argument_map.json from Week 2. Default: output_paths.argument_map in config."
        ),
    )
    parser.add_argument(
        "--output-path",
        default=None,
        help=(
            "speaker_perspective.json output. Default: speaker_perspective.output_path "
            "in config."
        ),
    )
    parser.add_argument("--logs-dir", default="logs/runs")

    args = parser.parse_args(argv)

    claim_inventory = Path(args.claim_inventory_path) if args.claim_inventory_path else None
    argument_map = Path(args.argument_map_path) if args.argument_map_path else None
    out = Path(args.output_path) if args.output_path else None

    written = run_steelman_pipeline(
        config_path=args.config_path,
        claim_inventory_path=claim_inventory,
        argument_map_path=argument_map,
        output_path=out,
        logs_dir=args.logs_dir,
    )

    print(f"Speaker perspective written to: {written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
