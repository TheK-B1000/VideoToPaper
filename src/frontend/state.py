from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, MutableMapping


DEFAULT_BACKEND_BASE_URL = "http://127.0.0.1:8000"
LAST_ACTION_SESSION_KEY = "studio_last_action"


@dataclass(frozen=True)
class StudioStateField:
    session_key: str
    query_param: str
    default: str
    allowed_values: tuple[str, ...] | None = None
    persist_to_query: bool = True


@dataclass(frozen=True)
class StudioViewState:
    library_query: str = ""
    library_status: str = "all"
    request_query: str = ""
    request_status: str = "all"
    audit_report_path: str = ""
    progress_log_path: str = ""
    activity_query: str = ""
    activity_type: str = "all"
    backend_run_id: str = ""
    backend_base_url: str = DEFAULT_BACKEND_BASE_URL
    backend_inquiry_id: str = ""

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class LastAction:
    title: str
    message: str
    status: str = "info"
    details: dict[str, Any] = field(default_factory=dict)
    artifact_path: str | None = None
    created_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LastAction":
        details = payload.get("details", {})

        if not isinstance(details, dict):
            details = {}

        return cls(
            title=str(payload.get("title", "")),
            message=str(payload.get("message", "")),
            status=str(payload.get("status", "info")),
            details=details,
            artifact_path=_optional_string(payload.get("artifact_path")),
            created_at=_optional_string(payload.get("created_at")),
        )


STUDIO_STATE_FIELDS: dict[str, StudioStateField] = {
    "library_query": StudioStateField(
        session_key="studio_library_query",
        query_param="library_query",
        default="",
    ),
    "library_status": StudioStateField(
        session_key="studio_library_status",
        query_param="library_status",
        default="all",
        allowed_values=("all", "completed", "failed", "running", "queued"),
    ),
    "request_query": StudioStateField(
        session_key="studio_request_query",
        query_param="request_query",
        default="",
    ),
    "request_status": StudioStateField(
        session_key="studio_request_status",
        query_param="request_status",
        default="all",
        allowed_values=("all", "pending", "queued", "running", "completed", "failed"),
    ),
    "audit_report_path": StudioStateField(
        session_key="studio_audit_report_path",
        query_param="audit_path",
        default="",
    ),
    "progress_log_path": StudioStateField(
        session_key="studio_progress_log_path",
        query_param="progress_path",
        default="",
    ),
    "activity_query": StudioStateField(
        session_key="studio_activity_query",
        query_param="activity_query",
        default="",
    ),
    "activity_type": StudioStateField(
        session_key="studio_activity_type",
        query_param="activity_type",
        default="all",
    ),
    "backend_run_id": StudioStateField(
        session_key="studio_backend_run_id",
        query_param="backend_run_id",
        default="",
    ),
    "backend_base_url": StudioStateField(
        session_key="studio_backend_base_url",
        query_param="backend_base_url",
        default=DEFAULT_BACKEND_BASE_URL,
    ),
    "backend_inquiry_id": StudioStateField(
        session_key="studio_backend_inquiry_id",
        query_param="backend_inquiry_id",
        default="",
    ),
}

STUDIO_SESSION_KEYS = {
    field_name: field_definition.session_key
    for field_name, field_definition in STUDIO_STATE_FIELDS.items()
}


def initialize_studio_state(
    session_state: MutableMapping[str, Any],
    query_params: Mapping[str, Any],
    *,
    defaults: Mapping[str, str] | None = None,
) -> StudioViewState:
    normalized_query = normalize_query_params(query_params)
    resolved_defaults = defaults or {}

    for field_name, field_definition in STUDIO_STATE_FIELDS.items():
        default = _field_default(field_name, field_definition, resolved_defaults)

        if field_definition.session_key in session_state:
            value = session_state[field_definition.session_key]
        else:
            value = normalized_query.get(field_definition.query_param, default)

        session_state[field_definition.session_key] = _normalize_field_value(
            field_definition,
            value,
            default=default,
        )

    return read_studio_view_state(session_state, defaults=resolved_defaults)


def read_studio_view_state(
    session_state: Mapping[str, Any],
    *,
    defaults: Mapping[str, str] | None = None,
) -> StudioViewState:
    resolved_defaults = defaults or {}
    values: dict[str, str] = {}

    for field_name, field_definition in STUDIO_STATE_FIELDS.items():
        default = _field_default(field_name, field_definition, resolved_defaults)
        values[field_name] = _normalize_field_value(
            field_definition,
            session_state.get(field_definition.session_key, default),
            default=default,
        )

    return StudioViewState(**values)


def persist_studio_state_to_query_params(
    session_state: Mapping[str, Any],
    query_params: MutableMapping[str, Any],
    *,
    defaults: Mapping[str, str] | None = None,
) -> None:
    resolved_defaults = defaults or {}

    for field_name, field_definition in STUDIO_STATE_FIELDS.items():
        if not field_definition.persist_to_query:
            continue

        default = _field_default(field_name, field_definition, resolved_defaults)
        value = _normalize_field_value(
            field_definition,
            session_state.get(field_definition.session_key, default),
            default=default,
        )

        if not value or value == default:
            _remove_query_param(query_params, field_definition.query_param)
        else:
            _set_query_param(query_params, field_definition.query_param, value)


def normalize_query_params(query_params: Mapping[str, Any]) -> dict[str, str]:
    normalized: dict[str, str] = {}

    for key, value in query_params.items():
        normalized[str(key)] = _first_query_value(value)

    return normalized


def record_last_action(
    session_state: MutableMapping[str, Any],
    *,
    title: str,
    message: str,
    status: str = "info",
    details: Mapping[str, Any] | None = None,
    artifact_path: str | None = None,
    created_at: str | None = None,
) -> LastAction:
    action = LastAction(
        title=title,
        message=message,
        status=status,
        details=dict(details or {}),
        artifact_path=artifact_path,
        created_at=created_at or _utc_timestamp(),
    )

    set_last_action(session_state, action)
    return action


def set_last_action(
    session_state: MutableMapping[str, Any],
    action: LastAction,
) -> None:
    session_state[LAST_ACTION_SESSION_KEY] = action.to_dict()


def get_last_action(session_state: Mapping[str, Any]) -> LastAction | None:
    payload = session_state.get(LAST_ACTION_SESSION_KEY)

    if payload is None:
        return None

    if isinstance(payload, LastAction):
        return payload

    if isinstance(payload, Mapping):
        action = LastAction.from_dict(payload)
        return action if action.title or action.message else None

    return None


def clear_last_action(session_state: MutableMapping[str, Any]) -> None:
    session_state.pop(LAST_ACTION_SESSION_KEY, None)


def _field_default(
    field_name: str,
    field_definition: StudioStateField,
    defaults: Mapping[str, str],
) -> str:
    return str(defaults.get(field_name, field_definition.default))


def _normalize_field_value(
    field_definition: StudioStateField,
    value: Any,
    *,
    default: str,
) -> str:
    normalized = _first_query_value(value).strip()

    if (
        field_definition.allowed_values
        and normalized not in field_definition.allowed_values
    ):
        return default

    return normalized


def _first_query_value(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        if not value:
            return ""

        return str(value[0])

    if value is None:
        return ""

    return str(value)


def _set_query_param(
    query_params: MutableMapping[str, Any],
    key: str,
    value: str,
) -> None:
    current_value = normalize_query_params(query_params).get(key)

    if current_value == value:
        return

    query_params[key] = value


def _remove_query_param(
    query_params: MutableMapping[str, Any],
    key: str,
) -> None:
    if key not in query_params:
        return

    del query_params[key]


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    return text or None


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00",
        "Z",
    )


__all__ = [
    "DEFAULT_BACKEND_BASE_URL",
    "LAST_ACTION_SESSION_KEY",
    "LastAction",
    "STUDIO_SESSION_KEYS",
    "STUDIO_STATE_FIELDS",
    "StudioStateField",
    "StudioViewState",
    "clear_last_action",
    "get_last_action",
    "initialize_studio_state",
    "normalize_query_params",
    "persist_studio_state_to_query_params",
    "record_last_action",
    "set_last_action",
]
