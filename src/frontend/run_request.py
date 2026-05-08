from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

DEFAULT_PIPELINE_STAGES = [
    "source_ingestion",
    "argument_structure",
    "claim_inventory",
    "steelman",
    "evidence_retrieval",
    "evidence_integration",
    "html_assembly",
    "interactive_components",
    "evaluation",
]


@dataclass(frozen=True)
class InquiryRunRequest:
    request_id: str
    created_at: str
    youtube_url: str
    video_id: str
    claim_type_filter: list[str]
    retrieval_depth: int
    source_tiers: list[int]
    stages: list[str]
    rerun_of: str | None = None
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "created_at": self.created_at,
            "youtube_url": self.youtube_url,
            "video_id": self.video_id,
            "claim_type_filter": self.claim_type_filter,
            "retrieval_depth": self.retrieval_depth,
            "source_tiers": self.source_tiers,
            "stages": self.stages,
            "rerun_of": self.rerun_of,
            "reason": self.reason,
            "metadata": self.metadata,
        }


def create_inquiry_run_request(
    *,
    youtube_url: str,
    claim_type_filter: list[str],
    retrieval_depth: int,
    source_tiers: list[int],
    stages: list[str] | None = None,
    rerun_of: str | None = None,
    reason: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> InquiryRunRequest:
    from src.frontend.inquiry_studio import build_run_parameters

    params = build_run_parameters(
        youtube_url=youtube_url,
        claim_type_filter=claim_type_filter,
        retrieval_depth=retrieval_depth,
        source_tiers=source_tiers,
    )

    selected_stages = list(stages or DEFAULT_PIPELINE_STAGES)
    validate_pipeline_stages(selected_stages)

    return InquiryRunRequest(
        request_id=f"request_{uuid4().hex}",
        created_at=datetime.now(timezone.utc).isoformat(),
        youtube_url=params.youtube_url,
        video_id=params.video_id,
        claim_type_filter=params.claim_type_filter,
        retrieval_depth=params.retrieval_depth,
        source_tiers=params.source_tiers,
        stages=selected_stages,
        rerun_of=_optional_string(rerun_of),
        reason=_optional_string(reason),
        metadata=metadata or {},
    )


def validate_pipeline_stages(stages: list[str]) -> None:
    if not stages:
        raise ValueError("At least one pipeline stage must be selected.")

    allowed = set(DEFAULT_PIPELINE_STAGES)
    invalid = [stage for stage in stages if stage not in allowed]

    if invalid:
        raise ValueError(f"Invalid pipeline stages: {', '.join(invalid)}")


def save_run_request(
    request: InquiryRunRequest,
    output_dir: str | Path,
) -> Path:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    output_path = root / f"{request.request_id}.json"

    output_path.write_text(
        json.dumps(request.to_dict(), indent=2),
        encoding="utf-8",
    )

    return output_path


def load_run_request(path: str | Path) -> InquiryRunRequest:
    request_path = Path(path)

    with request_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("Run request file must contain a JSON object.")

    return run_request_from_dict(data)


def run_request_from_dict(data: dict[str, Any]) -> InquiryRunRequest:
    required_fields = [
        "request_id",
        "created_at",
        "youtube_url",
        "video_id",
        "claim_type_filter",
        "retrieval_depth",
        "source_tiers",
        "stages",
    ]

    missing = [field_name for field_name in required_fields if field_name not in data]

    if missing:
        raise ValueError(f"Run request is missing fields: {', '.join(missing)}")

    stages = list(data["stages"])
    validate_pipeline_stages(stages)

    return InquiryRunRequest(
        request_id=str(data["request_id"]),
        created_at=str(data["created_at"]),
        youtube_url=str(data["youtube_url"]),
        video_id=str(data["video_id"]),
        claim_type_filter=list(data["claim_type_filter"]),
        retrieval_depth=int(data["retrieval_depth"]),
        source_tiers=[int(tier) for tier in data["source_tiers"]],
        stages=stages,
        rerun_of=_optional_string(data.get("rerun_of")),
        reason=_optional_string(data.get("reason")),
        metadata=dict(data.get("metadata", {})),
    )


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    return text or None