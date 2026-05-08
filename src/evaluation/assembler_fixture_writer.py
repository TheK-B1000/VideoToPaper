from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Union


def build_assembler_fixture_payloads() -> Dict[str, Any]:
    """
    Build realistic assembler-style JSON payloads.

    These are not evaluator-ready yet. They represent the separate output
    files a paper assembler or upstream pipeline might produce.
    """
    return {
        "claims": {
            "claims": [
                {
                    "claim_id": "claim_001",
                    "verbatim_quote": "Balanced evidence matters when evaluating a claim.",
                    "anchor_clip": {
                        "start": 10.0,
                        "end": 20.0,
                    },
                }
            ]
        },
        "speaker_perspective": {
            "expected_qualifications": [
                "the available evidence may be mixed"
            ],
            "qualifications_preserved": [
                "the available evidence may be mixed"
            ],
            "narrative_blocks": [
                {
                    "assertions": [
                        {
                            "text": "The speaker argues that evidence should be weighed carefully.",
                            "hedge_drift_detected": False,
                        }
                    ],
                    "verbatim_anchors": ["claim_001"],
                }
            ],
        },
        "adjudications": {
            "adjudications": [
                {
                    "claim_id": "claim_001",
                    "speaker_claim_summary": (
                        "The speaker claims evidence should be evaluated "
                        "in a balanced way."
                    ),
                    "balance_score": "balanced",
                    "verdict": "well_supported_with_qualifications",
                }
            ]
        },
        "evidence_records": {
            "evidence_records": [
                {
                    "evidence_record_id": "evidence_001",
                    "claim_id": "claim_001",
                    "tier": 1,
                    "stance": "supports",
                    "title": "Example Study on Evidence Evaluation",
                    "identifier": "10.1234/example-study",
                    "url": "https://example.com/example-study",
                },
                {
                    "evidence_record_id": "evidence_002",
                    "claim_id": "claim_001",
                    "tier": 2,
                    "stance": "qualifies",
                    "title": "Example Institutional Report",
                    "identifier": "report-example-001",
                    "url": "https://example.com/example-report",
                },
            ]
        },
    }


def write_assembler_fixtures(output_dir: Union[str, Path]) -> Dict[str, Path]:
    """
    Write assembler-style fixture files to a directory.

    Returns a dictionary of logical fixture names to written paths.
    """
    base_dir = Path(output_dir)
    base_dir.mkdir(parents=True, exist_ok=True)

    payloads = build_assembler_fixture_payloads()

    paths = {
        "claims": base_dir / "claims.json",
        "speaker_perspective": base_dir / "speaker_perspective.json",
        "adjudications": base_dir / "adjudications.json",
        "evidence_records": base_dir / "evidence_records.json",
    }

    for key, path in paths.items():
        path.write_text(
            json.dumps(payloads[key], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    return paths
