from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from src.integration.adjudication_builder import build_adjudication_record


DEFAULT_CLAIM_INVENTORY_PATH = Path("data/processed/claim_inventory.json")
DEFAULT_EVIDENCE_RECORDS_PATH = Path("data/processed/evidence_records.json")
DEFAULT_ADJUDICATIONS_OUTPUT_PATH = Path("data/processed/adjudications.json")


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
    allow_skewed_adjudication: bool = False,
) -> dict[str, Any]:
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

        adjudications.append(asdict(adjudication))

    payload = {
        "schema_version": "week7.v1",
        "adjudications": adjudications,
        "skipped_claims": skipped_claims,
        "metrics": {
            "claims_loaded": len(claims),
            "evidence_records_loaded": len(evidence_records),
            "adjudications_written": len(adjudications),
            "claims_skipped": len(skipped_claims),
            "guarded_adjudications": sum(
                1 for record in adjudications if record.get("guard_reason")
            ),
        },
    }

    write_json_document(output_path, payload)

    return payload


if __name__ == "__main__":
    result = run_evidence_integration_pipeline()
    print(
        "Evidence adjudications written to: "
        f"{DEFAULT_ADJUDICATIONS_OUTPUT_PATH} "
        f"({result['metrics']['adjudications_written']} records)"
    )
