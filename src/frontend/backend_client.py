from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib import error, request

from src.frontend.models.run import InquiryRunRequest


@dataclass(frozen=True)
class BackendResponse:
    status_code: int
    ok: bool
    data: dict[str, Any]
    error_message: str | None = None

    @property
    def request_id(self) -> str | None:
        value = self.data.get("request_id")
        return str(value) if value is not None else None

    @property
    def run_id(self) -> str | None:
        value = self.data.get("run_id")
        return str(value) if value is not None else None


@dataclass(frozen=True)
class BackendClientConfig:
    base_url: str
    timeout_seconds: float = 10.0

    @property
    def normalized_base_url(self) -> str:
        return self.base_url.rstrip("/")


class BackendClient:
    def __init__(self, config: BackendClientConfig) -> None:
        if not config.base_url.strip():
            raise ValueError("Backend base_url cannot be empty.")

        self.config = config

    def health_check(self) -> BackendResponse:
        return self._get("/health")

    def submit_run_request(self, run_request: InquiryRunRequest) -> BackendResponse:
        return self._post(
            "/inquiries/run",
            payload=run_request.to_dict(),
        )

    def get_run_progress(self, run_id: str) -> BackendResponse:
        if not run_id.strip():
            raise ValueError("run_id cannot be empty.")

        return self._get(f"/runs/{run_id}/progress")

    def get_inquiry_manifest(self, inquiry_id: str) -> BackendResponse:
        if not inquiry_id.strip():
            raise ValueError("inquiry_id cannot be empty.")

        return self._get(f"/inquiries/{inquiry_id}")

    def _get(self, path: str) -> BackendResponse:
        url = self._build_url(path)
        req = request.Request(url, method="GET")

        return self._send(req)

    def _post(self, path: str, payload: dict[str, Any]) -> BackendResponse:
        url = self._build_url(path)
        body = json.dumps(payload).encode("utf-8")

        req = request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )

        return self._send(req)

    def _send(self, req: request.Request) -> BackendResponse:
        try:
            with request.urlopen(
                req,
                timeout=self.config.timeout_seconds,
            ) as response:
                status_code = int(response.status)
                body = response.read().decode("utf-8")
                data = _parse_json_object(body)

                return BackendResponse(
                    status_code=status_code,
                    ok=200 <= status_code < 300,
                    data=data,
                )

        except error.HTTPError as http_error:
            body = http_error.read().decode("utf-8")
            data = _parse_json_object(body, fallback={})

            return BackendResponse(
                status_code=int(http_error.code),
                ok=False,
                data=data,
                error_message=_extract_error_message(data)
                or http_error.reason
                or "HTTP error.",
            )

        except error.URLError as url_error:
            return BackendResponse(
                status_code=0,
                ok=False,
                data={},
                error_message=str(url_error.reason),
            )

        except TimeoutError:
            return BackendResponse(
                status_code=0,
                ok=False,
                data={},
                error_message="Backend request timed out.",
            )

    def _build_url(self, path: str) -> str:
        clean_path = path if path.startswith("/") else f"/{path}"
        return f"{self.config.normalized_base_url}{clean_path}"


def _parse_json_object(
    body: str,
    *,
    fallback: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not body.strip():
        return fallback or {}

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return fallback or {"raw_body": body}

    if isinstance(parsed, dict):
        return parsed

    return fallback or {"value": parsed}


def _extract_error_message(data: dict[str, Any]) -> str | None:
    for key in ["detail", "error", "message"]:
        value = data.get(key)

        if value:
            return str(value)

    return None
