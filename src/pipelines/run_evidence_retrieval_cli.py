from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.core.evidence_retrieval import (
    EvidenceRecord,
    EvidenceRetrievalResult,
    generate_balanced_queries,
)
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

    or:
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


def _build_dry_run_result(claim: ClaimForRetrieval) -> EvidenceRetrievalResult:
    """
    Produce deterministic fake evidence for local development.

    This proves the CLI shape works without making live OpenAlex or Semantic
    Scholar calls.
    """
    claim.validate()

    if claim.verification_strategy != "literature_review":
        return EvidenceRetrievalResult(
            claim_id=claim.claim_id,
            queries_executed=[],
            evidence_records=[],
            balance_score="insufficient",
            query_traces=(),
            retrieval_exhausted_query_count=0,
        )

    records = [
        EvidenceRecord(
            claim_id=claim.claim_id,
            title=f"Dry-run supporting source for {claim.claim_id}",
            source="DryRun",
            tier=1,
            stance="supports",
            identifier=f"dryrun:{claim.claim_id}:supports",
            url="https://example.com/dry-run-supports",
            abstract="Deterministic dry-run supporting evidence.",
            year=2026,
        ),
        EvidenceRecord(
            claim_id=claim.claim_id,
            title=f"Dry-run qualifying source for {claim.claim_id}",
            source="DryRun",
            tier=1,
            stance="qualifies",
            identifier=f"dryrun:{claim.claim_id}:qualifies",
            url="https://example.com/dry-run-qualifies",
            abstract="Deterministic dry-run qualifying evidence.",
            year=2026,
        ),
    ]

    for record in records:
        record.validate()

    queries = generate_balanced_queries(claim.claim_text)

    return EvidenceRetrievalResult(
        claim_id=claim.claim_id,
        queries_executed=queries,
        evidence_records=records,
        balance_score="balanced",
        query_traces=(),
        retrieval_exhausted_query_count=0,
    )


def run_evidence_retrieval_cli(
    *,
    config_path: str | None = None,
    claim_inventory_path: str | None = None,
    output_path: str | None = None,
    dry_run: bool = False,
) -> Path:
    """
    Run Week 5 evidence retrieval from the command line.

    dry_run=True writes deterministic fake evidence so the stage can be tested
    without live API calls.
    """
    _ = config_path

    input_path = Path(claim_inventory_path) if claim_inventory_path else DEFAULT_CLAIM_INVENTORY_PATH
    destination = Path(output_path) if output_path else DEFAULT_EVIDENCE_OUTPUT_PATH

    payload = _load_json(input_path)
    claims = _extract_claims(payload)

    retrieval_results = []
    retrieval_exhausted_query_count_total = 0

    if dry_run:
        for claim in claims:
            result = _build_dry_run_result(claim)
            retrieval_exhausted_query_count_total += result.retrieval_exhausted_query_count
            retrieval_results.append(result.to_dict())
    else:
        pipeline = EvidenceRetrievalPipeline()
        for claim in claims:
            result = pipeline.retrieve_for_claim(claim)
            retrieval_exhausted_query_count_total += result.retrieval_exhausted_query_count
            retrieval_results.append(result.to_dict())

    destination.parent.mkdir(parents=True, exist_ok=True)

    output_payload = {
        "source_claim_inventory": str(input_path),
        "retrieval_count": len(retrieval_results),
        "dry_run": dry_run,
        "retrieval_exhausted_query_count_total": retrieval_exhausted_query_count_total,
        "retrieval_results": retrieval_results,
    }

    destination.write_text(
        json.dumps(output_payload, indent=2),
        encoding="utf-8",
    )

    print(f"Evidence retrieval written to: {destination}")

    return destination