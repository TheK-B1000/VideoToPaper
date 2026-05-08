from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Union


def build_publishable_sample_artifact() -> Dict[str, Any]:
    return {
        "claims": [
            {
                "claim_id": "claim_001",
                "verbatim_quote": "Balanced evidence matters when evaluating a claim.",
                "anchor_clip": {
                    "start": 10.0,
                    "end": 20.0,
                },
            }
        ],
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
        "adjudications": [
            {
                "claim_id": "claim_001",
                "speaker_claim_summary": "The speaker claims evidence should be evaluated in a balanced way.",
                "balance_score": "balanced",
                "verdict": "well_supported_with_qualifications",
            }
        ],
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
        ],
        "references": [
            {
                "evidence_record_id": "evidence_001",
                "identifier": "10.1234/example-study",
                "url": "https://example.com/example-study",
            },
            {
                "evidence_record_id": "evidence_002",
                "identifier": "report-example-001",
                "url": "https://example.com/example-report",
            },
        ],
        "rendered_clips": [
            {
                "claim_id": "claim_001",
                "start": 10.0,
                "end": 20.0,
            }
        ],
    }


def build_unpublishable_sample_artifact() -> Dict[str, Any]:
    artifact = build_publishable_sample_artifact()

    artifact["rendered_clips"][0]["start"] = 40.0
    artifact["rendered_clips"][0]["end"] = 50.0
    artifact["adjudications"][0]["balance_score"] = "supportive_skewed"
    artifact["adjudications"][0]["verdict"] = "well_supported"

    artifact["references"].append(
        {
            "evidence_record_id": "evidence_001",
            "identifier": "fake-source",
            "url": "https://fake.example/source",
        }
    )

    return artifact


def write_sample_artifact(
    output_path: Union[str, Path],
    *,
    publishable: bool = True,
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    artifact = (
        build_publishable_sample_artifact()
        if publishable
        else build_unpublishable_sample_artifact()
    )

    path.write_text(
        json.dumps(artifact, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return path