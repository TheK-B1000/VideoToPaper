from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Union


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class EvaluationManifest:
    paper_artifact_path: Optional[str]
    audit_report_path: str
    audit_summary_path: Optional[str]
    publishable: bool
    started_at: str
    finished_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "paper_artifact_path": self.paper_artifact_path,
            "audit_report_path": self.audit_report_path,
            "audit_summary_path": self.audit_summary_path,
            "publishable": self.publishable,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "metadata": self.metadata,
        }


def build_evaluation_manifest(
    *,
    paper_artifact_path: Optional[Union[str, Path]],
    audit_report_path: Union[str, Path],
    audit_summary_path: Optional[Union[str, Path]],
    publishable: bool,
    started_at: str,
    finished_at: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> EvaluationManifest:
    return EvaluationManifest(
        paper_artifact_path=str(paper_artifact_path) if paper_artifact_path else None,
        audit_report_path=str(audit_report_path),
        audit_summary_path=str(audit_summary_path) if audit_summary_path else None,
        publishable=publishable,
        started_at=started_at,
        finished_at=finished_at,
        metadata=metadata or {},
    )


def write_evaluation_manifest(
    manifest: EvaluationManifest,
    output_path: Union[str, Path],
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(
        json.dumps(manifest.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return path


def load_evaluation_manifest(input_path: Union[str, Path]) -> Dict[str, Any]:
    path = Path(input_path)

    if not path.exists():
        raise FileNotFoundError(f"Evaluation manifest not found: {path}")

    return json.loads(path.read_text(encoding="utf-8"))