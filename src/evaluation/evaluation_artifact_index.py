from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Union


@dataclass(frozen=True)
class EvaluationArtifactIndex:
    paper_artifact_path: Optional[str]
    audit_report_path: Optional[str]
    audit_summary_path: Optional[str]
    manifest_path: Optional[str]
    validation_report_path: Optional[str]
    validation_summary_path: Optional[str]
    publishable: Optional[bool]
    valid: Optional[bool]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "paper_artifact_path": self.paper_artifact_path,
            "audit_report_path": self.audit_report_path,
            "audit_summary_path": self.audit_summary_path,
            "manifest_path": self.manifest_path,
            "validation_report_path": self.validation_report_path,
            "validation_summary_path": self.validation_summary_path,
            "publishable": self.publishable,
            "valid": self.valid,
            "metadata": self.metadata,
        }


def build_evaluation_artifact_index(
    *,
    paper_artifact_path: Optional[Union[str, Path]] = None,
    audit_report_path: Optional[Union[str, Path]] = None,
    audit_summary_path: Optional[Union[str, Path]] = None,
    manifest_path: Optional[Union[str, Path]] = None,
    validation_report_path: Optional[Union[str, Path]] = None,
    validation_summary_path: Optional[Union[str, Path]] = None,
    publishable: Optional[bool] = None,
    valid: Optional[bool] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> EvaluationArtifactIndex:
    return EvaluationArtifactIndex(
        paper_artifact_path=str(paper_artifact_path) if paper_artifact_path else None,
        audit_report_path=str(audit_report_path) if audit_report_path else None,
        audit_summary_path=str(audit_summary_path) if audit_summary_path else None,
        manifest_path=str(manifest_path) if manifest_path else None,
        validation_report_path=str(validation_report_path) if validation_report_path else None,
        validation_summary_path=str(validation_summary_path) if validation_summary_path else None,
        publishable=publishable,
        valid=valid,
        metadata=metadata or {},
    )


def write_evaluation_artifact_index(
    index: EvaluationArtifactIndex,
    output_path: Union[str, Path],
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(
        json.dumps(index.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return path


def load_evaluation_artifact_index(input_path: Union[str, Path]) -> Dict[str, Any]:
    path = Path(input_path)

    if not path.exists():
        raise FileNotFoundError(f"Evaluation artifact index not found: {path}")

    return json.loads(path.read_text(encoding="utf-8"))