from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any, Iterable

from src.frontend.models.inquiry import (
    InquiryRecord,
    RunParameters,
    build_run_parameters,
    parse_youtube_video_id,
)
from src.frontend.run_progress import load_run_progress, summarize_progress
from src.frontend.run_queue import (
    discover_run_requests,
    filter_queued_requests,
    summarize_queue,
)
from src.frontend.local_runner import launch_local_run
from src.frontend.audit_summary import summarize_audit_report
from src.frontend.backend_client import BackendClient, BackendClientConfig
from src.frontend.backend_inquiry_import import import_backend_inquiry
from src.frontend.backend_progress_sync import sync_backend_progress
from src.frontend.backend_submission import submit_queued_request_to_backend
from src.frontend.operator_activity import (
    VALID_ACTIVITY_TYPES,
    filter_activities,
    read_activity_log,
    record_activity,
)
from src.frontend.paper_artifacts import build_file_url, inspect_paper_artifact
from src.frontend.queue_status import mark_request_queued, mark_request_running
from src.frontend.rerun_request import (
    RerunOverrides,
    create_rerun_from_inquiry_record,
    save_rerun_request,
)
from src.frontend.run_request import (
    DEFAULT_PIPELINE_STAGES,
    create_inquiry_run_request,
    save_run_request,
)
from src.frontend.studio_config import ensure_studio_directories, load_studio_config
from src.frontend.studio_health import run_studio_health_checks
from src.frontend.studio_readme import write_studio_readme
from src.frontend.studio_smoke import run_studio_smoke_test
from src.frontend.state import (
    DEFAULT_BACKEND_BASE_URL,
    LastAction,
    STUDIO_SESSION_KEYS,
    get_last_action,
    initialize_studio_state,
    persist_studio_state_to_query_params,
    record_last_action,
)

STUDIO_ENVIRONMENT = "Local"


STATUS_TONES = {
    "pass": "success",
    "ready": "success",
    "healthy": "success",
    "publishable": "success",
    "completed": "success",
    "queued": "warning",
    "pending": "warning",
    "running": "info",
    "warning": "warning",
    "needs_attention": "danger",
    "not_publishable": "danger",
    "success": "success",
    "failed": "danger",
    "fail": "danger",
    "info": "info",
    "error": "danger",
}

METRIC_TONES = {"success", "warning", "danger", "info", "neutral"}


def render_studio_css() -> str:
    return """
<style>
  :root {
    --studio-primary: #1f4f46;
    --studio-primary-strong: #173d36;
    --studio-accent: #d99735;
    --studio-bg: #f6f7f4;
    --studio-surface: #ffffff;
    --studio-ink: #111827;
    --studio-muted: #4b5563;
    --studio-line: rgba(17, 24, 39, 0.12);
    --studio-success: #16794c;
    --studio-warning: #a16207;
    --studio-danger: #b42318;
    --studio-info: #1d4ed8;
  }

  .block-container {
    padding-top: 1.4rem;
    padding-bottom: 3rem;
  }

  div[data-testid="stTabs"] button {
    font-weight: 700;
    min-height: 46px;
  }

  div[data-testid="stButton"] button,
  div[data-testid="stLinkButton"] a {
    min-height: 42px;
    border-radius: 10px;
    font-weight: 700;
  }

  .studio-brand-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding: 1.1rem 1.25rem;
    border: 1px solid var(--studio-line);
    border-radius: 16px;
    background: var(--studio-surface);
    margin-bottom: 1rem;
  }

  .studio-brand-left {
    display: flex;
    align-items: center;
    gap: 0.9rem;
  }

  .studio-mark {
    width: 48px;
    height: 48px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 14px;
    background: var(--studio-primary);
    color: white;
    font-size: 1.45rem;
  }

  /* Streamlit theme CSS often wins on bare h1/p; scope + !important keeps header readable. */
  [data-testid="stMarkdownContainer"] .studio-brand-row .studio-title,
  .studio-brand-row .studio-title {
    margin: 0;
    color: var(--studio-ink) !important;
    font-size: 1.55rem;
    line-height: 1.1;
    font-weight: 800 !important;
    letter-spacing: -0.02em;
  }

  [data-testid="stMarkdownContainer"] .studio-brand-row .studio-subtitle,
  .studio-brand-row .studio-subtitle {
    margin: 0.25rem 0 0;
    color: var(--studio-muted) !important;
    font-size: 0.95rem;
    font-weight: 500;
  }

  .studio-badge-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    justify-content: flex-end;
  }

  .studio-badge,
  .state-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    border-radius: 999px;
    border: 1px solid var(--studio-line);
    padding: 0.26rem 0.62rem;
    font-size: 0.75rem;
    font-weight: 800;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    white-space: nowrap;
  }

  .studio-badge {
    background: #f8fafc;
    color: var(--studio-ink);
  }

  .state-chip--success {
    color: var(--studio-success);
    background: #ecfdf3;
    border-color: rgba(22, 121, 76, 0.2);
  }

  .state-chip--warning {
    color: var(--studio-warning);
    background: #fffbeb;
    border-color: rgba(161, 98, 7, 0.22);
  }

  .state-chip--danger {
    color: var(--studio-danger);
    background: #fff1f0;
    border-color: rgba(180, 35, 24, 0.22);
  }

  .state-chip--info {
    color: var(--studio-info);
    background: #eff6ff;
    border-color: rgba(29, 78, 216, 0.2);
  }

  .state-chip--neutral {
    color: var(--studio-muted);
    background: #f3f4f6;
  }

  .studio-hero {
    border: 1px solid rgba(31, 79, 70, 0.18);
    border-radius: 18px;
    padding: 1.35rem;
    background:
      linear-gradient(135deg, rgba(31, 79, 70, 0.1), rgba(217, 151, 53, 0.12)),
      var(--studio-surface);
    margin-bottom: 1rem;
  }

  [data-testid="stMarkdownContainer"] .studio-hero h2,
  .studio-hero h2 {
    margin: 0 0 0.35rem;
    font-size: 1.55rem;
    color: var(--studio-ink) !important;
    font-weight: 800 !important;
  }

  [data-testid="stMarkdownContainer"] .studio-hero > p,
  .studio-hero > p {
    color: var(--studio-muted) !important;
    margin: 0.25rem 0;
    font-weight: 500;
  }

  .micro-guide {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.75rem;
    margin-top: 1rem;
  }

  .micro-step,
  .empty-state,
  .last-action-panel,
  .summary-panel {
    border: 1px solid var(--studio-line);
    border-radius: 14px;
    padding: 1rem;
    background: rgba(255, 255, 255, 0.72);
  }

  .micro-step strong,
  .empty-state strong,
  .last-action-panel strong,
  .summary-panel strong {
    color: var(--studio-ink);
  }

  .last-action-panel {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 1rem;
    margin: 0.75rem 0 1rem;
  }

  .last-action-panel p {
    margin: 0.25rem 0 0;
    color: var(--studio-muted);
  }

  .last-action-meta {
    font-size: 0.86rem;
    color: var(--studio-muted);
  }

  .card-heading {
    margin: 0 0 0.35rem;
    font-size: 1.08rem;
    color: var(--studio-ink);
  }

  .card-copy,
  .empty-copy {
    color: var(--studio-muted);
    margin: 0.2rem 0 0;
  }

  .metric-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 0.75rem;
    margin: 0.85rem 0 1rem;
  }

  .metric-card {
    border: 1px solid var(--studio-line);
    border-radius: 14px;
    padding: 0.9rem 1rem;
    background: var(--studio-surface);
  }

  .metric-card__label {
    color: var(--studio-muted);
    font-size: 0.78rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .metric-card__value {
    font-size: 1.65rem;
    line-height: 1.15;
    font-weight: 850;
    color: var(--studio-ink);
    margin-top: 0.25rem;
  }

  .metric-card__detail {
    color: var(--studio-muted);
    font-size: 0.9rem;
    margin-top: 0.2rem;
  }

  .metric-card--success {
    border-color: rgba(22, 121, 76, 0.24);
  }

  .metric-card--warning {
    border-color: rgba(161, 98, 7, 0.24);
  }

  .metric-card--danger {
    border-color: rgba(180, 35, 24, 0.24);
  }

  .metric-card--info {
    border-color: rgba(29, 78, 216, 0.22);
  }

  @media (max-width: 720px) {
    .studio-brand-row,
    .studio-brand-left {
      align-items: flex-start;
      flex-direction: column;
    }

    .studio-badge-row {
      justify-content: flex-start;
    }

    .micro-guide {
      grid-template-columns: 1fr;
    }
  }
</style>
""".strip()


def render_brand_header_html(
    *,
    title: str = "Inquiry Studio",
    subtitle: str = "Operate the video-to-paper engine from one local cockpit.",
    environment: str = STUDIO_ENVIRONMENT,
) -> str:
    return f"""
<div class="studio-brand-row">
  <div class="studio-brand-left">
    <div class="studio-mark">🔎</div>
    <div>
      <h1 class="studio-title">{escape(title)}</h1>
      <p class="studio-subtitle">{escape(subtitle)}</p>
    </div>
  </div>
  <div class="studio-badge-row">
    <span class="studio-badge">{escape(environment)}</span>
  </div>
</div>
""".strip()


def render_hero_html() -> str:
    return """
<section class="studio-hero">
  <h2>Create inquiry in 60 seconds</h2>
  <p>Paste a source video, choose retrieval settings, then launch or queue the run.</p>
  <div class="micro-guide">
    <div class="micro-step"><strong>1. Source</strong><p class="card-copy">Add a YouTube URL and claim filters.</p></div>
    <div class="micro-step"><strong>2. Queue</strong><p class="card-copy">Create a stable run request artifact.</p></div>
    <div class="micro-step"><strong>3. Inspect</strong><p class="card-copy">Review paper, audit, progress, and health outputs.</p></div>
  </div>
</section>
""".strip()


def render_state_chip(status: str, label: str | None = None) -> str:
    normalized = status.strip().lower().replace(" ", "_")
    tone = STATUS_TONES.get(normalized, "neutral")
    visible_label = (label or status).upper()

    return (
        f'<span class="state-chip state-chip--{tone}">'
        f"{escape(visible_label)}"
        "</span>"
    )


def render_metric_cards(metrics: Iterable[dict[str, Any]]) -> str:
    cards = []

    for metric in metrics:
        tone = str(metric.get("tone", "neutral")).strip().lower().replace(" ", "_")

        if tone not in METRIC_TONES:
            tone = "neutral"

        label = escape(str(metric.get("label", "")))
        value = escape(str(metric.get("value", "")))
        detail = escape(str(metric.get("detail", "")))

        cards.append(
            f"""
<div class="metric-card metric-card--{tone}">
  <div class="metric-card__label">{label}</div>
  <div class="metric-card__value">{value}</div>
  <div class="metric-card__detail">{detail}</div>
</div>
""".strip()
        )

    return f'<div class="metric-row">{"".join(cards)}</div>'


def render_empty_state_html(
    *,
    icon: str,
    title: str,
    body: str,
    action: str,
) -> str:
    return f"""
<div class="empty-state">
  <strong>{escape(icon)} {escape(title)}</strong>
  <p class="empty-copy">{escape(body)}</p>
  <p class="empty-copy"><strong>Next action:</strong> {escape(action)}</p>
</div>
""".strip()


def render_last_action_panel_html(action: LastAction | None) -> str:
    if action is None:
        return ""

    meta_parts = []

    if action.created_at:
        meta_parts.append(escape(action.created_at))

    if action.artifact_path:
        meta_parts.append(f"Artifact: {escape(action.artifact_path)}")

    meta_html = (
        f'<p class="last-action-meta">{" · ".join(meta_parts)}</p>'
        if meta_parts
        else ""
    )

    return f"""
<div class="last-action-panel">
  <div>
    <strong>{escape(action.title)}</strong>
    <p>{escape(action.message)}</p>
    {meta_html}
  </div>
  <div>{render_state_chip(action.status)}</div>
</div>
""".strip()


def discover_inquiries(library_dir: str | Path) -> list[InquiryRecord]:
    """
    Discover saved inquiries from manifest files.

    Expected layout:

    data/inquiries/
      inquiry_001/
        manifest.json
      inquiry_002/
        manifest.json
    """
    root = Path(library_dir)

    if not root.exists():
        return []

    records: list[InquiryRecord] = []

    for manifest_path in sorted(root.glob("*/manifest.json")):
        try:
            records.append(InquiryRecord.from_manifest(manifest_path))
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            continue

    return sorted(records, key=lambda record: record.created_at, reverse=True)


def filter_inquiries(
    records: Iterable[InquiryRecord],
    *,
    query: str = "",
    status: str = "all",
) -> list[InquiryRecord]:
    normalized_query = query.strip().lower()
    normalized_status = status.strip().lower()

    filtered: list[InquiryRecord] = []

    for record in records:
        title_matches = normalized_query in record.title.lower()
        url_matches = normalized_query in record.youtube_url.lower()
        query_matches = not normalized_query or title_matches or url_matches

        status_matches = (
            normalized_status == "all"
            or record.status.lower() == normalized_status
        )

        if query_matches and status_matches:
            filtered.append(record)

    return filtered


def load_audit_report(path: str | Path | None) -> dict[str, Any] | None:
    if path is None:
        return None

    audit_path = Path(path)

    if not audit_path.exists():
        return None

    return _load_json(audit_path)


def paper_exists(path: str | Path | None) -> bool:
    return path is not None and Path(path).exists()


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")

    return data


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None

    value_as_string = str(value).strip()
    return value_as_string or None


def run_streamlit_app() -> None:
    """
    Streamlit entrypoint.

    Run with:

        streamlit run src/frontend/inquiry_studio.py
    """
    import streamlit as st

    st.set_page_config(
        page_title="Inquiry Studio",
        page_icon="🔎",
        layout="wide",
    )
    st.markdown(render_studio_css(), unsafe_allow_html=True)

    studio_config = load_studio_config()
    ensure_studio_directories(studio_config)
    state_defaults = {
        "audit_report_path": studio_config.default_audit_report_path or "",
        "progress_log_path": studio_config.default_progress_log_path or "",
        "backend_base_url": getattr(
            studio_config,
            "backend_base_url",
            None,
        )
        or DEFAULT_BACKEND_BASE_URL,
    }
    initialize_studio_state(
        st.session_state,
        st.query_params,
        defaults=state_defaults,
    )

    st.markdown(render_brand_header_html(), unsafe_allow_html=True)
    st.markdown(render_hero_html(), unsafe_allow_html=True)

    last_action = get_last_action(st.session_state)

    if last_action:
        st.markdown(
            render_last_action_panel_html(last_action),
            unsafe_allow_html=True,
        )

    cta_prepare, cta_smoke, cta_backend = st.columns(3)

    with cta_prepare:
        if st.button("Prepare Request", use_container_width=True):
            st.info("Use the New Inquiry controls in the sidebar to create a run request.")
            action = record_last_action(
                st.session_state,
                title="Request prep opened",
                message="Use the sidebar controls to create a stable run request.",
                status="info",
            )
            st.markdown(render_last_action_panel_html(action), unsafe_allow_html=True)

    with cta_smoke:
        if st.button("Run Smoke Test", use_container_width=True):
            smoke_result = run_studio_smoke_test(config=studio_config)

            if smoke_result.passed:
                st.success("Studio smoke test passed.")
                st.markdown(
                    render_state_chip("pass", "passed"),
                    unsafe_allow_html=True,
                )
                action_status = "success"
            else:
                st.error("Studio smoke test failed.")
                st.markdown(
                    render_state_chip("fail", "failed"),
                    unsafe_allow_html=True,
                )
                action_status = "failed"

            action = record_last_action(
                st.session_state,
                title="Smoke test finished",
                message="Studio smoke test completed.",
                status=action_status,
                details={
                    "checks": len(smoke_result.checks),
                    "errors": len(smoke_result.errors),
                },
            )
            st.markdown(render_last_action_panel_html(action), unsafe_allow_html=True)

            with st.expander("Developer Details: smoke result"):
                st.json(smoke_result.to_dict())

    with cta_backend:
        if st.button("Check Backend", use_container_width=True):
            try:
                client = BackendClient(
                    BackendClientConfig(
                        base_url=st.session_state[
                            STUDIO_SESSION_KEYS["backend_base_url"]
                        ],
                        timeout_seconds=float(
                            getattr(studio_config, "backend_timeout_seconds", 10.0)
                        ),
                    )
                )
                response = client.health_check()

                if response.ok:
                    st.success("Backend is reachable.")
                    st.markdown(
                        render_state_chip("healthy"),
                        unsafe_allow_html=True,
                    )
                    action_status = "success"
                else:
                    st.error(response.error_message or "Backend health check failed.")
                    st.markdown(
                        render_state_chip("failed"),
                        unsafe_allow_html=True,
                    )
                    action_status = "failed"

                action = record_last_action(
                    st.session_state,
                    title="Backend health checked",
                    message=(
                        "Backend is reachable."
                        if response.ok
                        else response.error_message or "Backend health check failed."
                    ),
                    status=action_status,
                    details={"base_url": client.config.base_url},
                )
                st.markdown(render_last_action_panel_html(action), unsafe_allow_html=True)

                with st.expander("Developer Details: backend health"):
                    st.json(response.data)
            except ValueError as error:
                st.error(str(error))

    library_dir = Path(studio_config.inquiry_library_dir)

    with st.sidebar:
        st.header("New Inquiry")

        youtube_url = st.text_input(
            "YouTube URL",
            placeholder="https://www.youtube.com/watch?v=...",
        )

        claim_type_filter = st.multiselect(
            "Claim types",
            options=[
                "empirical_technical",
                "empirical_historical",
                "empirical_scientific",
                "interpretive",
                "normative",
                "anecdotal",
                "predictive",
            ],
            default=[
                "empirical_technical",
                "empirical_historical",
                "empirical_scientific",
            ],
        )

        retrieval_depth = st.slider(
            "Retrieval depth",
            min_value=1,
            max_value=10,
            value=3,
        )

        source_tiers = st.multiselect(
            "Source tiers",
            options=[1, 2, 3],
            default=[1, 2],
            help="1 = peer-reviewed, 2 = institutional, 3 = secondary",
        )

        selected_stages = st.multiselect(
            "Pipeline stages",
            options=DEFAULT_PIPELINE_STAGES,
            default=DEFAULT_PIPELINE_STAGES,
        )

        if st.button("Prepare Run Request", use_container_width=True):
            try:
                request = create_inquiry_run_request(
                    youtube_url=youtube_url,
                    claim_type_filter=claim_type_filter,
                    retrieval_depth=retrieval_depth,
                    source_tiers=source_tiers,
                    stages=selected_stages,
                    metadata={
                        "created_from": "streamlit_inquiry_studio",
                    },
                )

                output_path = save_run_request(
                    request,
                    output_dir=studio_config.run_requests_dir,
                )
                record_activity(
                    activity_type="request_created",
                    message=f"Created run request for video {request.video_id}.",
                    request_id=request.request_id,
                    artifact_path=output_path.as_posix(),
                    log_path=studio_config.operator_activity_log_path,
                )

                st.success(f"Run request saved to {output_path}")
                action = record_last_action(
                    st.session_state,
                    title="Run request created",
                    message=f"Created request for video {request.video_id}.",
                    status="success",
                    details={"request_id": request.request_id},
                    artifact_path=output_path.as_posix(),
                )
                st.markdown(render_last_action_panel_html(action), unsafe_allow_html=True)

                with st.expander("Developer Details: run request payload"):
                    st.json(request.to_dict())
            except ValueError as error:
                st.error(str(error))

    tab_library, tab_requests, tab_audit, tab_progress, tab_activity, tab_health, tab_backend = st.tabs(
        [
            "🔎 Inquiry Library",
            "▶ Run Requests",
            "⚠ Audit Inspector",
            "📈 Run Progress",
            "📄 Activity Log",
            "✅ Health Check",
            "🔗 Backend",
        ]
    )

    records = discover_inquiries(library_dir)

    with tab_library:
        st.markdown("### 🔎 Inquiry Library")
        with st.container(border=True):
            st.markdown("#### Browse generated papers")
            st.write(
                "Search previous inquiries, open finished papers, inspect audits, or create a rerun request."
            )

        col_query, col_status = st.columns([3, 1])

        with col_query:
            query = st.text_input(
                "Search title or URL",
                key=STUDIO_SESSION_KEYS["library_query"],
            )

        with col_status:
            status = st.selectbox(
                "Status",
                options=["all", "completed", "failed", "running", "queued"],
                key=STUDIO_SESSION_KEYS["library_status"],
            )

        visible_records = filter_inquiries(records, query=query, status=status)

        if not visible_records:
            st.markdown(
                render_empty_state_html(
                    icon="🔎",
                    title="No inquiries indexed yet",
                    body=(
                        "This library reads saved inquiry manifests from "
                        f"{studio_config.inquiry_library_dir}."
                    ),
                    action="Create a run request, launch it, then return here after the run writes a manifest.",
                ),
                unsafe_allow_html=True,
            )
        else:
            for record in visible_records:
                with st.container(border=True):
                    st.markdown(f"### {record.title}")
                    st.markdown(render_state_chip(record.status), unsafe_allow_html=True)
                    st.write(f"**Created:** {record.created_at}")
                    st.write(f"**Source:** {record.youtube_url}")

                    cols = st.columns(4)

                    with cols[0]:
                        paper_artifact = inspect_paper_artifact(record.paper_path)

                        if paper_artifact.is_openable:
                            st.link_button(
                                "Open Paper",
                                build_file_url(paper_artifact.path),
                                use_container_width=True,
                            )

                            if paper_artifact.title:
                                st.caption(f"Paper title: {paper_artifact.title}")

                            if paper_artifact.size_bytes is not None:
                                st.caption(f"Size: {paper_artifact.size_bytes:,} bytes")
                        else:
                            st.button(
                                "Paper Missing",
                                disabled=True,
                                use_container_width=True,
                            )

                    with cols[1]:
                        if record.audit_report_path:
                            st.write(f"Audit: `{record.audit_report_path}`")
                        else:
                            st.write("Audit: not available")

                    with cols[2]:
                        with st.expander("Create rerun request"):
                            rerun_depth = st.slider(
                                "Rerun retrieval depth",
                                min_value=1,
                                max_value=10,
                                value=int(record.parameters.get("retrieval_depth", 3)),
                                key=f"rerun-depth-{record.inquiry_id}",
                            )

                            rerun_tiers = st.multiselect(
                                "Rerun source tiers",
                                options=[1, 2, 3],
                                default=record.parameters.get("source_tiers", [1, 2]),
                                key=f"rerun-tiers-{record.inquiry_id}",
                            )

                            rerun_reason = st.text_area(
                                "Reason",
                                value="Adjust retrieval settings and rerun inquiry.",
                                key=f"rerun-reason-{record.inquiry_id}",
                            )

                            if st.button(
                                "Create Rerun Request",
                                key=f"create-rerun-{record.inquiry_id}",
                                use_container_width=True,
                            ):
                                try:
                                    rerun_request = create_rerun_from_inquiry_record(
                                        record,
                                        overrides=RerunOverrides(
                                            retrieval_depth=rerun_depth,
                                            source_tiers=rerun_tiers,
                                            reason=rerun_reason,
                                        ),
                                    )

                                    rerun_path = save_rerun_request(
                                        rerun_request,
                                        output_dir=studio_config.run_requests_dir,
                                    )
                                    record_activity(
                                        activity_type="rerun_created",
                                        message=f"Created rerun request from inquiry {record.inquiry_id}.",
                                        request_id=rerun_request.request_id,
                                        inquiry_id=record.inquiry_id,
                                        artifact_path=rerun_path.as_posix(),
                                        log_path=studio_config.operator_activity_log_path,
                                    )

                                    st.success(f"Rerun request saved to {rerun_path}")
                                    action = record_last_action(
                                        st.session_state,
                                        title="Rerun request created",
                                        message=(
                                            "Created a rerun request from "
                                            f"{record.inquiry_id}."
                                        ),
                                        status="success",
                                        details={
                                            "request_id": rerun_request.request_id,
                                            "inquiry_id": record.inquiry_id,
                                        },
                                        artifact_path=rerun_path.as_posix(),
                                    )
                                    st.markdown(
                                        render_last_action_panel_html(action),
                                        unsafe_allow_html=True,
                                    )

                                    with st.expander(
                                        "Developer Details: rerun request payload"
                                    ):
                                        st.json(rerun_request.to_dict())

                                except ValueError as error:
                                    st.error(str(error))

                    with st.expander("Developer Details: run parameters"):
                        st.json(record.parameters)

    with tab_requests:
        st.markdown("### ▶ Run Requests")
        with st.container(border=True):
            st.markdown("#### Queue and launch work")
            st.write(
                "Review request artifacts, launch local runs, or submit an executable request to the backend."
            )

        queued_requests = discover_run_requests(studio_config.run_requests_dir)
        queue_summary = summarize_queue(queued_requests)

        st.markdown(
            render_metric_cards(
                [
                    {
                        "label": "Total",
                        "value": queue_summary["total"],
                        "detail": "requests found",
                        "tone": "neutral",
                    },
                    {
                        "label": "Executable",
                        "value": queue_summary["executable"],
                        "detail": "ready to launch",
                        "tone": "success",
                    },
                    {
                        "label": "Pending",
                        "value": queue_summary["pending"],
                        "detail": "waiting in queue",
                        "tone": "warning",
                    },
                    {
                        "label": "Running",
                        "value": queue_summary["running"],
                        "detail": "runs active",
                        "tone": "info",
                    },
                    {
                        "label": "Completed",
                        "value": queue_summary["completed"],
                        "detail": "finished runs",
                        "tone": "success",
                    },
                    {
                        "label": "Failed",
                        "value": queue_summary["failed"],
                        "detail": "needs attention",
                        "tone": "danger",
                    },
                ]
            ),
            unsafe_allow_html=True,
        )

        col_query, col_status = st.columns([3, 1])

        with col_query:
            request_query = st.text_input(
                "Search request, URL, or video id",
                key=STUDIO_SESSION_KEYS["request_query"],
            )

        with col_status:
            request_status = st.selectbox(
                "Queue status",
                options=["all", "pending", "queued", "running", "completed", "failed"],
                key=STUDIO_SESSION_KEYS["request_status"],
            )

        visible_requests = filter_queued_requests(
            queued_requests,
            query=request_query,
            status=request_status,
        )

        if not visible_requests:
            st.markdown(
                render_empty_state_html(
                    icon="▶",
                    title="No run requests yet",
                    body=(
                        "Run requests appear here after the sidebar form writes "
                        f"JSON files into {studio_config.run_requests_dir}."
                    ),
                    action="Use Prepare Request, then save a run request from the sidebar.",
                ),
                unsafe_allow_html=True,
            )
        else:
            for item in visible_requests:
                with st.container(border=True):
                    st.markdown(f"### {item.request_id}")
                    st.markdown(render_state_chip(item.status), unsafe_allow_html=True)
                    st.write(f"**Video ID:** {item.request.video_id}")
                    st.write(f"**Created:** {item.created_at}")
                    st.write(f"**Source:** {item.youtube_url}")
                    st.write(f"**Request file:** `{item.request_path}`")

                    cols = st.columns(4)

                    with cols[0]:
                        if st.button(
                            "Launch Local Run" if item.is_executable else "Not Runnable",
                            disabled=not item.is_executable,
                            key=f"launch-{item.request_id}",
                            use_container_width=True,
                        ):
                            try:
                                launch = launch_local_run(
                                    item,
                                    runs_dir=studio_config.runs_dir,
                                )

                                if item.request_path:
                                    mark_request_queued(
                                        item.request_path,
                                        progress_path=launch.progress_path,
                                    )
                                    record_activity(
                                        activity_type="run_launched",
                                        message=f"Launched local run {launch.run_id}.",
                                        request_id=item.request_id,
                                        run_id=launch.run_id,
                                        artifact_path=launch.progress_path,
                                        log_path=studio_config.operator_activity_log_path,
                                    )

                                st.success(f"Run launched: {launch.run_id}")
                                st.write(f"Progress log: `{launch.progress_path}`")
                                action = record_last_action(
                                    st.session_state,
                                    title="Local run launched",
                                    message=f"Started local run {launch.run_id}.",
                                    status="success",
                                    details={"request_id": item.request_id},
                                    artifact_path=launch.progress_path,
                                )
                                st.markdown(
                                    render_last_action_panel_html(action),
                                    unsafe_allow_html=True,
                                )

                                with st.expander("Developer Details: launch payload"):
                                    st.json(launch.to_dict())
                            except ValueError as error:
                                st.error(str(error))
                            except FileExistsError:
                                st.error(
                                    "A run folder with this generated id already exists. Try again."
                                )

                    with cols[1]:
                        if st.button(
                            "Submit to Backend",
                            disabled=not item.is_executable,
                            key=f"submit-backend-{item.request_id}",
                            use_container_width=True,
                        ):
                            try:
                                client = BackendClient(
                                    BackendClientConfig(
                                        base_url=st.session_state[
                                            STUDIO_SESSION_KEYS["backend_base_url"]
                                        ],
                                        timeout_seconds=float(
                                            getattr(
                                                studio_config,
                                                "backend_timeout_seconds",
                                                10.0,
                                            )
                                        ),
                                    )
                                )

                                result = submit_queued_request_to_backend(
                                    item,
                                    client=client,
                                )

                                if result.submitted:
                                    if item.request_path:
                                        mark_request_running(
                                            item.request_path,
                                            progress_path=item.progress_path,
                                        )

                                    record_activity(
                                        activity_type="run_launched",
                                        message=f"Submitted request {item.request_id} to backend.",
                                        request_id=item.request_id,
                                        run_id=result.run_id,
                                        artifact_path=item.request_path,
                                        log_path=studio_config.operator_activity_log_path,
                                    )

                                    st.success(result.message)
                                    action_status = "success"
                                else:
                                    st.error(result.message)
                                    action_status = "failed"

                                action = record_last_action(
                                    st.session_state,
                                    title="Backend submission finished",
                                    message=result.message,
                                    status=action_status,
                                    details={
                                        "request_id": item.request_id,
                                        "run_id": result.run_id,
                                    },
                                )
                                st.markdown(
                                    render_last_action_panel_html(action),
                                    unsafe_allow_html=True,
                                )

                                with st.expander(
                                    "Developer Details: backend submission response"
                                ):
                                    st.json(result.to_dict())

                            except ValueError as error:
                                st.error(str(error))

                    with cols[2]:
                        if item.progress_path:
                            st.write(f"Progress: `{item.progress_path}`")
                        else:
                            st.write("Progress: not started")

                    with cols[3]:
                        if item.result_inquiry_id:
                            st.write(f"Result: `{item.result_inquiry_id}`")
                        else:
                            st.write("Result: none yet")

                    with st.expander("Developer Details: request payload"):
                        st.json(item.request.to_dict())

    with tab_audit:
        st.markdown("### ⚠ Audit Inspector")
        with st.container(border=True):
            st.markdown("#### Open Audit")
            st.write(
                "Load an audit JSON file and scan publishability, blocking issues, and axis-level scores first."
            )

        audit_path = st.text_input(
            "Audit report path",
            placeholder="data/inquiries/inquiry_001/audit_report.json",
            key=STUDIO_SESSION_KEYS["audit_report_path"],
        )

        if st.button("Load Audit Report"):
            report = load_audit_report(audit_path)

            if report is None:
                st.error("Audit report could not be loaded.")
            else:
                record_activity(
                    activity_type="audit_opened",
                    message="Opened audit report in the Studio.",
                    artifact_path=audit_path,
                    log_path=studio_config.operator_activity_log_path,
                )
                summary = summarize_audit_report(report)

                if summary.publishable:
                    st.success("Audit status: publishable")
                    st.markdown(
                        render_state_chip("publishable"),
                        unsafe_allow_html=True,
                    )
                    action_status = "success"
                else:
                    st.error("Audit status: not publishable")
                    st.markdown(
                        render_state_chip("not_publishable", "not publishable"),
                        unsafe_allow_html=True,
                    )
                    action_status = "failed"

                action = record_last_action(
                    st.session_state,
                    title="Audit report opened",
                    message=(
                        "Audit report is publishable."
                        if summary.publishable
                        else "Audit report has blocking findings."
                    ),
                    status=action_status,
                    details={
                        "blocking_issues": len(summary.blocking_issues),
                        "warnings": len(summary.warning_issues),
                    },
                    artifact_path=audit_path,
                )
                st.markdown(render_last_action_panel_html(action), unsafe_allow_html=True)

                st.markdown(
                    render_metric_cards(
                        [
                            {
                                "label": axis.axis.replace("_", " ").title(),
                                "value": axis.status.upper(),
                                "detail": axis.score,
                                "tone": "success"
                                if axis.status.lower() in {"pass", "passed"}
                                else "danger",
                            }
                            for axis in summary.axes
                        ]
                    ),
                    unsafe_allow_html=True,
                )

                if summary.blocking_issues:
                    st.subheader("Blocking Issues")
                    for issue in summary.blocking_issues:
                        st.error(issue)

                if summary.warning_issues:
                    st.subheader("Warnings")
                    for issue in summary.warning_issues:
                        st.warning(issue)

                with st.expander("Developer Details: raw audit report"):
                    st.json(report)

    with tab_progress:
        st.markdown("### 📈 Run Progress")
        with st.container(border=True):
            st.markdown("#### Inspect Run")
            st.write(
                "Load a progress log or sync a backend run to see current status before opening raw payloads."
            )

        progress_path = st.text_input(
            "Progress log path",
            placeholder="logs/runs/latest_progress.json",
            key=STUDIO_SESSION_KEYS["progress_log_path"],
        )

        if st.button("Load Progress"):
            try:
                progress = load_run_progress(progress_path)

                if progress is None:
                    st.error("Progress log could not be found.")
                else:
                    record_activity(
                        activity_type="progress_viewed",
                        message=f"Viewed progress for run {progress.run_id}.",
                        run_id=progress.run_id,
                        artifact_path=progress_path,
                        log_path=studio_config.operator_activity_log_path,
                    )
                    summary = summarize_progress(progress)

                    st.progress(summary["completion_ratio"])
                    st.write(f"**Run ID:** {summary['run_id']}")
                    st.markdown(
                        render_state_chip(str(summary["status"])),
                        unsafe_allow_html=True,
                    )
                    st.write(f"**Current step:** {summary['current_step'] or 'None'}")
                    st.write(f"**Elapsed seconds:** {summary['elapsed_seconds']}")
                    action = record_last_action(
                        st.session_state,
                        title="Progress log loaded",
                        message=f"Loaded progress for run {summary['run_id']}.",
                        status=(
                            "failed"
                            if int(summary["failed_steps"]) > 0
                            else "success"
                        ),
                        details={
                            "completed_steps": summary["completed_steps"],
                            "failed_steps": summary["failed_steps"],
                        },
                        artifact_path=progress_path,
                    )
                    st.markdown(
                        render_last_action_panel_html(action),
                        unsafe_allow_html=True,
                    )

                    st.markdown(
                        render_metric_cards(
                            [
                                {
                                    "label": "Completed",
                                    "value": summary["completed_steps"],
                                    "detail": "steps finished",
                                    "tone": "success",
                                },
                                {
                                    "label": "Running",
                                    "value": summary["running_steps"],
                                    "detail": "steps active",
                                    "tone": "info",
                                },
                                {
                                    "label": "Queued",
                                    "value": summary["queued_steps"],
                                    "detail": "waiting",
                                    "tone": "warning",
                                },
                                {
                                    "label": "Skipped",
                                    "value": summary["skipped_steps"],
                                    "detail": "not run",
                                    "tone": "neutral",
                                },
                                {
                                    "label": "Failed",
                                    "value": summary["failed_steps"],
                                    "detail": "blocking issues",
                                    "tone": "danger",
                                },
                            ]
                        ),
                        unsafe_allow_html=True,
                    )

                    for step in progress.steps:
                        with st.container(border=True):
                            st.write(f"**{step.name}**")
                            st.markdown(
                                render_state_chip(step.status),
                                unsafe_allow_html=True,
                            )

                            if step.elapsed_seconds is not None:
                                st.write(f"Elapsed: {step.elapsed_seconds}s")

                            if step.message:
                                st.write(step.message)

            except ValueError as error:
                st.error(str(error))

        st.divider()
        st.subheader("Sync Backend Progress")

        backend_run_id = st.text_input(
            "Backend run id",
            placeholder="run_001",
            key=STUDIO_SESSION_KEYS["backend_run_id"],
        )

        if st.button("Sync from Backend"):
            try:
                client = BackendClient(
                    BackendClientConfig(
                        base_url=st.session_state[
                            STUDIO_SESSION_KEYS["backend_base_url"]
                        ],
                        timeout_seconds=float(
                            getattr(
                                studio_config,
                                "backend_timeout_seconds",
                                10.0,
                            )
                        ),
                    )
                )

                result = sync_backend_progress(
                    run_id=backend_run_id,
                    client=client,
                    snapshot_dir=studio_config.runs_dir,
                )

                if result.synced and result.progress is not None:
                    st.success(result.message)

                    summary = summarize_progress(result.progress)

                    st.progress(summary["completion_ratio"])
                    st.write(f"**Run ID:** {summary['run_id']}")
                    st.markdown(
                        render_state_chip(str(summary["status"])),
                        unsafe_allow_html=True,
                    )
                    st.write(f"**Current step:** {summary['current_step'] or 'None'}")

                    st.markdown(
                        render_metric_cards(
                            [
                                {
                                    "label": "Completed",
                                    "value": summary["completed_steps"],
                                    "detail": "steps finished",
                                    "tone": "success",
                                },
                                {
                                    "label": "Running",
                                    "value": summary["running_steps"],
                                    "detail": "steps active",
                                    "tone": "info",
                                },
                                {
                                    "label": "Queued",
                                    "value": summary["queued_steps"],
                                    "detail": "waiting",
                                    "tone": "warning",
                                },
                                {
                                    "label": "Failed",
                                    "value": summary["failed_steps"],
                                    "detail": "blocking issues",
                                    "tone": "danger",
                                },
                            ]
                        ),
                        unsafe_allow_html=True,
                    )

                    if result.snapshot_path:
                        st.write(f"Snapshot saved to: `{result.snapshot_path}`")

                    record_activity(
                        activity_type="progress_viewed",
                        message=f"Synced backend progress for run {result.run_id}.",
                        run_id=result.run_id,
                        artifact_path=result.snapshot_path,
                        log_path=studio_config.operator_activity_log_path,
                    )
                    action = record_last_action(
                        st.session_state,
                        title="Backend progress synced",
                        message=f"Synced progress for run {result.run_id}.",
                        status=(
                            "failed"
                            if int(summary["failed_steps"]) > 0
                            else "success"
                        ),
                        details={
                            "completed_steps": summary["completed_steps"],
                            "failed_steps": summary["failed_steps"],
                        },
                        artifact_path=result.snapshot_path,
                    )
                    st.markdown(
                        render_last_action_panel_html(action),
                        unsafe_allow_html=True,
                    )

                    with st.expander("Developer Details: synced progress payload"):
                        st.json(result.to_dict())
                else:
                    st.error(result.message)
                    action = record_last_action(
                        st.session_state,
                        title="Backend progress sync failed",
                        message=result.message,
                        status="failed",
                        details={"run_id": result.run_id},
                    )
                    st.markdown(
                        render_last_action_panel_html(action),
                        unsafe_allow_html=True,
                    )

                    with st.expander("Developer Details: backend sync response"):
                        st.json(result.to_dict())

            except ValueError as error:
                st.error(str(error))

    with tab_activity:
        st.markdown("### 📄 Activity Log")
        with st.container(border=True):
            st.markdown("#### Recent operator actions")
            st.write(
                "Scan requests, launches, imports, documentation generation, and progress views from one log."
            )

        activities = read_activity_log(
            studio_config.operator_activity_log_path,
            limit=200,
        )

        col_query, col_type = st.columns([3, 1])

        with col_query:
            activity_query = st.text_input(
                "Search activity",
                key=STUDIO_SESSION_KEYS["activity_query"],
            )

        with col_type:
            activity_type_options = ["all", *sorted(VALID_ACTIVITY_TYPES)]

            if (
                st.session_state[STUDIO_SESSION_KEYS["activity_type"]]
                not in activity_type_options
            ):
                st.session_state[STUDIO_SESSION_KEYS["activity_type"]] = "all"

            activity_type = st.selectbox(
                "Activity type",
                options=activity_type_options,
                key=STUDIO_SESSION_KEYS["activity_type"],
            )

        visible_activities = filter_activities(
            activities,
            activity_type=activity_type,
            query=activity_query,
        )

        if not visible_activities:
            st.markdown(
                render_empty_state_html(
                    icon="📄",
                    title="No operator activity yet",
                    body=(
                        "The activity log records request creation, launch actions, "
                        "audit opens, imports, and documentation generation."
                    ),
                    action="Create a request or open an audit to write the first activity event.",
                ),
                unsafe_allow_html=True,
            )
        else:
            for activity in visible_activities:
                with st.container(border=True):
                    st.write(f"**{activity.activity_type.replace('_', ' ').title()}**")
                    st.markdown(
                        render_state_chip(activity.activity_type, activity.activity_type),
                        unsafe_allow_html=True,
                    )
                    st.write(activity.message)
                    st.caption(activity.created_at)

                    details = {
                        "request_id": activity.request_id,
                        "inquiry_id": activity.inquiry_id,
                        "run_id": activity.run_id,
                        "artifact_path": activity.artifact_path,
                        "metadata": activity.metadata or {},
                    }

                    with st.expander("Developer Details"):
                        st.json(details)

    with tab_health:
        st.markdown("### ✅ Studio Health Check")
        with st.container(border=True):
            st.markdown("#### Preflight readiness")
            st.write(
                "Confirm required folders, request writes, run-log writes, and optional default files before launching work."
            )

        health_report = run_studio_health_checks(studio_config)

        if health_report.is_ready:
            st.success("Studio status: ready")
            st.markdown(
                render_state_chip("ready"),
                unsafe_allow_html=True,
            )
        else:
            st.error("Studio status: needs attention")
            st.markdown(
                render_state_chip("needs_attention", "needs attention"),
                unsafe_allow_html=True,
            )

        st.markdown(
            render_metric_cards(
                [
                    {
                        "label": "Passing",
                        "value": health_report.passing_count,
                        "detail": "healthy checks",
                        "tone": "success",
                    },
                    {
                        "label": "Warnings",
                        "value": health_report.warning_count,
                        "detail": "optional issues",
                        "tone": "warning",
                    },
                    {
                        "label": "Failing",
                        "value": health_report.failing_count,
                        "detail": "blocking issues",
                        "tone": "danger",
                    },
                ]
            ),
            unsafe_allow_html=True,
        )

        for check in health_report.checks:
            with st.container(border=True):
                st.write(f"**{check.name}**")
                st.markdown(render_state_chip(check.status), unsafe_allow_html=True)
                st.write(check.message)

                if check.path:
                    st.caption(check.path)

        with st.expander("Developer Details: raw health report"):
            st.json(health_report.to_dict())

        st.divider()
        st.subheader("Documentation")

        if st.button("Generate Studio README"):
            readme_path = write_studio_readme(
                studio_config,
                output_path="docs/inquiry_studio.md",
            )

            record_activity(
                activity_type="documentation_generated",
                message="Generated Inquiry Studio README.",
                artifact_path=readme_path.as_posix(),
                log_path=studio_config.operator_activity_log_path,
                metadata={"artifact_type": "documentation"},
            )

            st.success(f"README written to {readme_path}")

        st.divider()
        st.subheader("Smoke Test")

        if st.button("Run Studio Smoke Test"):
            result = run_studio_smoke_test(config=studio_config)

            if result.passed:
                st.success("Studio smoke test passed.")
                st.markdown(
                    render_state_chip("pass", "passed"),
                    unsafe_allow_html=True,
                )
            else:
                st.error("Studio smoke test failed.")
                st.markdown(
                    render_state_chip("fail", "failed"),
                    unsafe_allow_html=True,
                )

            if result.errors:
                st.subheader("Errors")
                for error in result.errors:
                    st.error(error)

            st.markdown(
                render_metric_cards(
                    [
                        {
                            "label": "Checks",
                            "value": len(result.checks),
                            "detail": "preflight checks run",
                            "tone": "success" if result.passed else "warning",
                        },
                        {
                            "label": "Errors",
                            "value": len(result.errors),
                            "detail": "blocking issues",
                            "tone": "danger" if result.errors else "success",
                        },
                    ]
                ),
                unsafe_allow_html=True,
            )

            with st.expander("Developer Details: smoke checks"):
                st.json(result.to_dict())


    with tab_backend:
        st.markdown("### 🔗 Backend")
        with st.container(border=True):
            st.markdown("#### Backend connection")
            st.write(
                "Check the backend health endpoint, then import a completed inquiry into the local library."
            )

        backend_base_url = st.text_input(
            "Backend base URL",
            key=STUDIO_SESSION_KEYS["backend_base_url"],
        )

        timeout_seconds = st.number_input(
            "Timeout seconds",
            min_value=1.0,
            max_value=60.0,
            value=float(getattr(studio_config, "backend_timeout_seconds", 10.0)),
        )

        if st.button("Check Backend Health"):
            try:
                client = BackendClient(
                    BackendClientConfig(
                        base_url=backend_base_url,
                        timeout_seconds=timeout_seconds,
                    )
                )

                response = client.health_check()

                if response.ok:
                    st.success("Backend is reachable.")
                    st.markdown(
                        render_state_chip("healthy"),
                        unsafe_allow_html=True,
                    )
                else:
                    st.error(response.error_message or "Backend health check failed.")
                    st.markdown(
                        render_state_chip("failed"),
                        unsafe_allow_html=True,
                    )

                with st.expander("Developer Details: backend health response"):
                    st.json(response.data)

            except ValueError as error:
                st.error(str(error))

        st.divider()
        st.subheader("Import Completed Inquiry")

        backend_inquiry_id = st.text_input(
            "Backend inquiry id",
            placeholder="inquiry_001",
        )

        if st.button("Import Inquiry"):
            try:
                client = BackendClient(
                    BackendClientConfig(
                        base_url=st.session_state[
                            STUDIO_SESSION_KEYS["backend_base_url"]
                        ],
                        timeout_seconds=float(
                            getattr(
                                studio_config,
                                "backend_timeout_seconds",
                                10.0,
                            )
                        ),
                    )
                )

                result = import_backend_inquiry(
                    inquiry_id=backend_inquiry_id,
                    client=client,
                    library_dir=studio_config.inquiry_library_dir,
                )

                if result.imported:
                    st.success(result.message)
                    st.markdown(
                        render_state_chip("completed", "imported"),
                        unsafe_allow_html=True,
                    )

                    record_activity(
                        activity_type="inquiry_imported",
                        message=f"Imported backend inquiry {result.inquiry_id}.",
                        inquiry_id=result.inquiry_id,
                        artifact_path=result.manifest_path,
                        log_path=studio_config.operator_activity_log_path,
                        metadata={"source": "backend_import"},
                    )
                else:
                    st.error(result.message)
                    st.markdown(
                        render_state_chip("failed", "not imported"),
                        unsafe_allow_html=True,
                    )

                with st.expander("Developer Details: import response"):
                    st.json(result.to_dict())

            except ValueError as error:
                st.error(str(error))


if __name__ == "__main__":
    run_streamlit_app()
