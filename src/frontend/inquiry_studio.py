from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


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

    st.title("Inquiry Studio")
    st.caption("Operate the video-to-paper engine from one local cockpit.")

    library_dir = Path("data/inquiries")

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

        if st.button("Prepare Run Config", use_container_width=True):
            try:
                params = build_run_parameters(
                    youtube_url=youtube_url,
                    claim_type_filter=claim_type_filter,
                    retrieval_depth=retrieval_depth,
                    source_tiers=source_tiers,
                )
                st.success("Run config is valid.")
                st.json(params.to_dict())
            except ValueError as error:
                st.error(str(error))

    tab_library, tab_audit = st.tabs(["Inquiry Library", "Audit Inspector"])

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

                    cols = st.columns(3)

                    with cols[0]:
                        if paper_exists(record.paper_path):
                            st.link_button(
                                "Open Paper",
                                Path(record.paper_path).as_posix(),
                                use_container_width=True,
                            )
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
                        st.button(
                            "Re-run",
                            key=f"rerun-{record.inquiry_id}",
                            use_container_width=True,
                            help="Backend wiring comes next.",
                        )

                    with st.expander("Run parameters"):
                        st.json(record.parameters)

    with tab_audit:
        st.subheader("Audit Report Viewer")

        audit_path = st.text_input(
            "Audit report path",
            placeholder="data/inquiries/inquiry_001/audit_report.json",
        )

        if st.button("Load Audit Report"):
            report = load_audit_report(audit_path)

            if report is None:
                st.error("Audit report could not be loaded.")
            else:
                st.json(report)


if __name__ == "__main__":
    run_streamlit_app()
