from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

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


YOUTUBE_ID_PATTERN = re.compile(
    r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([A-Za-z0-9_-]{11})"
)


@dataclass(frozen=True)
class RunParameters:
    youtube_url: str
    video_id: str
    claim_type_filter: list[str]
    retrieval_depth: int
    source_tiers: list[int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "youtube_url": self.youtube_url,
            "video_id": self.video_id,
            "claim_type_filter": self.claim_type_filter,
            "retrieval_depth": self.retrieval_depth,
            "source_tiers": self.source_tiers,
        }


@dataclass(frozen=True)
class InquiryRecord:
    inquiry_id: str
    title: str
    youtube_url: str
    status: str
    created_at: str
    paper_path: str | None
    audit_report_path: str | None
    parameters: dict[str, Any]

    @classmethod
    def from_manifest(cls, manifest_path: Path) -> "InquiryRecord":
        data = _load_json(manifest_path)

        return cls(
            inquiry_id=str(data.get("inquiry_id", manifest_path.parent.name)),
            title=str(data.get("title", "Untitled inquiry")),
            youtube_url=str(data.get("youtube_url", "")),
            status=str(data.get("status", "unknown")),
            created_at=str(data.get("created_at", "")),
            paper_path=_optional_string(data.get("paper_path")),
            audit_report_path=_optional_string(data.get("audit_report_path")),
            parameters=dict(data.get("parameters", {})),
        )


def parse_youtube_video_id(url: str) -> str:
    """
    Extract an 11-character YouTube video id from a supported YouTube URL.
    """
    match = YOUTUBE_ID_PATTERN.search(url.strip())

    if not match:
        raise ValueError("Could not parse a valid YouTube video id from the URL.")

    return match.group(1)


def build_run_parameters(
    *,
    youtube_url: str,
    claim_type_filter: Iterable[str],
    retrieval_depth: int,
    source_tiers: Iterable[int],
) -> RunParameters:
    """
    Validate operator inputs and convert them into a stable run config.
    """
    video_id = parse_youtube_video_id(youtube_url)

    if retrieval_depth < 1:
        raise ValueError("retrieval_depth must be at least 1.")

    normalized_tiers = sorted(set(int(tier) for tier in source_tiers))

    if not normalized_tiers:
        raise ValueError("At least one source tier must be selected.")

    if any(tier < 1 or tier > 3 for tier in normalized_tiers):
        raise ValueError("source_tiers must only contain tiers 1, 2, or 3.")

    normalized_claim_types = sorted(set(claim_type_filter))

    return RunParameters(
        youtube_url=youtube_url.strip(),
        video_id=video_id,
        claim_type_filter=normalized_claim_types,
        retrieval_depth=retrieval_depth,
        source_tiers=normalized_tiers,
    )


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
    studio_config = load_studio_config()
    ensure_studio_directories(studio_config)

    st.title("Inquiry Studio")
    st.caption("Operate the video-to-paper engine from one local cockpit.")

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
                st.json(request.to_dict())
            except ValueError as error:
                st.error(str(error))

    tab_library, tab_requests, tab_audit, tab_progress, tab_activity, tab_health, tab_backend = st.tabs(
        [
            "Inquiry Library",
            "Run Requests",
            "Audit Inspector",
            "Run Progress",
            "Activity Log",
            "Health Check",
            "Backend",
        ]
    )

    records = discover_inquiries(library_dir)

    with tab_library:
        st.subheader("Past Inquiries")

        col_query, col_status = st.columns([3, 1])

        with col_query:
            query = st.text_input("Search title or URL")

        with col_status:
            status = st.selectbox(
                "Status",
                options=["all", "completed", "failed", "running", "queued"],
            )

        visible_records = filter_inquiries(records, query=query, status=status)

        if not visible_records:
            st.info("No inquiries found yet. Add manifest files under data/inquiries/.")
        else:
            for record in visible_records:
                with st.container(border=True):
                    st.markdown(f"### {record.title}")
                    st.write(f"**Status:** {record.status}")
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
                                    st.json(rerun_request.to_dict())

                                except ValueError as error:
                                    st.error(str(error))

                    with st.expander("Run parameters"):
                        st.json(record.parameters)

    with tab_requests:
        st.subheader("Run Request Queue")

        queued_requests = discover_run_requests(studio_config.run_requests_dir)
        queue_summary = summarize_queue(queued_requests)

        metric_cols = st.columns(6)
        metric_cols[0].metric("Total", queue_summary["total"])
        metric_cols[1].metric("Executable", queue_summary["executable"])
        metric_cols[2].metric("Pending", queue_summary["pending"])
        metric_cols[3].metric("Running", queue_summary["running"])
        metric_cols[4].metric("Completed", queue_summary["completed"])
        metric_cols[5].metric("Failed", queue_summary["failed"])

        col_query, col_status = st.columns([3, 1])

        with col_query:
            request_query = st.text_input("Search request, URL, or video id")

        with col_status:
            request_status = st.selectbox(
                "Queue status",
                options=["all", "pending", "queued", "running", "completed", "failed"],
            )

        visible_requests = filter_queued_requests(
            queued_requests,
            query=request_query,
            status=request_status,
        )

        if not visible_requests:
            st.info("No run requests found yet.")
        else:
            for item in visible_requests:
                with st.container(border=True):
                    st.markdown(f"### {item.request_id}")
                    st.write(f"**Status:** {item.status}")
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
                                        base_url=getattr(
                                            studio_config,
                                            "backend_base_url",
                                            None,
                                        )
                                        or "http://127.0.0.1:8000",
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
                                else:
                                    st.error(result.message)

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

                    with st.expander("Request payload"):
                        st.json(item.request.to_dict())

    with tab_audit:
        st.subheader("Audit Report Viewer")

        audit_path = st.text_input(
            "Audit report path",
            value=studio_config.default_audit_report_path or "",
            placeholder="data/inquiries/inquiry_001/audit_report.json",
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
                else:
                    st.error("Audit status: not publishable")

                axis_cols = st.columns(4)

                for index, axis in enumerate(summary.axes):
                    with axis_cols[index]:
                        st.metric(
                            label=axis.axis.replace("_", " ").title(),
                            value=axis.status.upper(),
                            delta=axis.score,
                        )

                if summary.blocking_issues:
                    st.subheader("Blocking Issues")
                    for issue in summary.blocking_issues:
                        st.error(issue)

                if summary.warning_issues:
                    st.subheader("Warnings")
                    for issue in summary.warning_issues:
                        st.warning(issue)

                with st.expander("Raw audit report"):
                    st.json(report)

    with tab_progress:
        st.subheader("Run Progress")

        progress_path = st.text_input(
            "Progress log path",
            value=studio_config.default_progress_log_path or "",
            placeholder="logs/runs/latest_progress.json",
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
                    st.write(f"**Status:** {summary['status']}")
                    st.write(f"**Current step:** {summary['current_step'] or 'None'}")
                    st.write(f"**Elapsed seconds:** {summary['elapsed_seconds']}")

                    metric_cols = st.columns(5)
                    metric_cols[0].metric("Completed", summary["completed_steps"])
                    metric_cols[1].metric("Running", summary["running_steps"])
                    metric_cols[2].metric("Queued", summary["queued_steps"])
                    metric_cols[3].metric("Skipped", summary["skipped_steps"])
                    metric_cols[4].metric("Failed", summary["failed_steps"])

                    for step in progress.steps:
                        with st.container(border=True):
                            st.write(f"**{step.name}**")
                            st.write(f"Status: `{step.status}`")

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
        )

        if st.button("Sync from Backend"):
            try:
                client = BackendClient(
                    BackendClientConfig(
                        base_url=getattr(
                            studio_config,
                            "backend_base_url",
                            None,
                        )
                        or "http://127.0.0.1:8000",
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
                    st.write(f"**Status:** {summary['status']}")
                    st.write(f"**Current step:** {summary['current_step'] or 'None'}")

                    if result.snapshot_path:
                        st.write(f"Snapshot saved to: `{result.snapshot_path}`")

                    record_activity(
                        activity_type="progress_viewed",
                        message=f"Synced backend progress for run {result.run_id}.",
                        run_id=result.run_id,
                        artifact_path=result.snapshot_path,
                        log_path=studio_config.operator_activity_log_path,
                    )

                    with st.expander("Synced progress payload"):
                        st.json(result.to_dict())
                else:
                    st.error(result.message)
                    st.json(result.to_dict())

            except ValueError as error:
                st.error(str(error))

    with tab_activity:
        st.subheader("Operator Activity Log")

        activities = read_activity_log(
            studio_config.operator_activity_log_path,
            limit=200,
        )

        col_query, col_type = st.columns([3, 1])

        with col_query:
            activity_query = st.text_input("Search activity")

        with col_type:
            activity_type = st.selectbox(
                "Activity type",
                options=["all", *sorted(VALID_ACTIVITY_TYPES)],
            )

        visible_activities = filter_activities(
            activities,
            activity_type=activity_type,
            query=activity_query,
        )

        if not visible_activities:
            st.info("No operator activity recorded yet.")
        else:
            for activity in visible_activities:
                with st.container(border=True):
                    st.write(f"**{activity.activity_type.replace('_', ' ').title()}**")
                    st.write(activity.message)
                    st.caption(activity.created_at)

                    details = {
                        "request_id": activity.request_id,
                        "inquiry_id": activity.inquiry_id,
                        "run_id": activity.run_id,
                        "artifact_path": activity.artifact_path,
                        "metadata": activity.metadata or {},
                    }

                    with st.expander("Details"):
                        st.json(details)

    with tab_health:
        st.subheader("Studio Health Check")

        health_report = run_studio_health_checks(studio_config)

        if health_report.is_ready:
            st.success("Studio status: ready")
        else:
            st.error("Studio status: needs attention")

        metric_cols = st.columns(3)
        metric_cols[0].metric("Passing", health_report.passing_count)
        metric_cols[1].metric("Warnings", health_report.warning_count)
        metric_cols[2].metric("Failing", health_report.failing_count)

        for check in health_report.checks:
            with st.container(border=True):
                st.write(f"**{check.name}**")
                st.write(f"Status: `{check.status}`")
                st.write(check.message)

                if check.path:
                    st.caption(check.path)

        with st.expander("Raw health report"):
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

    with tab_backend:
        st.subheader("Backend Connection")

        backend_base_url = st.text_input(
            "Backend base URL",
            value=getattr(studio_config, "backend_base_url", None)
            or "http://127.0.0.1:8000",
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
                else:
                    st.error(response.error_message or "Backend health check failed.")

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
                        base_url=getattr(
                            studio_config,
                            "backend_base_url",
                            None,
                        )
                        or "http://127.0.0.1:8000",
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

                st.json(result.to_dict())

            except ValueError as error:
                st.error(str(error))


if __name__ == "__main__":
    run_streamlit_app()
