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
    RetrievalSource,
)


DEFAULT_CLAIM_INVENTORY_PATH = Path("data/processed/claim_inventory.json")
DEFAULT_EVIDENCE_OUTPUT_PATH = Path("data/processed/evidence_retrieval.json")


def _load_json(path: str | Path) -> dict[str, Any]:
    resolved_path = Path(path)

    if not resolved_path.exists():
        raise FileNotFoundError(f"JSON file not found: {resolved_path}")

    return json.loads(resolved_path.read_text(encoding="utf-8"))


def _load_evidence_retrieval_config(config_path: str | None) -> dict[str, Any]:
    if not config_path:
        return {}

    payload = _load_json(config_path)
    section = payload.get("evidence_retrieval", {})

    if not isinstance(section, dict):
        raise ValueError("evidence_retrieval config section must be an object.")

    return section


def _resolve_setting(
    *,
    explicit_value: Any,
    config: dict[str, Any],
    config_key: str,
    default_value: Any,
) -> Any:
    if explicit_value is not None:
        return explicit_value

    if config_key in config:
        return config[config_key]

    return default_value


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


def _validate_source(source: str) -> RetrievalSource:
    if source not in ("all", "openalex", "semantic_scholar"):
        raise ValueError(
            "source must be one of: all, openalex, semantic_scholar"
        )

    return source  # type: ignore[return-value]


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
    source: str | None = None,
    per_query_limit: int | None = None,
    dry_run: bool | None = None,
) -> Path:
    """
    Run Week 5 evidence retrieval from the command line.

    Values can come from explicit CLI args or the ``evidence_retrieval`` section
    inside ``configs/argument_config.json``.
    """
    config = _load_evidence_retrieval_config(config_path)

    resolved_claim_inventory_path = _resolve_setting(
        explicit_value=claim_inventory_path,
        config=config,
        config_key="claim_inventory_path",
        default_value=str(DEFAULT_CLAIM_INVENTORY_PATH),
    )

    resolved_output_path = _resolve_setting(
        explicit_value=output_path,
        config=config,
        config_key="output_path",
        default_value=str(DEFAULT_EVIDENCE_OUTPUT_PATH),
    )

    resolved_source = _validate_source(
        str(
            _resolve_setting(
                explicit_value=source,
                config=config,
                config_key="source",
                default_value="all",
            )
        )
    )

    resolved_per_query_limit = int(
        _resolve_setting(
            explicit_value=per_query_limit,
            config=config,
            config_key="per_query_limit",
            default_value=3,
        )
    )

    if resolved_per_query_limit <= 0:
        raise ValueError("per_query_limit must be positive.")

    resolved_dry_run = bool(
        _resolve_setting(
            explicit_value=dry_run,
            config=config,
            config_key="dry_run",
            default_value=False,
        )
    )

    input_path = Path(str(resolved_claim_inventory_path))
    destination = Path(str(resolved_output_path))

    payload = _load_json(input_path)
    claims = _extract_claims(payload)

    retrieval_results = []
    retrieval_exhausted_query_count_total = 0

    if resolved_dry_run:
        for claim in claims:
            result = _build_dry_run_result(claim)
            retrieval_exhausted_query_count_total += result.retrieval_exhausted_query_count
            retrieval_results.append(result.to_dict())
    else:
        pipeline = EvidenceRetrievalPipeline()
        for claim in claims:
            result = pipeline.retrieve_for_claim(
                claim,
                source=resolved_source,
                per_query_limit=resolved_per_query_limit,
            )
            retrieval_exhausted_query_count_total += result.retrieval_exhausted_query_count
            retrieval_results.append(result.to_dict())

    destination.parent.mkdir(parents=True, exist_ok=True)

    output_payload = {
        "source_claim_inventory": str(input_path),
        "retrieval_count": len(retrieval_results),
        "dry_run": resolved_dry_run,
        "source": resolved_source,
        "per_query_limit": resolved_per_query_limit,
        "retrieval_exhausted_query_count_total": retrieval_exhausted_query_count_total,
        "retrieval_results": retrieval_results,
    }

    destination.write_text(
        json.dumps(output_payload, indent=2),
        encoding="utf-8",
    )

    print(f"Evidence retrieval written to: {destination}")

    return destination
