from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ArtifactRecord:
    label: str
    path: str
    exists: bool
    size_bytes: int | None
    sha256: str | None


@dataclass(frozen=True)
class PaperArtifactManifest:
    stage: str
    artifacts: list[ArtifactRecord]

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "artifacts": [asdict(artifact) for artifact in self.artifacts],
        }


class ArtifactManifestError(ValueError):
    """Raised when an artifact manifest cannot be written."""


def build_paper_artifact_manifest(
    *,
    paper_spec_path: str | Path,
    html_output_path: str | Path,
    audit_report_path: str | Path | None = None,
    run_report_path: str | Path | None = None,
) -> PaperArtifactManifest:
    """
    Build a manifest for Week 8 paper assembly artifacts.

    The manifest gives each generated artifact a stable file hash and byte size.
    This helps confirm that the HTML paper, paper spec, audit report, and run
    report are the exact artifacts produced by a run.
    """
    artifact_inputs: list[tuple[str, str | Path | None, bool]] = [
        ("paper_spec", paper_spec_path, True),
        ("html_paper", html_output_path, True),
        ("html_audit_report", audit_report_path, False),
        ("paper_run_report", run_report_path, False),
    ]

    artifacts = [
        _build_artifact_record(label=label, path=path, required=required)
        for label, path, required in artifact_inputs
        if path is not None or required
    ]

    return PaperArtifactManifest(
        stage="assemble_paper",
        artifacts=artifacts,
    )


def write_paper_artifact_manifest(
    *,
    output_path: str | Path,
    paper_spec_path: str | Path,
    html_output_path: str | Path,
    audit_report_path: str | Path | None = None,
    run_report_path: str | Path | None = None,
) -> Path:
    manifest = build_paper_artifact_manifest(
        paper_spec_path=paper_spec_path,
        html_output_path=html_output_path,
        audit_report_path=audit_report_path,
        run_report_path=run_report_path,
    )

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(manifest.to_dict(), indent=2), encoding="utf-8")

    return target


def _build_artifact_record(
    *,
    label: str,
    path: str | Path | None,
    required: bool,
) -> ArtifactRecord:
    if path is None:
        if required:
            raise ArtifactManifestError(f"Required artifact path missing: {label}")

        return ArtifactRecord(
            label=label,
            path="",
            exists=False,
            size_bytes=None,
            sha256=None,
        )

    target = Path(path)

    if not target.exists():
        if required:
            raise ArtifactManifestError(f"Required artifact does not exist: {target}")

        return ArtifactRecord(
            label=label,
            path=str(target),
            exists=False,
            size_bytes=None,
            sha256=None,
        )

    if not target.is_file():
        raise ArtifactManifestError(f"Artifact path is not a file: {target}")

    data = target.read_bytes()

    return ArtifactRecord(
        label=label,
        path=str(target),
        exists=True,
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
    )
