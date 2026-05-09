"""
Write ``manifest.json`` entries under ``data/inquiries/`` so Inquiry Studio can index completed runs.

The CLI pipeline writes HTML under ``data/outputs/``; the library tab scans ``*/manifest.json`` only.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _relative_or_absolute(repo_root: Path, artifact: Path) -> str:
    artifact_resolved = artifact.resolve()
    root_resolved = repo_root.resolve()
    try:
        return artifact_resolved.relative_to(root_resolved).as_posix()
    except ValueError:
        return artifact_resolved.as_posix()


def write_inquiry_library_manifest(
    *,
    library_dir: Path,
    inquiry_id: str,
    title: str,
    youtube_url: str,
    paper_path: Path,
    repo_root: Path,
    audit_report_path: Path | None = None,
    status: str = "completed",
    parameters: dict[str, Any] | None = None,
) -> Path:
    """
    Persist a manifest discoverable by :func:`src.frontend.inquiry_studio.discover_inquiries`.
    """
    safe_id = inquiry_id.replace("/", "_").replace("\\", "_").strip()
    if not safe_id:
        raise ValueError("inquiry_id cannot be empty")

    inquiry_dir = Path(library_dir) / safe_id
    inquiry_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = inquiry_dir / "manifest.json"

    audit_rel = (
        _relative_or_absolute(repo_root, audit_report_path)
        if audit_report_path is not None
        else None
    )

    payload = {
        "inquiry_id": safe_id,
        "title": title,
        "youtube_url": youtube_url,
        "status": status,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "paper_path": _relative_or_absolute(repo_root, paper_path),
        "audit_report_path": audit_rel,
        "parameters": dict(parameters or {}),
    }

    manifest_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return manifest_path


def register_pipeline_outputs_for_studio(
    repo_root: Path,
    *,
    library_dir: Path,
    default_parameters: dict[str, Any] | None = None,
) -> Path:
    """
    Point the Inquiry Library at the standard outputs from ``youtube_paper`` / ``assemble_paper``.

    Prefers ``data/outputs/paper_spec.json`` embedded ``video`` (matches the assembled paper).
    Falls back to ``data/processed/source_registry.json`` when the spec has no video id.
    """
    root = repo_root.resolve()
    registry_path = root / "data" / "processed" / "source_registry.json"
    paper_spec_path = root / "data" / "outputs" / "paper_spec.json"
    html_path = root / "data" / "outputs" / "inquiry_paper.html"
    audit_path = root / "data" / "outputs" / "html_audit_report.json"

    if not html_path.is_file():
        raise FileNotFoundError(
            f"Missing HTML paper ({html_path}); complete assembly before registering."
        )

    title = "Untitled inquiry"
    video_id = ""
    youtube_url = ""

    if paper_spec_path.is_file():
        try:
            spec = json.loads(paper_spec_path.read_text(encoding="utf-8"))
            if isinstance(spec, dict):
                raw_title = spec.get("title")
                if isinstance(raw_title, str) and raw_title.strip():
                    title = raw_title.strip()
                video = spec.get("video")
                if isinstance(video, dict):
                    video_id = str(video.get("video_id", "")).strip()
                    youtube_url = str(video.get("url", "")).strip()
        except (json.JSONDecodeError, OSError):
            pass

    if not video_id and registry_path.is_file():
        try:
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            video_id = str(registry.get("video_id", "")).strip()
            youtube_url = str(registry.get("url", "")).strip()
        except (json.JSONDecodeError, OSError):
            pass

    if not video_id:
        raise ValueError(
            "Cannot register inquiry: no video_id in paper_spec.json video block "
            f"and missing or invalid {registry_path}."
        )

    inquiry_id = f"inquiry_{video_id}"

    audit_report_path: Path | None = audit_path if audit_path.is_file() else None

    if not youtube_url:
        youtube_url = f"https://www.youtube.com/watch?v={video_id}"

    params = {
        "retrieval_depth": 3,
        "source_tiers": [1, 2],
        "claim_type_filter": [],
        **(default_parameters or {}),
    }

    manifest_written = write_inquiry_library_manifest(
        library_dir=library_dir,
        inquiry_id=inquiry_id,
        title=title,
        youtube_url=youtube_url or f"https://www.youtube.com/watch?v={video_id}",
        paper_path=html_path,
        repo_root=root,
        audit_report_path=audit_report_path,
        parameters=params,
    )

    print(f"Inquiry Studio manifest written to: {manifest_written}")
    return manifest_written


def try_register_studio_library_after_assembly(repo_root: Path) -> None:
    """
    Best-effort registration so Inquiry Studio lists the latest assembled paper.

    Prints a short note when artifacts are missing or paths cannot be written.
    """
    root = repo_root.resolve()

    try:
        from src.frontend.studio_config import DEFAULT_STUDIO_CONFIG_PATH, load_studio_config

        cfg_path = root / DEFAULT_STUDIO_CONFIG_PATH
        studio_cfg = load_studio_config(cfg_path)
        library_root = Path(studio_cfg.inquiry_library_dir)
        if not library_root.is_absolute():
            library_root = root / studio_cfg.inquiry_library_dir
        register_pipeline_outputs_for_studio(root, library_dir=library_root)
    except (FileNotFoundError, ValueError, OSError, json.JSONDecodeError) as exc:
        print(
            "Note: Inquiry Studio library manifest was not updated "
            f"({exc}). The HTML paper is still under data/outputs/."
        )
