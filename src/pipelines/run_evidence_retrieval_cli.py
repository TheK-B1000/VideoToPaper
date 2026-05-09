from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.core.evidence_retrieval import (
    EvidenceRecord,
    EvidenceRetrievalResult,
    generate_balanced_queries,
)
from src.core.evidence_retrieval_output import validate_evidence_retrieval_output
from src.pipelines.evidence_retrieval_flatten import flatten_evidence_records
from src.pipelines.run_evidence_retrieval import (
    ClaimForRetrieval,
    EvidenceRetrievalPipeline,
    RetrievalSource,
)


DEFAULT_CLAIM_INVENTORY_PATH = Path("data/processed/claim_inventory.json")
DEFAULT_EVIDENCE_OUTPUT_PATH = Path("data/processed/evidence_retrieval.json")
DEFAULT_EVIDENCE_RUN_LOG_DIR = Path("logs/runs")


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
            identifier=f"semantic_scholar:dryrun-{claim.claim_id}:supports",
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
            identifier=f"semantic_scholar:dryrun-{claim.claim_id}:qualifies",
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


def _build_retrieval_summary(
    retrieval_results: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Build a stage-level audit summary for Week 5 retrieval quality.

    This makes balance visible at the run level instead of burying it inside
    each individual claim result.
    """
    total_claims = len(retrieval_results)

    balance_counts = {
        "balanced": 0,
        "supportive_skewed": 0,
        "contrary_skewed": 0,
        "insufficient": 0,
    }

    claims_needing_review: list[str] = []
    total_evidence_records = 0
    sources_seen: set[str] = set()

    for result in retrieval_results:
        balance_score = result.get("balance_score", "insufficient")

        if balance_score not in balance_counts:
            balance_score = "insufficient"

        balance_counts[balance_score] += 1

        if balance_score != "balanced":
            claims_needing_review.append(str(result.get("claim_id", "")))

        evidence_records = result.get("evidence_records", [])
        total_evidence_records += len(evidence_records)

        for record in evidence_records:
            source = record.get("source")

            if source:
                sources_seen.add(str(source))

    balanced_claims = balance_counts["balanced"]

    balance_rate = 0.0
    if total_claims > 0:
        balance_rate = balanced_claims / total_claims

    return {
        "total_claims": total_claims,
        "total_evidence_records": total_evidence_records,
        "balance_counts": balance_counts,
        "balance_rate": balance_rate,
        "claims_needing_review": claims_needing_review,
        "sources_seen": sorted(sources_seen),
        "publishable_for_week5": total_claims > 0 and len(claims_needing_review) == 0,
    }


def _enforce_retrieval_quality_gate(
    *,
    retrieval_summary: dict[str, Any],
    fail_on_unbalanced: bool,
) -> None:
    """
    Optionally fail the stage when retrieval is not balanced.

    This is the Week 5 guardrail against quietly producing a cherry-picked
    evidence set.
    """
    if not fail_on_unbalanced:
        return

    if retrieval_summary.get("publishable_for_week5") is True:
        return

    claims_needing_review = retrieval_summary.get("claims_needing_review", [])

    raise RuntimeError(
        "Evidence retrieval quality gate failed. "
        f"Claims needing review: {claims_needing_review}"
    )


def _write_retrieval_run_log(
    *,
    source_claim_inventory: Path,
    output_path: Path,
    dry_run: bool,
    source: str,
    per_query_limit: int,
    fail_on_unbalanced: bool,
    retrieval_count: int,
    retrieval_summary: dict[str, Any],
    log_dir: str | Path = DEFAULT_EVIDENCE_RUN_LOG_DIR,
) -> Path:
    """
    Write a small audit log for the evidence retrieval stage.

    The paper output answers: what evidence did we retrieve?
    The run log answers: how did this run execute?
    """
    resolved_log_dir = Path(log_dir)
    resolved_log_dir.mkdir(parents=True, exist_ok=True)

    run_id = str(uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    log_payload = {
        "run_id": run_id,
        "stage": "evidence_retrieval",
        "started_at": timestamp,
        "finished_at": timestamp,
        "source_claim_inventory": str(source_claim_inventory),
        "output_path": str(output_path),
        "dry_run": dry_run,
        "source": source,
        "per_query_limit": per_query_limit,
        "fail_on_unbalanced": fail_on_unbalanced,
        "retrieval_count": retrieval_count,
        "retrieval_summary": retrieval_summary,
    }

    log_path = resolved_log_dir / f"evidence_retrieval_{run_id}.json"
    log_path.write_text(json.dumps(log_payload, indent=2), encoding="utf-8")

    return log_path


def run_evidence_retrieval_cli(
    *,
    config_path: str | None = None,
    claim_inventory_path: str | None = None,
    output_path: str | None = None,
    source: str | None = None,
    per_query_limit: int | None = None,
    dry_run: bool | None = None,
    fail_on_unbalanced: bool | None = None,
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

    resolved_fail_on_unbalanced = bool(
        _resolve_setting(
            explicit_value=fail_on_unbalanced,
            config=config,
            config_key="fail_on_unbalanced",
            default_value=False,
        )
    )

    if not resolved_dry_run:
        ss_hint = ""
        if not os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "").strip():
            ss_hint = (
                " SEMANTIC_SCHOLAR_API_KEY is unset; Semantic Scholar uses public "
                "rate limits (set the key for higher throughput)."
            )
        print(f"Live evidence retrieval against OpenAlex / Semantic Scholar.{ss_hint}")

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

    retrieval_summary = _build_retrieval_summary(retrieval_results)

    _enforce_retrieval_quality_gate(
        retrieval_summary=retrieval_summary,
        fail_on_unbalanced=resolved_fail_on_unbalanced,
    )

    output_payload = {
        "source_claim_inventory": str(input_path),
        "retrieval_count": len(retrieval_results),
        "dry_run": resolved_dry_run,
        "source": resolved_source,
        "per_query_limit": resolved_per_query_limit,
        "fail_on_unbalanced": resolved_fail_on_unbalanced,
        "retrieval_exhausted_query_count_total": retrieval_exhausted_query_count_total,
        "retrieval_summary": retrieval_summary,
        "retrieval_results": retrieval_results,
    }

    validate_evidence_retrieval_output(output_payload)

    destination.write_text(
        json.dumps(output_payload, indent=2),
        encoding="utf-8",
    )

    flat_path = destination.with_name("evidence_records.json")
    flat_records = flatten_evidence_records(output_payload)
    flat_path.parent.mkdir(parents=True, exist_ok=True)
    flat_path.write_text(
        json.dumps(flat_records, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    run_log_path = _write_retrieval_run_log(
        source_claim_inventory=input_path,
        output_path=destination,
        dry_run=resolved_dry_run,
        source=resolved_source,
        per_query_limit=resolved_per_query_limit,
        fail_on_unbalanced=resolved_fail_on_unbalanced,
        retrieval_count=len(retrieval_results),
        retrieval_summary=retrieval_summary,
    )

    print(f"Evidence retrieval written to: {destination}")
    print(f"Evidence retrieval run log written to: {run_log_path}")

    return destination
