"""
Append-only JSONL audit log for LLM attempts (allowed and blocked).

Files: ``ledger_YYYY-MM-DD.jsonl`` under ``budget_persistence_dir`` (UTC calendar day).

Lines are JSON objects appended by :func:`src.ops.llm_client.safe_llm_call` (and must
stay backward-compatible for operational queries).

**Stable schema (load-bearing)**

All rows include at least:

- ``run_id``, ``timestamp``, ``pipeline_name``, ``model``
- ``input_token_estimate``, ``expected_output_tokens``, ``estimated_cost_usd``
- ``allowed`` (bool)
- ``reason`` — human-readable string, or ``null`` on successful completion
- ``actual_input_tokens``, ``actual_output_tokens``, ``actual_cost_usd``

**guard_reason_code** (guard / budget refusals only):

- **Absent** on the happy path (successful vendor response and successful ledger row).
  Queries such as ``[e for e in entries if e.get("guard_reason_code")]`` select blocked
  guard paths without picking up allowed calls.
- **Present** (non-null string) when ``allowed`` is ``False`` because the cost guard
  refused the call before vendor I/O. Values are defined alongside :class:`src.ops.cost_guard.LlmGuardRefusal`
  (e.g. ``no_pricing``, ``model_not_allowed``, ``per_call_cost_exceeded``,
  ``dry_run_enabled``). The fallback ``permission_denied`` means a plain
  ``PermissionError`` reached the ledger without ``reason_code`` — treat as an anomaly.

Pipeline **run** JSON logs (per-stage metrics, errors) live in :mod:`src.ops.run_tracker`;
they are separate artifacts from this ledger.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def append_llm_ledger_entry(budget_dir: str | Path, entry: dict[str, Any]) -> None:
    """Append one JSON object as a line to today's ledger file."""
    root = Path(budget_dir)
    root.mkdir(parents=True, exist_ok=True)

    d = datetime.now(timezone.utc).date()
    path = root / f"ledger_{d.isoformat()}.jsonl"

    line = json.dumps(entry, ensure_ascii=False) + "\n"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line)
