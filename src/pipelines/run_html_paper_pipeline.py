from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.paper.html_assembler import (
    PaperAdjudication,
    PaperClaim,
    PaperDocument,
    PaperEvidenceRecord,
    PaperVideo,
    write_html_paper,
)


class HtmlPaperPipelineError(ValueError):
    """Raised when HTML paper pipeline inputs are invalid."""


def run_html_paper_pipeline(
    *,
    paper_spec_path: str | Path,
    output_path: str | Path,
) -> Path:
    """
    Build the Week 8 HTML paper from a single paper spec JSON file.

    This runner is intentionally small. It does not perform evidence retrieval,
    steelmanning, or adjudication. It only assembles already-produced artifacts
    into the format-matched HTML document.
    """
    paper_spec = _load_json(paper_spec_path)
    document = _parse_paper_document(paper_spec)

    return write_html_paper(document, output_path)


def _load_json(path: str | Path) -> dict[str, Any]:
    target = Path(path)

    if not target.exists():
        raise HtmlPaperPipelineError(f"Paper spec file does not exist: {target}")

    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HtmlPaperPipelineError(f"Invalid JSON in paper spec: {target}") from exc

    if not isinstance(data, dict):
        raise HtmlPaperPipelineError("Paper spec must be a JSON object.")

    return data


def _parse_paper_document(data: dict[str, Any]) -> PaperDocument:
    required_fields = [
        "title",
        "abstract",
        "video",
        "speaker_perspective",
        "claims",
        "evidence_records",
        "adjudications",
    ]

    for field in required_fields:
        if field not in data:
            raise HtmlPaperPipelineError(f"Paper spec is missing required field: {field}")

    video = _parse_video(data["video"])
    claims = [_parse_claim(item) for item in data["claims"]]
    evidence_records = [_parse_evidence_record(item) for item in data["evidence_records"]]
    adjudications = [_parse_adjudication(item) for item in data["adjudications"]]

    limitations = data.get("limitations", [])
    if not isinstance(limitations, list):
        raise HtmlPaperPipelineError("limitations must be a list.")

    further_reading_raw = data.get("further_reading", [])
    if not isinstance(further_reading_raw, list):
        raise HtmlPaperPipelineError("further_reading must be a list.")

    further_reading = [_parse_evidence_record(item) for item in further_reading_raw]

    return PaperDocument(
        title=_required_string(data, "title"),
        abstract=_required_string(data, "abstract"),
        video=video,
        speaker_perspective=_required_string(data, "speaker_perspective"),
        claims=claims,
        evidence_records=evidence_records,
        adjudications=adjudications,
        limitations=[str(item) for item in limitations],
        further_reading=further_reading,
    )


def _parse_video(data: Any) -> PaperVideo:
    if not isinstance(data, dict):
        raise HtmlPaperPipelineError("video must be a JSON object.")

    return PaperVideo(
        video_id=_required_string(data, "video_id"),
        title=_required_string(data, "title"),
        url=_required_string(data, "url"),
        embed_base_url=_required_string(data, "embed_base_url"),
        speaker_name=_optional_string(data, "speaker_name"),
        speaker_credentials=_optional_string(data, "speaker_credentials"),
    )


def _parse_claim(data: Any) -> PaperClaim:
    if not isinstance(data, dict):
        raise HtmlPaperPipelineError("Each claim must be a JSON object.")

    return PaperClaim(
        claim_id=_required_string(data, "claim_id"),
        verbatim_quote=_required_string(data, "verbatim_quote"),
        claim_type=_required_string(data, "claim_type"),
        anchor_clip_start=_required_float(data, "anchor_clip_start"),
        anchor_clip_end=_required_float(data, "anchor_clip_end"),
        embed_url=_optional_string(data, "embed_url"),
    )


def _parse_evidence_record(data: Any) -> PaperEvidenceRecord:
    if not isinstance(data, dict):
        raise HtmlPaperPipelineError("Each evidence record must be a JSON object.")

    return PaperEvidenceRecord(
        evidence_id=_required_string(data, "evidence_id"),
        claim_id=_required_string(data, "claim_id"),
        title=_required_string(data, "title"),
        source=_required_string(data, "source"),
        url=_required_string(data, "url"),
        tier=_required_int(data, "tier"),
        stance=_required_string(data, "stance"),
        identifier=_optional_string(data, "identifier"),
        key_finding=_optional_string(data, "key_finding"),
    )


def _parse_adjudication(data: Any) -> PaperAdjudication:
    if not isinstance(data, dict):
        raise HtmlPaperPipelineError("Each adjudication must be a JSON object.")

    return PaperAdjudication(
        claim_id=_required_string(data, "claim_id"),
        verdict=_required_string(data, "verdict"),
        confidence=_required_string(data, "confidence"),
        narrative=_required_string(data, "narrative"),
        supports=_string_list(data.get("supports", []), "supports"),
        complicates=_string_list(data.get("complicates", []), "complicates"),
        contradicts=_string_list(data.get("contradicts", []), "contradicts"),
        qualifies=_string_list(data.get("qualifies", []), "qualifies"),
    )


def _required_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)

    if not isinstance(value, str) or not value.strip():
        raise HtmlPaperPipelineError(f"{key} must be a non-empty string.")

    return value


def _optional_string(data: dict[str, Any], key: str) -> str | None:
    value = data.get(key)

    if value is None:
        return None

    if not isinstance(value, str):
        raise HtmlPaperPipelineError(f"{key} must be a string when provided.")

    return value


def _required_float(data: dict[str, Any], key: str) -> float:
    value = data.get(key)

    if not isinstance(value, int | float):
        raise HtmlPaperPipelineError(f"{key} must be a number.")

    return float(value)


def _required_int(data: dict[str, Any], key: str) -> int:
    value = data.get(key)

    if not isinstance(value, int):
        raise HtmlPaperPipelineError(f"{key} must be an integer.")

    return value


def _string_list(value: Any, field_name: str) -> list[str]:
    if not isinstance(value, list):
        raise HtmlPaperPipelineError(f"{field_name} must be a list.")

    return [str(item) for item in value]