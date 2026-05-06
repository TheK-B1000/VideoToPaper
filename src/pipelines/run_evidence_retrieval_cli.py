from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.pipelines.run_evidence_retrieval import (
    ClaimForRetrieval,
    EvidenceRetrievalPipeline,
)


DEFAULT_CLAIM_INVENTORY_PATH = Path("data/processed/claim_inventory.json")
DEFAULT_EVIDENCE_OUTPUT_PATH = Path("data/processed/evidence_retrieval.json")


def _load_json(path: str | Path) -> dict[str, Any]:
    resolved_path = Path(path)

    if not resolved_path.exists():
        raise FileNotFoundError(f"JSON file not found: {resolved_path}")

    return json.loads(resolved_path.read_text(encoding="utf-8"))


def _extract_claims(payload: dict[str, Any]) -> list[ClaimForRetrieval]:
    """
    Supports either:
    {
      "claims": [...]
    }

    or a raw list-like claim inventory stored under:
    {
      "claim_inventory": [...]
    }
    """
    raw_claims = payload.get("claims") or payload.get("claim_inventory") or []

    claims: list[ClaimForRetrieval] = []

    for raw_claim in raw_claims:
        claim_id = raw_claim.get("claim_id") or raw_claim.get("id")
        claim_text = (
            raw_claim.get("verbatim_quote")
            or raw_claim.get("claim_text")
            or raw_claim.get("text")
        )

        claim_type = raw_claim.get("claim_type", "")
        verification_strategy = raw_claim.get("verification_strategy", "")

        claims.append(
            ClaimForRetrieval(
                claim_id=claim_id or "",
                claim_text=claim_text or "",
                claim_type=claim_type,
                verification_strategy=verification_strategy,
            )
        )

    return claims


def run_evidence_retrieval_cli(
    *,
    config_path: str | None = None,
    claim_inventory_path: str | None = None,
    output_path: str | None = None,
) -> Path:
    """
    Run Week 5 evidence retrieval from the command line.

    config_path is accepted for consistency with the other stages, but this
    first version only needs claim_inventory_path and output_path.
    """
    _ = config_path

    input_path = Path(claim_inventory_path) if claim_inventory_path else DEFAULT_CLAIM_INVENTORY_PATH
    destination = Path(output_path) if output_path else DEFAULT_EVIDENCE_OUTPUT_PATH

    payload = _load_json(input_path)
    claims = _extract_claims(payload)

    pipeline = EvidenceRetrievalPipeline()

    retrieval_results = []
    retrieval_exhausted_query_count_total = 0

    for claim in claims:
        result = pipeline.retrieve_for_claim(claim)
        retrieval_results.append(result.to_dict())
        retrieval_exhausted_query_count_total += result.retrieval_exhausted_query_count

    destination.parent.mkdir(parents=True, exist_ok=True)

    output_payload = {
        "source_claim_inventory": str(input_path),
        "retrieval_count": len(retrieval_results),
        "retrieval_exhausted_query_count_total": retrieval_exhausted_query_count_total,
        "retrieval_results": retrieval_results,
    }

    destination.write_text(
        json.dumps(output_payload, indent=2),
        encoding="utf-8",
    )

    print(f"Evidence retrieval written to: {destination}")

    return destination