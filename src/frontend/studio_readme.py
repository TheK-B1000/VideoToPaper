from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.frontend.studio_config import StudioConfig


@dataclass(frozen=True)
class StudioReadme:
    title: str
    content: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "content": self.content,
        }


def build_studio_readme(config: StudioConfig) -> StudioReadme:
    audit_path = config.default_audit_report_path or "not configured"
    progress_path = config.default_progress_log_path or "not configured"

    content = f"""# Inquiry Studio

Inquiry Studio is the local operator surface for the Inquiry Engine. It lets an operator prepare inquiry runs, browse prior inquiries, inspect audit reports, open generated HTML papers, monitor run progress, and connect to the backend API when available.

## Run the Studio

```bash
streamlit run src/frontend/inquiry_studio.py
```

## Configured Paths

- Inquiry library: `{config.inquiry_library_dir}`
- Run requests queue: `{config.run_requests_dir}`
- Local runs directory: `{config.runs_dir}`
- Operator activity log: `{config.operator_activity_log_path}`
- Default audit report path: `{audit_path}`
- Default progress log path: `{progress_path}`
- Backend base URL: `{config.backend_base_url or "not configured"}`
- Backend timeout (seconds): `{config.backend_timeout_seconds}`

## Operator workflow

1. Submit a YouTube URL from the sidebar.
2. Review created requests in **Run Requests**.
3. Launch locally or submit to backend.
4. Inspect reports in **Audit Inspector**.
5. Watch execution updates in **Run Progress**.
6. Review readiness in **Health Check**.

## Completion standard

A run is considered complete when:
- a manifest exists in the inquiry library,
- generated paper and audit artifacts are discoverable, and
- activity log captures major operator actions.
"""

    return StudioReadme(
        title="Inquiry Studio README",
        content=content,
    )


def write_studio_readme(
    config: StudioConfig,
    *,
    output_path: str | Path = "docs/inquiry_studio.md",
) -> Path:
    readme = build_studio_readme(config)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(readme.content, encoding="utf-8")
    return path