from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.frontend.audit_summary import summarize_audit_report
from src.frontend.inquiry_studio import InquiryRecord
from src.frontend.paper_artifacts import inspect_paper_artifact


@dataclass(frozen=True)
class SampleArtifact:
    inquiry_id: str
    title: str
    youtube_url: str
    paper_path: str | None
    audit_report_path: str | None
    paper_exists: bool
    audit_exists: bool
    audit_publishable: bool | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "inquiry_id": self.inquiry_id,
            "title": self.title,
            "youtube_url": self.youtube_url,
            "paper_path": self.paper_path,
            "audit_report_path": self.audit_report_path,
            "paper_exists": self.paper_exists,
            "audit_exists": self.audit_exists,
            "audit_publishable": self.audit_publishable,
        }


@dataclass(frozen=True)
class SampleArtifactIndex:
    title: str
    content: str
    samples: list[SampleArtifact]

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "content": self.content,
            "samples": [sample.to_dict() for sample in self.samples],
        }


def build_sample_artifact_index(
    records: list[InquiryRecord],
    *,
    title: str = "Sample Inquiry Artifacts",
) -> SampleArtifactIndex:
    samples = [build_sample_artifact(record) for record in records]

    content = "\n\n".join(
        [
            f"# {title}",
            _build_intro(),
            _render_summary_table(samples),
            *[_render_sample(sample) for sample in samples],
            _build_review_notes(),
        ]
    )

    return SampleArtifactIndex(
        title=title,
        content=content,
        samples=samples,
    )


def build_sample_artifact(record: InquiryRecord) -> SampleArtifact:
    paper = inspect_paper_artifact(record.paper_path)
    audit_exists = bool(record.audit_report_path and Path(record.audit_report_path).exists())

    audit_publishable = None

    if audit_exists and record.audit_report_path:
        audit_report = _load_json(record.audit_report_path)
        audit_summary = summarize_audit_report(audit_report)
        audit_publishable = audit_summary.publishable

    return SampleArtifact(
        inquiry_id=record.inquiry_id,
        title=record.title,
        youtube_url=record.youtube_url,
        paper_path=record.paper_path,
        audit_report_path=record.audit_report_path,
        paper_exists=paper.exists,
        audit_exists=audit_exists,
        audit_publishable=audit_publishable,
    )


def write_sample_artifact_index(
    records: list[InquiryRecord],
    *,
    output_path: str | Path = "docs/sample_artifacts.md",
    title: str = "Sample Inquiry Artifacts",
) -> Path:
    index = build_sample_artifact_index(records, title=title)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(index.content, encoding="utf-8")
    return path


def load_inquiry_records_from_library(library_dir: str | Path) -> list[InquiryRecord]:
    root = Path(library_dir)

    if not root.exists():
        return []

    records: list[InquiryRecord] = []

    for manifest_path in sorted(root.glob("*/manifest.json")):
        try:
            records.append(InquiryRecord.from_manifest(manifest_path))
        except Exception:
            continue

    return records


def _build_intro() -> str:
    return """This document lists portfolio-ready sample outputs for the Inquiry Engine.

Each sample should include a generated interactive HTML paper and its matching audit report. The goal is to make it easy for a reviewer to inspect the output, verify source anchoring, and understand whether the generated paper passed the system's evaluation checks."""


def _render_summary_table(samples: list[SampleArtifact]) -> str:
    rows = [
        "| Inquiry | Paper | Audit | Publishable |",
        "|---|---:|---:|---:|",
    ]

    for sample in samples:
        rows.append(
            "| "
            f"{sample.title} "
            f"| {_yes_no(sample.paper_exists)} "
            f"| {_yes_no(sample.audit_exists)} "
            f"| {_publishable_label(sample.audit_publishable)} "
            "|"
        )

    return "\n".join(["## Summary", *rows])


def _render_sample(sample: SampleArtifact) -> str:
    return f"""## {sample.title}

| Field | Value |
|---|---|
| Inquiry ID | `{sample.inquiry_id}` |
| Source video | {sample.youtube_url} |
| Paper path | `{sample.paper_path or "not available"}` |
| Audit report path | `{sample.audit_report_path or "not available"}` |
| Paper exists | `{sample.paper_exists}` |
| Audit exists | `{sample.audit_exists}` |
| Audit publishable | `{sample.audit_publishable}` |

### Reviewer checklist

- Open the paper artifact.
- Click at least one embedded source clip.
- Expand at least one evidence trail.
- Open the audit report.
- Confirm there are no fabricated references.
- Confirm clip-anchor accuracy passed or review any drift warnings."""


def _build_review_notes() -> str:
    return """## Notes for reviewers

The strongest samples are not necessarily the cleanest ones. A useful sample can show limitations, contested evidence, or a non-publishable audit result if the system clearly explains why.

For portfolio review, include at least two samples:

1. One clean/publishable output.
2. One more complex output where evidence is mixed, limited, or qualified."""


def _load_json(path: str | Path) -> dict[str, Any]:
    import json

    with Path(path).open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("Expected audit report to be a JSON object.")

    return data


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _publishable_label(value: bool | None) -> str:
    if value is True:
        return "yes"

    if value is False:
        return "no"

    return "unknown"