from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


RunStatus = Literal[
    "queued",
    "running",
    "completed",
    "failed",
]

AuditEventType = Literal[
    "video_registered",
    "speaker_registered",
    "claim_created",
    "evidence_created",
    "paper_created",
    "pipeline_started",
    "pipeline_completed",
    "pipeline_failed",
    "audit_requested",
]


def new_run_id() -> str:
    return f"run_{uuid4().hex[:12]}"


def new_audit_event_id() -> str:
    return f"audit_{uuid4().hex[:12]}"


class RunRecordCreate(BaseModel):
    video_id: str = Field(..., min_length=1)
    pipeline_name: str = Field(default="week6_backend")
    pipeline_config: Dict[str, Any] = Field(default_factory=dict)
    input_artifacts: Dict[str, str] = Field(default_factory=dict)


class RunRecordRead(BaseModel):
    id: str
    video_id: str
    pipeline_name: str
    status: RunStatus
    pipeline_config: Dict[str, Any] = Field(default_factory=dict)
    input_artifacts: Dict[str, str] = Field(default_factory=dict)
    output_artifacts: Dict[str, str] = Field(default_factory=dict)
    started_at: datetime
    finished_at: Optional[datetime] = None
    error_message: Optional[str] = None


class AuditEventCreate(BaseModel):
    run_id: Optional[str] = None
    video_id: Optional[str] = None
    event_type: AuditEventType
    message: str = Field(..., min_length=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AuditEventRead(BaseModel):
    id: str
    run_id: Optional[str] = None
    video_id: Optional[str] = None
    event_type: AuditEventType
    message: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
