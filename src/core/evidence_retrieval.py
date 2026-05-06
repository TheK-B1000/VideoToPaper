from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal


EvidenceStance = Literal["supports", "contradicts", "complicates", "qualifies"]
EvidenceTier = Literal[1, 2, 3]
BalanceScore = Literal["balanced", "supportive_skewed", "contrary_skewed", "insufficient"]


@dataclass(frozen=True)
class EvidenceRecord:
    claim_id: str
    title: str
    source: str
    tier: EvidenceTier
    stance: EvidenceStance
    identifier: str
    url: str | None = None
    doi: str | None = None
    abstract: str | None = None
    year: int | None = None

    def validate(self) -> None:
        if not self.claim_id.strip():
            raise ValueError("EvidenceRecord requires claim_id.")

        if not self.title.strip():
            raise ValueError("EvidenceRecord requires title.")

        if not self.source.strip():
            raise ValueError("EvidenceRecord requires source.")

        if self.tier not in (1, 2, 3):
            raise ValueError(f"Invalid evidence tier: {self.tier}")

        if self.stance not in ("supports", "contradicts", "complicates", "qualifies"):
            raise ValueError(f"Invalid evidence stance: {self.stance}")

        if not self.identifier.strip():
            raise ValueError("EvidenceRecord requires a resolvable identifier.")

        if not (self.url or self.doi or self.identifier):
            raise ValueError("EvidenceRecord must include url, doi, or identifier.")


@dataclass(frozen=True)
class EvidenceRetrievalResult:
    claim_id: str
    queries_executed: list[str]
    evidence_records: list[EvidenceRecord]
    balance_score: BalanceScore

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "queries_executed": self.queries_executed,
            "evidence_records": [asdict(record) for record in self.evidence_records],
            "balance_score": self.balance_score,
        }


def generate_balanced_queries(claim_text: str) -> list[str]:
    """
    Produce retrieval queries that intentionally search for supporting,
    contrary, and qualifying evidence.

    This is intentionally heuristic for now. Later, Week 5 can route this
    through a safe LLM call if needed.
    """
    clean_claim = " ".join(claim_text.split())

    if not clean_claim:
        raise ValueError("claim_text cannot be empty.")

    return [
        clean_claim,
        f"evidence supporting {clean_claim}",
        f"evidence against {clean_claim}",
        f"limitations qualifications {clean_claim}",
    ]


def score_evidence_balance(records: list[EvidenceRecord]) -> BalanceScore:
    """
    Score whether retrieval contains evidence on multiple sides.

    supports: directly supports the claim
    contradicts: directly challenges the claim
    complicates/qualifies: adds nuance, limits, or mixed findings
    """
    if not records:
        return "insufficient"

    support_count = sum(1 for record in records if record.stance == "supports")
    contrary_count = sum(1 for record in records if record.stance == "contradicts")
    nuance_count = sum(1 for record in records if record.stance in ("complicates", "qualifies"))

    has_support = support_count > 0
    has_contrary_or_nuance = contrary_count > 0 or nuance_count > 0

    if has_support and has_contrary_or_nuance:
        return "balanced"

    if has_support and not has_contrary_or_nuance:
        return "supportive_skewed"

    if contrary_count > 0 and support_count == 0:
        return "contrary_skewed"

    return "insufficient"


class RetrievalCache:
    """
    Small JSON-file cache for development.

    This prevents duplicate academic API calls while you test the pipeline.
    """

    def __init__(self, cache_dir: str | Path = "logs/retrieval_cache") -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _key_to_path(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{digest}.json"

    def get(self, key: str) -> dict[str, Any] | None:
        path = self._key_to_path(key)

        if not path.exists():
            return None

        return json.loads(path.read_text(encoding="utf-8"))

    def set(self, key: str, payload: dict[str, Any]) -> None:
        path = self._key_to_path(key)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def build_evidence_result(
    claim_id: str,
    claim_text: str,
    records: list[EvidenceRecord],
) -> EvidenceRetrievalResult:
    for record in records:
        record.validate()

    queries = generate_balanced_queries(claim_text)
    balance_score = score_evidence_balance(records)

    return EvidenceRetrievalResult(
        claim_id=claim_id,
        queries_executed=queries,
        evidence_records=records,
        balance_score=balance_score,
    )