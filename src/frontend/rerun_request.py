from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, TYPE_CHECKING

from src.frontend.run_request import (
    InquiryRunRequest,
    create_inquiry_run_request,
    save_run_request,
)

if TYPE_CHECKING:
    from src.frontend.inquiry_studio import InquiryRecord


@dataclass(frozen=True)
class RerunOverrides:
    claim_type_filter: list[str] | None = None
    retrieval_depth: int | None = None
    source_tiers: list[int] | None = None
    stages: list[str] | None = None
    reason: str | None = None
    metadata: dict[str, Any] | None = None


def create_rerun_from_inquiry_record(
    record: "InquiryRecord",
    *,
    overrides: RerunOverrides,
) -> InquiryRunRequest:
    """
    Create a rerun request from a completed inquiry manifest.

    The rerun preserves the source video and original inquiry id while allowing
    the operator to adjust parameters such as retrieval depth, source tiers,
    claim types, or selected pipeline stages.
    """
    original_parameters = record.parameters

    claim_type_filter = _resolve_list(
        overrides.claim_type_filter,
        original_parameters.get("claim_type_filter"),
        default=["empirical_technical", "empirical_historical", "empirical_scientific"],
    )

    retrieval_depth = int(
        overrides.retrieval_depth
        if overrides.retrieval_depth is not None
        else original_parameters.get("retrieval_depth", 3)
    )

    source_tiers = [
        int(tier)
        for tier in _resolve_list(
            overrides.source_tiers,
            original_parameters.get("source_tiers"),
            default=[1, 2],
        )
    ]

    stages = _resolve_optional_list(
        overrides.stages,
        original_parameters.get("stages"),
    )

    metadata = {
        "created_from": "streamlit_inquiry_studio_rerun",
        "original_inquiry_id": record.inquiry_id,
        "original_title": record.title,
        "original_status": record.status,
    }

    if overrides.metadata:
        metadata.update(overrides.metadata)

    return create_inquiry_run_request(
        youtube_url=record.youtube_url,
        claim_type_filter=[str(item) for item in claim_type_filter],
        retrieval_depth=retrieval_depth,
        source_tiers=source_tiers,
        stages=[str(stage) for stage in stages] if stages is not None else None,
        rerun_of=record.inquiry_id,
        reason=overrides.reason or "Operator requested rerun with adjusted parameters.",
        metadata=metadata,
    )


def create_rerun_from_run_request(
    request: InquiryRunRequest,
    *,
    overrides: RerunOverrides,
) -> InquiryRunRequest:
    """
    Create a rerun request from a previous request.

    This is useful when a request failed before becoming a completed inquiry.
    """
    claim_type_filter = (
        overrides.claim_type_filter
        if overrides.claim_type_filter is not None
        else request.claim_type_filter
    )

    retrieval_depth = (
        overrides.retrieval_depth
        if overrides.retrieval_depth is not None
        else request.retrieval_depth
    )

    source_tiers = (
        overrides.source_tiers
        if overrides.source_tiers is not None
        else request.source_tiers
    )

    stages = overrides.stages if overrides.stages is not None else request.stages

    metadata = {
        "created_from": "streamlit_inquiry_studio_request_rerun",
        "original_request_id": request.request_id,
        "original_video_id": request.video_id,
    }

    if overrides.metadata:
        metadata.update(overrides.metadata)

    return create_inquiry_run_request(
        youtube_url=request.youtube_url,
        claim_type_filter=claim_type_filter,
        retrieval_depth=int(retrieval_depth),
        source_tiers=[int(tier) for tier in source_tiers],
        stages=stages,
        rerun_of=request.request_id,
        reason=overrides.reason or "Operator requested rerun from prior request.",
        metadata=metadata,
    )


def save_rerun_request(
    request: InquiryRunRequest,
    *,
    output_dir: str | Path = "data/run_requests",
) -> Path:
    return save_run_request(request, output_dir)


def _resolve_list(
    override_value: list[Any] | None,
    original_value: Any,
    *,
    default: list[Any],
) -> list[Any]:
    if override_value is not None:
        return list(override_value)

    if isinstance(original_value, list):
        return list(original_value)

    return list(default)


def _resolve_optional_list(
    override_value: list[Any] | None,
    original_value: Any,
) -> list[Any] | None:
    if override_value is not None:
        return list(override_value)

    if isinstance(original_value, list):
        return list(original_value)

    return None