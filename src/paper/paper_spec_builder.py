from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class PaperSpecBuilderError(ValueError):
    """Raised when upstream artifacts cannot produce a valid paper spec."""


def build_paper_spec(
    *,
    source_registry_path: str | Path,
    claim_inventory_path: str | Path,
    evidence_integration_path: str | Path,
    output_path: str | Path,
    title: str | None = None,
    abstract: str | None = None,
) -> Path:
    """
    Build the Week 8 paper_spec.json from upstream pipeline artifacts.

    Expected inputs:
    - source registry from Week 1
    - claim inventory from Week 3
    - evidence integration output from Week 7
    """
    source_registry = _load_json_object(source_registry_path, "source registry")
    claim_inventory = _load_json_object(claim_inventory_path, "claim inventory")
    evidence_integration = _load_json_object(
        evidence_integration_path,
        "evidence integration",
    )

    spec = build_paper_spec_dict(
        source_registry=source_registry,
        claim_inventory=claim_inventory,
        evidence_integration=evidence_integration,
        title=title,
        abstract=abstract,
    )

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(spec, indent=2), encoding="utf-8")

    return target


def build_paper_spec_dict(
    *,
    source_registry: dict[str, Any],
    claim_inventory: dict[str, Any],
    evidence_integration: dict[str, Any],
    title: str | None = None,
    abstract: str | None = None,
) -> dict[str, Any]:
    video = _parse_video(source_registry)

    claims = _parse_claims(claim_inventory)
    evidence_records = _parse_evidence_records(evidence_integration)
    adjudications = _parse_adjudications(evidence_integration)

    speaker_perspective = _parse_speaker_perspective(evidence_integration)
    limitations = _parse_limitations(evidence_integration)

    return {
        "title": title or f"Inquiry Paper: {video['title']}",
        "abstract": abstract
        or "A charitable, evidence-balanced inquiry generated from a source video.",
        "video": video,
        "speaker_perspective": speaker_perspective,
        "claims": claims,
        "evidence_records": evidence_records,
        "adjudications": adjudications,
        "limitations": limitations,
        "further_reading": _build_further_reading(evidence_records),
    }


def _load_json_object(path: str | Path, artifact_name: str) -> dict[str, Any]:
    target = Path(path)

    if not target.exists():
        raise PaperSpecBuilderError(f"Missing {artifact_name} file: {target}")

    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PaperSpecBuilderError(f"Invalid JSON in {artifact_name}: {target}") from exc

    if not isinstance(data, dict):
        raise PaperSpecBuilderError(f"{artifact_name} must be a JSON object.")

    return data


def _parse_video(source_registry: dict[str, Any]) -> dict[str, Any]:
    source = source_registry.get("source", source_registry)

    if not isinstance(source, dict):
        raise PaperSpecBuilderError("source registry must contain a source object.")

    speaker = source.get("speaker", {})
    if speaker is None:
        speaker = {}

    if not isinstance(speaker, dict):
        raise PaperSpecBuilderError("speaker must be an object when provided.")

    return {
        "video_id": _required_string(source, "video_id"),
        "title": _required_string(source, "title"),
        "url": _required_string(source, "url"),
        "embed_base_url": _required_string(source, "embed_base_url"),
        "speaker_name": _optional_string(speaker, "name"),
        "speaker_credentials": _optional_string(speaker, "credentials"),
    }


def _parse_claims(claim_inventory: dict[str, Any]) -> list[dict[str, Any]]:
    raw_claims = claim_inventory.get("claims", claim_inventory.get("claim_inventory", []))

    if not isinstance(raw_claims, list):
        raise PaperSpecBuilderError("claim inventory must contain a claims list.")

    claims: list[dict[str, Any]] = []

    for item in raw_claims:
        if not isinstance(item, dict):
            raise PaperSpecBuilderError("Each claim must be an object.")

        anchor_clip = item.get("anchor_clip", {})
        if not isinstance(anchor_clip, dict):
            raise PaperSpecBuilderError("Each claim anchor_clip must be an object.")

        claims.append(
            {
                "claim_id": _required_string(item, "claim_id"),
                "verbatim_quote": _required_string(item, "verbatim_quote"),
                "claim_type": _required_string(item, "claim_type"),
                "anchor_clip_start": _required_number(anchor_clip, "start"),
                "anchor_clip_end": _required_number(anchor_clip, "end"),
                "embed_url": _optional_string(item, "embed_url"),
            }
        )

    if not claims:
        raise PaperSpecBuilderError("Cannot build a paper spec without claims.")

    return claims


def _parse_evidence_records(evidence_integration: dict[str, Any]) -> list[dict[str, Any]]:
    raw_records = evidence_integration.get("evidence_records", [])

    if not isinstance(raw_records, list):
        raise PaperSpecBuilderError("evidence_records must be a list.")

    records: list[dict[str, Any]] = []

    for item in raw_records:
        if not isinstance(item, dict):
            raise PaperSpecBuilderError("Each evidence record must be an object.")

        records.append(
            {
                "evidence_id": _required_string(item, "evidence_id"),
                "claim_id": _required_string(item, "claim_id"),
                "title": _required_string(item, "title"),
                "source": _required_string(item, "source"),
                "url": _required_string(item, "url"),
                "tier": _required_int(item, "tier"),
                "stance": _required_string(item, "stance"),
                "identifier": _optional_string(item, "identifier"),
                "key_finding": _optional_string(item, "key_finding"),
            }
        )

    return records


def _parse_adjudications(evidence_integration: dict[str, Any]) -> list[dict[str, Any]]:
    raw_adjudications = evidence_integration.get("adjudications", [])

    if not isinstance(raw_adjudications, list):
        raise PaperSpecBuilderError("adjudications must be a list.")

    adjudications: list[dict[str, Any]] = []

    for item in raw_adjudications:
        if not isinstance(item, dict):
            raise PaperSpecBuilderError("Each adjudication must be an object.")

        adjudications.append(
            {
                "claim_id": _required_string(item, "claim_id"),
                "verdict": _required_string(item, "verdict"),
                "confidence": _required_string(item, "confidence"),
                "narrative": _required_string(item, "narrative"),
                "supports": _string_list(item.get("supports", []), "supports"),
                "complicates": _string_list(item.get("complicates", []), "complicates"),
                "contradicts": _string_list(item.get("contradicts", []), "contradicts"),
                "qualifies": _string_list(item.get("qualifies", []), "qualifies"),
            }
        )

    return adjudications


def _parse_speaker_perspective(evidence_integration: dict[str, Any]) -> str:
    value = evidence_integration.get("speaker_perspective")

    if isinstance(value, str) and value.strip():
        return value

    steelman = evidence_integration.get("steelman")

    if isinstance(steelman, dict):
        narrative_blocks = steelman.get("narrative_blocks", [])
        if isinstance(narrative_blocks, list):
            texts = [
                block.get("text", "")
                for block in narrative_blocks
                if isinstance(block, dict) and isinstance(block.get("text"), str)
            ]

            joined = "\n\n".join(text.strip() for text in texts if text.strip())
            if joined:
                return joined

    return (
        "The speaker perspective section has not yet been generated. "
        "This placeholder preserves the paper structure while upstream steelmanning is completed."
    )


def _parse_limitations(evidence_integration: dict[str, Any]) -> list[str]:
    limitations = evidence_integration.get("limitations", [])

    if limitations is None:
        return []

    if not isinstance(limitations, list):
        raise PaperSpecBuilderError("limitations must be a list.")

    return [str(item) for item in limitations]


def _build_further_reading(
    evidence_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    # Keep this simple for Week 8. Week 9 can add filtering and source-tier UI.
    return sorted(
        evidence_records,
        key=lambda record: (record.get("tier", 999), record.get("title", "")),
    )


def _required_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)

    if not isinstance(value, str) or not value.strip():
        raise PaperSpecBuilderError(f"{key} must be a non-empty string.")

    return value


def _optional_string(data: dict[str, Any], key: str) -> str | None:
    value = data.get(key)

    if value is None:
        return None

    if not isinstance(value, str):
        raise PaperSpecBuilderError(f"{key} must be a string when provided.")

    return value


def _required_number(data: dict[str, Any], key: str) -> float:
    value = data.get(key)

    if not isinstance(value, int | float):
        raise PaperSpecBuilderError(f"{key} must be a number.")

    return float(value)


def _required_int(data: dict[str, Any], key: str) -> int:
    value = data.get(key)

    if not isinstance(value, int):
        raise PaperSpecBuilderError(f"{key} must be an integer.")

    return value


def _string_list(value: Any, field_name: str) -> list[str]:
    if not isinstance(value, list):
        raise PaperSpecBuilderError(f"{field_name} must be a list.")

    return [str(item) for item in value]