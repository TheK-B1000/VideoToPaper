"""
Append-only JSONL audit log for LLM attempts (allowed and blocked).
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
