from __future__ import annotations

import json
from pathlib import Path

from src.pipelines.run_evidence_retrieval_cli import run_evidence_retrieval_cli


SMOKE_DIR = Path("data/smoke")
CLAIMS_PATH = SMOKE_DIR / "claim_inventory_smoke.json"
OUTPUT_PATH = SMOKE_DIR / "evidence_retrieval_smoke.json"
CONFIG_PATH = SMOKE_DIR / "evidence_retrieval_smoke_config.json"


def write_smoke_inputs() -> None:
    SMOKE_DIR.mkdir(parents=True, exist_ok=True)

    CLAIMS_PATH.write_text(
        json.dumps(
            {
                "claims": [
                    {
                        "claim_id": "claim_smoke_001",
                        "verbatim_quote": (
                            "Multi-agent reinforcement learning environments are "
                            "often non-stationary because agents learn at the same time."
                        ),
                        "claim_type": "empirical_technical",
                        "verification_strategy": "literature_review",
                    }
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    CONFIG_PATH.write_text(
        json.dumps(
            {
                "evidence_retrieval": {
                    "claim_inventory_path": str(CLAIMS_PATH),
                    "output_path": str(OUTPUT_PATH),
                    "source": "all",
                    "per_query_limit": 1,
                    "dry_run": False,
                }
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> None:
    write_smoke_inputs()

    output_path = run_evidence_retrieval_cli(config_path=str(CONFIG_PATH))

    payload = json.loads(output_path.read_text(encoding="utf-8"))

    print("\nSmoke test summary")
    print("------------------")
    print(f"Output path: {output_path}")
    print(f"Dry run: {payload['dry_run']}")
    print(f"Source: {payload['source']}")
    print(f"Per-query limit: {payload['per_query_limit']}")
    print(f"Retrieval count: {payload['retrieval_count']}")
    print(f"Evidence records: {payload['retrieval_summary']['total_evidence_records']}")
    print(f"Balance score counts: {payload['retrieval_summary']['balance_counts']}")

    if payload["dry_run"] is True:
        raise RuntimeError("Smoke test unexpectedly ran in dry-run mode.")

    if payload["retrieval_count"] != 1:
        raise RuntimeError("Smoke test expected exactly one claim result.")

    if payload["retrieval_summary"]["total_evidence_records"] == 0:
        raise RuntimeError("Smoke test returned no evidence records.")


if __name__ == "__main__":
    main()
