from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.frontend.backend_client import BackendClient, BackendResponse


@dataclass(frozen=True)
class ImportedInquiryRecord:
    inquiry_id: str
    title: str
    youtube_url: str
    status: str
    created_at: str
    paper_path: str | None
    audit_report_path: str | None
    parameters: dict[str, Any]


@dataclass(frozen=True)
class BackendInquiryImportResult:
    imported: bool
    inquiry_id: str
    manifest_path: str | None
    record: ImportedInquiryRecord | None
    message: str
    response_data: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "imported": self.imported,
            "inquiry_id": self.inquiry_id,
            "manifest_path": self.manifest_path,
            "record": self.record.__dict__ if self.record is not None else None,
            "message": self.message,
            "response_data": self.response_data,
        }


def import_backend_inquiry(
    *,
    inquiry_id: str,
    client: BackendClient,
    library_dir: str | Path = "data/inquiries",
) -> BackendInquiryImportResult:
    clean_inquiry_id = inquiry_id.strip()

    if not clean_inquiry_id:
        raise ValueError("inquiry_id cannot be empty.")

    response = client.get_inquiry_manifest(clean_inquiry_id)

    return backend_response_to_inquiry_import_result(
        response,
        inquiry_id=clean_inquiry_id,
        library_dir=library_dir,
    )


def backend_response_to_inquiry_import_result(
    response: BackendResponse,
    *,
    inquiry_id: str,
    library_dir: str | Path,
) -> BackendInquiryImportResult:
    if not response.ok:
        return BackendInquiryImportResult(
            imported=False,
            inquiry_id=inquiry_id,
            manifest_path=None,
            record=None,
            message=response.error_message or "Backend inquiry import failed.",
            response_data=response.data,
        )

    try:
        manifest = normalize_backend_inquiry_manifest(
            response.data,
            fallback_inquiry_id=inquiry_id,
        )
        manifest_path = save_inquiry_manifest(
            manifest,
            library_dir=library_dir,
        )
        record = _load_imported_inquiry_record(manifest_path)
    except ValueError as error:
        return BackendInquiryImportResult(
            imported=False,
            inquiry_id=inquiry_id,
            manifest_path=None,
            record=None,
            message=str(error),
            response_data=response.data,
        )

    return BackendInquiryImportResult(
        imported=True,
        inquiry_id=record.inquiry_id,
        manifest_path=manifest_path.as_posix(),
        record=record,
        message="Backend inquiry imported into local library.",
        response_data=response.data,
    )


def normalize_backend_inquiry_manifest(
    payload: dict[str, Any],
    *,
    fallback_inquiry_id: str,
) -> dict[str, Any]:
    """
    Convert likely backend inquiry response shapes into the local manifest shape.

    Supported shapes:

    1. Native manifest:
       {
         "inquiry_id": "...",
         "title": "...",
         "youtube_url": "...",
         "status": "completed",
         "created_at": "...",
         "paper_path": "...",
         "audit_report_path": "...",
         "parameters": {...}
       }

    2. Wrapped API shape:
       {
         "inquiry": {...}
       }

    3. Minimal API shape:
       {
         "id": "...",
         "video": {"title": "...", "url": "..."},
         "paper": {"html_render_path": "..."},
         "audit": {"report_path": "..."}
       }
    """
    if "inquiry" in payload and isinstance(payload["inquiry"], dict):
        source = dict(payload["inquiry"])
    else:
        source = dict(payload)

    video = source.get("video", {})
    paper = source.get("paper", {})
    audit = source.get("audit", {})

    if not isinstance(video, dict):
        video = {}

    if not isinstance(paper, dict):
        paper = {}

    if not isinstance(audit, dict):
        audit = {}

    inquiry_id = (
        source.get("inquiry_id")
        or source.get("id")
        or fallback_inquiry_id
    )

    title = (
        source.get("title")
        or video.get("title")
        or "Untitled inquiry"
    )

    youtube_url = (
        source.get("youtube_url")
        or source.get("url")
        or video.get("youtube_url")
        or video.get("url")
        or ""
    )

    if not str(youtube_url).strip():
        raise ValueError("Backend inquiry manifest is missing youtube_url.")

    return {
        "inquiry_id": str(inquiry_id),
        "title": str(title),
        "youtube_url": str(youtube_url),
        "status": str(source.get("status", "completed")),
        "created_at": str(source.get("created_at", "")),
        "paper_path": _optional_string(
            source.get("paper_path")
            or paper.get("html_render_path")
            or paper.get("path")
        ),
        "audit_report_path": _optional_string(
            source.get("audit_report_path")
            or audit.get("report_path")
            or audit.get("path")
        ),
        "parameters": dict(source.get("parameters", {})),
    }


def save_inquiry_manifest(
    manifest: dict[str, Any],
    *,
    library_dir: str | Path,
) -> Path:
    inquiry_id = str(manifest.get("inquiry_id", "")).strip()

    if not inquiry_id:
        raise ValueError("Inquiry manifest is missing inquiry_id.")

    inquiry_dir = Path(library_dir) / _safe_directory_name(inquiry_id)
    inquiry_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = inquiry_dir / "manifest.json"

    manifest_path.write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    return manifest_path


def _safe_directory_name(value: str) -> str:
    return "".join(
        char if char.isalnum() or char in {"_", "-"} else "_"
        for char in value
    )


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    return text or None


def _load_imported_inquiry_record(manifest_path: Path) -> ImportedInquiryRecord:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))

    if not isinstance(data, dict):
        raise ValueError("Imported inquiry manifest must be a JSON object.")

    return ImportedInquiryRecord(
        inquiry_id=str(data.get("inquiry_id", manifest_path.parent.name)),
        title=str(data.get("title", "Untitled inquiry")),
        youtube_url=str(data.get("youtube_url", "")),
        status=str(data.get("status", "unknown")),
        created_at=str(data.get("created_at", "")),
        paper_path=_optional_string(data.get("paper_path")),
        audit_report_path=_optional_string(data.get("audit_report_path")),
        parameters=dict(data.get("parameters", {})),
    )