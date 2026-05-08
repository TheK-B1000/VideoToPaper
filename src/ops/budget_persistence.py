"""
Persistent LLM spend totals per calendar day and month (cross-run caps).

Files (under ``budget_persistence_dir``):

- ``daily_usage_YYYY-MM-DD.json``
- ``monthly_usage_YYYY-MM.json``
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


def _utc_date() -> date:
    return datetime.now(timezone.utc).date()


def _daily_filename(d: date) -> str:
    return f"daily_usage_{d.isoformat()}.json"


def _monthly_filename(year: int, month: int) -> str:
    return f"monthly_usage_{year:04d}-{month:02d}.json"


def _read_usage(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"total_cost_usd": 0.0}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"total_cost_usd": 0.0}
    total = data.get("total_cost_usd")
    if isinstance(total, (int, float)):
        return {"total_cost_usd": float(total)}
    return {"total_cost_usd": 0.0}


def load_daily_spend_usd(budget_dir: str | Path, *, on_date: date | None = None) -> float:
    """Sum of recorded USD spend for UTC calendar day."""
    d = on_date or _utc_date()
    path = Path(budget_dir) / _daily_filename(d)
    return float(_read_usage(path)["total_cost_usd"])


def load_monthly_spend_usd(budget_dir: str | Path, *, on_date: date | None = None) -> float:
    """Sum of recorded USD spend for UTC calendar month."""
    d = on_date or _utc_date()
    path = Path(budget_dir) / _monthly_filename(d.year, d.month)
    return float(_read_usage(path)["total_cost_usd"])


def record_spend_usd(budget_dir: str | Path, cost_usd: float) -> None:
    """
    Add ``cost_usd`` to today's daily file and this month's monthly file.

    Uses estimated or actual post-call cost from the ledger path.
    """
    if cost_usd <= 0:
        return

    d = _utc_date()
    root = Path(budget_dir)
    root.mkdir(parents=True, exist_ok=True)

    now_iso = datetime.now(timezone.utc).isoformat()

    daily_path = root / _daily_filename(d)
    daily = _read_usage(daily_path)
    daily["period"] = d.isoformat()
    daily["total_cost_usd"] = float(daily["total_cost_usd"]) + float(cost_usd)
    daily["updated_at"] = now_iso
    daily_path.write_text(json.dumps(daily, indent=2), encoding="utf-8")

    monthly_path = root / _monthly_filename(d.year, d.month)
    monthly = _read_usage(monthly_path)
    monthly["period"] = f"{d.year:04d}-{d.month:02d}"
    monthly["total_cost_usd"] = float(monthly["total_cost_usd"]) + float(cost_usd)
    monthly["updated_at"] = now_iso
    monthly_path.write_text(json.dumps(monthly, indent=2), encoding="utf-8")
