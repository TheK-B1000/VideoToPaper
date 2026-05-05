"""
Week 4: persist Speaker's Perspective (steelman) artifact next to Week 3 inventory.

Reads ``claim_inventory.json`` and Week 2 ``argument_map.json``, runs
:func:`build_steelman_section`, writes ``data/processed/speaker_perspective.json``
(or configured path).

CLI: ``python -m src.pipelines.run_steelman_pipeline``
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.core.config import load_config
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
from src.pipelines.steelman_pipeline import build_steelman_section

DEFAULT_SPEAKER_PERSPECTIVE_PATH = Path("data/processed/speaker_perspective.json")


def _speaker_perspective_settings(config: dict[str, Any]) -> dict[str, Any]:
    """Defaults when ``speaker_perspective`` is missing from argument config."""
    defaults = {
        "enabled": True,
        "output_path": str(DEFAULT_SPEAKER_PERSPECTIVE_PATH),
    }
    section = config.get("speaker_perspective")
    if not isinstance(section, dict):
        return defaults

    out = dict(defaults)
    if "enabled" in section:
        if not isinstance(section["enabled"], bool):
            raise ValueError("speaker_perspective.enabled must be a boolean")
        out["enabled"] = section["enabled"]

    if "output_path" in section:
        op = section["output_path"]
        if not isinstance(op, str) or not op.strip():
            raise ValueError("speaker_perspective.output_path must be a non-empty string")
        out["output_path"] = op.strip()

    extra = set(section.keys()) - {"enabled", "output_path"}
    if extra:
        raise ValueError(f"speaker_perspective unknown keys: {sorted(extra)}")

    return out


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


def run_steelman_pipeline(
    *,
    config_path: str | Path = Path("configs/argument_config.json"),
    claim_inventory_path: str | Path | None = None,
    argument_map_path: str | Path | None = None,
    output_path: str | Path | None = None,
    logs_dir: str | Path = Path("logs/runs"),
) -> Path:
    """
    Build and save ``speaker_perspective.json``.

    Input paths default from the same ``argument_config.json`` as Week 3:
    ``claim_inventory.output_path`` and ``output_paths.argument_map``.
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

    try:
        if not sp["enabled"]:
            payload_disabled = {
                "stage": "speaker_perspective",
                "enabled": False,
                "input_paths": run_log["input_paths"],
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
            record_metric(run_log, "claim_count", 0)
            record_metric(run_log, "narrative_block_count", 0)
            finish_run_log(run_log, status="success")
            save_run_log(run_log, str(Path(logs_dir)))
            return output_path_p

        claims = _load_claim_inventory_claims(claim_resolved)
        argument_inner = load_argument_map_document(argument_resolved)

        section = build_steelman_section(
            claim_inventory=claims,
            argument_map=argument_inner,
        )

        payload = {
            "stage": "speaker_perspective",
            "enabled": True,
            "input_paths": run_log["input_paths"],
            "claim_count": len(claims),
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
