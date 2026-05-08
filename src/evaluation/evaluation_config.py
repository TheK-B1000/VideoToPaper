from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Union

from src.evaluation.evaluation_harness import EvaluationConfig


@dataclass(frozen=True)
class EvaluationOutputConfig:
    audit_report_path: str = "data/outputs/audit_report.json"
    audit_summary_path: Optional[str] = "data/outputs/audit_summary.md"
    manifest_path: Optional[str] = "data/outputs/evaluation_manifest.json"


@dataclass(frozen=True)
class EvaluationRuntimeConfig:
    evaluation: EvaluationConfig
    outputs: EvaluationOutputConfig
    metadata: Dict[str, Any]


def load_evaluation_runtime_config(
    config_path: Union[str, Path],
) -> EvaluationRuntimeConfig:
    path = Path(config_path)

    if not path.exists():
        raise FileNotFoundError(f"Evaluation config not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))

    evaluation_payload = payload.get("evaluation", {})
    output_payload = payload.get("outputs", {})
    metadata_payload = payload.get("metadata", {})

    evaluation = EvaluationConfig(
        clip_tolerance_seconds=float(
            evaluation_payload.get("clip_tolerance_seconds", 1.0)
        ),
        minimum_balanced_retrieval_ratio=float(
            evaluation_payload.get("minimum_balanced_retrieval_ratio", 0.8)
        ),
    )

    outputs = EvaluationOutputConfig(
        audit_report_path=output_payload.get(
            "audit_report_path",
            "data/outputs/audit_report.json",
        ),
        audit_summary_path=output_payload.get(
            "audit_summary_path",
            "data/outputs/audit_summary.md",
        ),
        manifest_path=output_payload.get(
            "manifest_path",
            "data/outputs/evaluation_manifest.json",
        ),
    )

    return EvaluationRuntimeConfig(
        evaluation=evaluation,
        outputs=outputs,
        metadata=metadata_payload,
    )