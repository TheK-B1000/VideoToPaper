from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence
from uuid import uuid4

from src.integration.adjudication_builder import build_adjudication_record
from src.integration.adjudication_validator import validate_adjudications_payload
from src.integration.cherry_picking_guard import build_cherry_picking_guard_report
from src.integration.evidence_narrative import generate_evidence_narrative


DEFAULT_CLAIM_INVENTORY_PATH = Path("data/processed/claim_inventory.json")
DEFAULT_EVIDENCE_RECORDS_PATH = Path("data/processed/evidence_records.json")
DEFAULT_ADJUDICATIONS_OUTPUT_PATH = Path("data/processed/adjudications.json")
DEFAULT_RUN_LOG_DIR = Path("logs/runs")
PIPELINE_NAME = "evidence_integration"
PIPELINE_STAGE = "week7"


def load_json_document(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"JSON input file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json_document(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, ensure_ascii=False)


def normalize_claim_inventory(document: Any) -> list[Mapping[str, Any]]:
    """
    Accept the common claim inventory shapes produced by earlier weeks.

    Supported shapes:
    1. [{"claim_id": "..."}]
    2. {"claims": [...]}
    3. {"claim_inventory": [...]}
    """
    if isinstance(document, list):
        return document

    if isinstance(document, dict):
        claims = document.get("claims") or document.get("claim_inventory")

        if isinstance(claims, list):
            return claims

    raise ValueError(
        "Claim inventory must be a list, {'claims': [...]}, or {'claim_inventory': [...]}."
    )


def normalize_evidence_records(document: Any) -> list[Mapping[str, Any]]:
    """
    Accept the common evidence output shapes from Week 5.

    Supported shapes:
    1. [{"claim_id": "...", "stance": "..."}]
    2. {"evidence_records": [...]}
    3. {"records": [...]}
    """
    if isinstance(document, list):
        return document

    if isinstance(document, dict):
        records = document.get("evidence_records") or document.get("records")

        if isinstance(records, list):
            return records

    raise ValueError(
        "Evidence records must be a list, {'evidence_records': [...]}, or {'records': [...]}."
    )


def group_evidence_by_claim_id(
    evidence_records: Sequence[Mapping[str, Any]],
) -> dict[str, list[Mapping[str, Any]]]:
    grouped: dict[str, list[Mapping[str, Any]]] = {}

    for record in evidence_records:
        claim_id = record.get("claim_id")

        if not isinstance(claim_id, str) or not claim_id.strip():
            raise ValueError(f"Evidence record is missing a valid claim_id: {record!r}")

        grouped.setdefault(claim_id.strip(), []).append(record)

    return grouped


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def write_run_log(
    *,
    run_log_dir: Path,
    run_id: str,
    started_at: str,
    finished_at: str,
    claim_inventory_path: Path,
    evidence_records_path: Path,
    output_path: Path,
    settings: Mapping[str, Any],
    metrics: Mapping[str, Any],
    status: str,
    cherry_picking_guard: Mapping[str, Any] | None = None,
    validation: Mapping[str, Any] | None = None,
    error: str | None = None,
) -> Path:
    """
    Write an audit-grade run log for Week 7 evidence integration.

    The adjudications file is the product. The run log is the receipt.
    It records what inputs were used, what output was written, what settings
    were active, and whether the stage completed successfully.
    """
    run_log_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "run_id": run_id,
        "pipeline_name": PIPELINE_NAME,
        "stage": PIPELINE_STAGE,
        "status": status,
        "started_at": started_at,
        "finished_at": finished_at,
        "input_paths": {
            "claim_inventory": str(claim_inventory_path),
            "evidence_records": str(evidence_records_path),
        },
        "output_paths": {
            "adjudications": str(output_path),
        },
        "settings": dict(settings),
        "metrics": dict(metrics),
        "cherry_picking_guard": dict(cherry_picking_guard or {}),
        "validation": dict(validation or {}),
    }

    if error is not None:
        payload["error"] = error

    log_path = run_log_dir / f"{PIPELINE_NAME}_{run_id}.json"

    with log_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, ensure_ascii=False)

    return log_path


def should_integrate_claim(claim: Mapping[str, Any]) -> bool:
    """
    Only empirical claims should move into evidence integration.

    Normative and interpretive claims may appear in the paper, but they should
    not receive literature-style adjudications.
    """
    claim_type = claim.get("claim_type")
    verification_strategy = claim.get("verification_strategy")

    if isinstance(verification_strategy, str):
        return verification_strategy.strip().lower() == "literature_review"

    if isinstance(claim_type, str):
        return claim_type.strip().lower().startswith("empirical")

    return False


def run_evidence_integration_pipeline(
    *,
    claim_inventory_path: Path = DEFAULT_CLAIM_INVENTORY_PATH,
    evidence_records_path: Path = DEFAULT_EVIDENCE_RECORDS_PATH,
    output_path: Path = DEFAULT_ADJUDICATIONS_OUTPUT_PATH,
    run_log_dir: Path = DEFAULT_RUN_LOG_DIR,
    allow_skewed_adjudication: bool = False,
    use_llm_narratives: bool = False,
    narrative_client: Any | None = None,
) -> dict[str, Any]:
    run_id = str(uuid4())
    started_at = utc_now_iso()

    try:
        claim_document = load_json_document(claim_inventory_path)
        evidence_document = load_json_document(evidence_records_path)

        claims = normalize_claim_inventory(claim_document)
        evidence_records = normalize_evidence_records(evidence_document)
        evidence_by_claim_id = group_evidence_by_claim_id(evidence_records)

        adjudications = []
        skipped_claims = []

        for claim in claims:
            claim_id = claim.get("claim_id")

            if not isinstance(claim_id, str) or not claim_id.strip():
                raise ValueError(f"Claim is missing a valid claim_id: {claim!r}")

            normalized_claim_id = claim_id.strip()

            if not should_integrate_claim(claim):
                skipped_claims.append(
                    {
                        "claim_id": normalized_claim_id,
                        "reason": "Claim is not routed to literature_review.",
                    }
                )
                continue

            claim_evidence = evidence_by_claim_id.get(normalized_claim_id, [])

            adjudication = build_adjudication_record(
                claim,
                claim_evidence,
                allow_skewed_adjudication=allow_skewed_adjudication,
            )

            adjudication_payload = asdict(adjudication)

            narrative_result = generate_evidence_narrative(
                claim=claim,
                adjudication=adjudication_payload,
                evidence_records=claim_evidence,
                narrative_client=narrative_client,
                use_llm=use_llm_narratives,
            )

            adjudication_payload["narrative"] = narrative_result.narrative
            adjudication_payload["narrative_generation"] = {
                "used_llm": narrative_result.used_llm,
                "fallback_reason": narrative_result.fallback_reason,
            }

            adjudications.append(adjudication_payload)

        metrics = {
            "claims_loaded": len(claims),
            "evidence_records_loaded": len(evidence_records),
            "adjudications_written": len(adjudications),
            "claims_skipped": len(skipped_claims),
            "guarded_adjudications": sum(
                1 for record in adjudications if record.get("guard_reason")
            ),
            "llm_narratives_used": sum(
                1
                for record in adjudications
                if record.get("narrative_generation", {}).get("used_llm") is True
            ),
            "fallback_narratives_used": sum(
                1
                for record in adjudications
                if record.get("narrative_generation", {}).get("used_llm") is False
            ),
        }

        guard_report = build_cherry_picking_guard_report(adjudications)

        payload = {
            "schema_version": "week7.v1",
            "run_id": run_id,
            "adjudications": adjudications,
            "skipped_claims": skipped_claims,
            "metrics": metrics,
            "cherry_picking_guard": guard_report,
        }

        validation_report = validate_adjudications_payload(payload)
        payload["validation"] = validation_report

        write_json_document(output_path, payload)

        finished_at = utc_now_iso()
        run_log_path = write_run_log(
            run_log_dir=run_log_dir,
            run_id=run_id,
            started_at=started_at,
            finished_at=finished_at,
            claim_inventory_path=claim_inventory_path,
            evidence_records_path=evidence_records_path,
            output_path=output_path,
            settings={
                "allow_skewed_adjudication": allow_skewed_adjudication,
                "use_llm_narratives": use_llm_narratives,
            },
            metrics=metrics,
            status="completed",
            cherry_picking_guard=guard_report,
            validation=validation_report,
        )

        payload["run_log_path"] = str(run_log_path)

        return payload

    except Exception as exc:
        finished_at = utc_now_iso()

        error_metrics = {
            "claims_loaded": 0,
            "evidence_records_loaded": 0,
            "adjudications_written": 0,
            "claims_skipped": 0,
            "guarded_adjudications": 0,
            "llm_narratives_used": 0,
            "fallback_narratives_used": 0,
        }

        write_run_log(
            run_log_dir=run_log_dir,
            run_id=run_id,
            started_at=started_at,
            finished_at=finished_at,
            claim_inventory_path=claim_inventory_path,
            evidence_records_path=evidence_records_path,
            output_path=output_path,
            settings={
                "allow_skewed_adjudication": allow_skewed_adjudication,
                "use_llm_narratives": use_llm_narratives,
            },
            metrics=error_metrics,
            status="failed",
            error=str(exc),
        )

        raise


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Week 7 evidence integration and write adjudications."
    )

    parser.add_argument(
        "--claim-inventory-path",
        type=Path,
        default=DEFAULT_CLAIM_INVENTORY_PATH,
        help="Path to the Week 3 claim inventory JSON file.",
    )

    parser.add_argument(
        "--evidence-records-path",
        type=Path,
        default=DEFAULT_EVIDENCE_RECORDS_PATH,
        help="Path to the Week 5 evidence records JSON file.",
    )

    parser.add_argument(
        "--output-path",
        type=Path,
        default=DEFAULT_ADJUDICATIONS_OUTPUT_PATH,
        help="Path where Week 7 adjudications JSON will be written.",
    )

    parser.add_argument(
        "--run-log-dir",
        type=Path,
        default=DEFAULT_RUN_LOG_DIR,
        help="Directory where the Week 7 MLOps run log will be written.",
    )

    parser.add_argument(
        "--allow-skewed-adjudication",
        action="store_true",
        help=(
            "Allow adjudication even when retrieval is supportive-skewed or "
            "contrary-skewed. Default is false."
        ),
    )

    parser.add_argument(
        "--use-llm-narratives",
        action="store_true",
        help=(
            "Enable LLM-backed evidence narratives. Requires a narrative client "
            "to be wired in by application code. The CLI default path uses fallback narratives."
        ),
    )

    return parser


def main(argv: list[str] | None = None) -> dict[str, Any]:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    result = run_evidence_integration_pipeline(
        claim_inventory_path=args.claim_inventory_path,
        evidence_records_path=args.evidence_records_path,
        output_path=args.output_path,
        run_log_dir=args.run_log_dir,
        allow_skewed_adjudication=args.allow_skewed_adjudication,
        use_llm_narratives=args.use_llm_narratives,
    )

    print(
        "Evidence adjudications written to: "
        f"{args.output_path} "
        f"({result['metrics']['adjudications_written']} records)"
    )
    print(f"Run log written to: {result['run_log_path']}")

    if not result["validation"]["is_valid"]:
        print(
            "Validation warning: "
            f"{result['validation']['issue_count']} issue(s) found."
        )

    if not result["cherry_picking_guard"]["publishable_for_week8"]:
        print("Cherry-picking guard warning: output is not publishable for Week 8 yet.")

    return result


if __name__ == "__main__":
    main()
