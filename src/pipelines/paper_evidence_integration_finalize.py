"""
Merge Week 4 steelman + Week 5 evidence rows into Week 7 integration JSON for paper assembly.

``build_paper_spec`` reads ``speaker_perspective`` / ``steelman`` and ``evidence_records`` from
the integration document; the core integration pipeline only writes adjudications by default.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.integration.integration_limitations import apply_integration_limitations


def enrich_evidence_records_for_paper(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Paper spec requires ``evidence_id`` on each record; Week 5 rows may omit it."""
    out: list[dict[str, Any]] = []
    for idx, raw in enumerate(records):
        row = dict(raw)
        eid = row.get("evidence_id")
        if not isinstance(eid, str) or not eid.strip():
            ident = row.get("identifier")
            if isinstance(ident, str) and ident.strip():
                row["evidence_id"] = ident.strip()
            else:
                row["evidence_id"] = f"evidence_{idx:06d}"
        out.append(row)
    return out


def finalize_evidence_integration_json_for_paper(
    *,
    integration_path: Path,
    speaker_perspective_path: Path,
    evidence_records_path: Path,
) -> None:
    """Augment integration JSON with steelman narrative blocks and flat evidence records."""
    integration_payload = json.loads(integration_path.read_text(encoding="utf-8"))

    steelman_doc = json.loads(speaker_perspective_path.read_text(encoding="utf-8"))
    integration_payload["steelman"] = {
        "narrative_blocks": steelman_doc.get("narrative_blocks", []),
    }

    flat_raw = json.loads(evidence_records_path.read_text(encoding="utf-8"))
    if not isinstance(flat_raw, list):
        raise ValueError("evidence_records.json must contain a JSON list.")

    integration_payload["evidence_records"] = enrich_evidence_records_for_paper(flat_raw)

    apply_integration_limitations(integration_payload)

    integration_path.write_text(
        json.dumps(integration_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
