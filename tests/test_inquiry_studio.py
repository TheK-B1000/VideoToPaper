import json
from pathlib import Path

import pytest

from src.frontend.inquiry_studio import (
    build_run_parameters,
    discover_inquiries,
    filter_inquiries,
    load_audit_report,
    paper_exists,
    parse_youtube_video_id,
    render_brand_header_html,
    render_empty_state_html,
    render_hero_html,
    render_last_action_panel_html,
    render_metric_cards,
    render_state_chip,
    render_studio_css,
)
from src.frontend.state import LastAction


def test_parse_youtube_video_id_from_watch_url():
    video_id = parse_youtube_video_id(
        "https://www.youtube.com/watch?v=ABC123xyz_9"
    )

    assert video_id == "ABC123xyz_9"


def test_parse_youtube_video_id_from_short_url():
    video_id = parse_youtube_video_id("https://youtu.be/ABC123xyz_9")

    assert video_id == "ABC123xyz_9"


def test_parse_youtube_video_id_rejects_invalid_url():
    with pytest.raises(ValueError, match="Could not parse"):
        parse_youtube_video_id("https://example.com/not-youtube")


def test_build_run_parameters_normalizes_values():
    params = build_run_parameters(
        youtube_url=" https://www.youtube.com/watch?v=ABC123xyz_9 ",
        claim_type_filter=[
            "empirical_technical",
            "empirical_technical",
            "predictive",
        ],
        retrieval_depth=3,
        source_tiers=[2, 1, 2],
    )

    assert params.youtube_url == "https://www.youtube.com/watch?v=ABC123xyz_9"
    assert params.video_id == "ABC123xyz_9"
    assert params.claim_type_filter == ["empirical_technical", "predictive"]
    assert params.retrieval_depth == 3
    assert params.source_tiers == [1, 2]


def test_build_run_parameters_rejects_empty_source_tiers():
    with pytest.raises(ValueError, match="At least one source tier"):
        build_run_parameters(
            youtube_url="https://www.youtube.com/watch?v=ABC123xyz_9",
            claim_type_filter=["empirical_technical"],
            retrieval_depth=3,
            source_tiers=[],
        )


def test_build_run_parameters_rejects_invalid_source_tier():
    with pytest.raises(ValueError, match="source_tiers"):
        build_run_parameters(
            youtube_url="https://www.youtube.com/watch?v=ABC123xyz_9",
            claim_type_filter=["empirical_technical"],
            retrieval_depth=3,
            source_tiers=[1, 4],
        )


def test_build_run_parameters_rejects_invalid_retrieval_depth():
    with pytest.raises(ValueError, match="retrieval_depth"):
        build_run_parameters(
            youtube_url="https://www.youtube.com/watch?v=ABC123xyz_9",
            claim_type_filter=["empirical_technical"],
            retrieval_depth=0,
            source_tiers=[1],
        )


def test_discover_inquiries_reads_manifest_files(tmp_path: Path):
    inquiry_dir = tmp_path / "data" / "inquiries" / "inquiry_001"
    inquiry_dir.mkdir(parents=True)

    manifest = {
        "inquiry_id": "inquiry_001",
        "title": "Test Inquiry",
        "youtube_url": "https://www.youtube.com/watch?v=ABC123xyz_9",
        "status": "completed",
        "created_at": "2026-05-08T12:00:00",
        "paper_path": "data/inquiries/inquiry_001/paper.html",
        "audit_report_path": "data/inquiries/inquiry_001/audit_report.json",
        "parameters": {
            "retrieval_depth": 3,
            "source_tiers": [1, 2],
        },
    }

    (inquiry_dir / "manifest.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    records = discover_inquiries(tmp_path / "data" / "inquiries")

    assert len(records) == 1
    assert records[0].inquiry_id == "inquiry_001"
    assert records[0].title == "Test Inquiry"
    assert records[0].status == "completed"
    assert records[0].parameters["retrieval_depth"] == 3


def test_discover_inquiries_skips_invalid_manifest(tmp_path: Path):
    good_dir = tmp_path / "data" / "inquiries" / "good"
    bad_dir = tmp_path / "data" / "inquiries" / "bad"

    good_dir.mkdir(parents=True)
    bad_dir.mkdir(parents=True)

    (good_dir / "manifest.json").write_text(
        json.dumps(
            {
                "inquiry_id": "good",
                "title": "Good Inquiry",
                "youtube_url": "https://www.youtube.com/watch?v=ABC123xyz_9",
                "status": "completed",
                "created_at": "2026-05-08T12:00:00",
            }
        ),
        encoding="utf-8",
    )

    (bad_dir / "manifest.json").write_text("{not valid json", encoding="utf-8")

    records = discover_inquiries(tmp_path / "data" / "inquiries")

    assert len(records) == 1
    assert records[0].inquiry_id == "good"


def test_filter_inquiries_by_query_and_status(tmp_path: Path):
    inquiry_dir = tmp_path / "data" / "inquiries" / "inquiry_001"
    inquiry_dir.mkdir(parents=True)

    (inquiry_dir / "manifest.json").write_text(
        json.dumps(
            {
                "inquiry_id": "inquiry_001",
                "title": "Reinforcement Learning Talk",
                "youtube_url": "https://www.youtube.com/watch?v=ABC123xyz_9",
                "status": "completed",
                "created_at": "2026-05-08T12:00:00",
            }
        ),
        encoding="utf-8",
    )

    records = discover_inquiries(tmp_path / "data" / "inquiries")

    filtered = filter_inquiries(
        records,
        query="reinforcement",
        status="completed",
    )

    assert len(filtered) == 1
    assert filtered[0].title == "Reinforcement Learning Talk"

    no_matches = filter_inquiries(
        records,
        query="biology",
        status="completed",
    )

    assert no_matches == []


def test_load_audit_report_returns_json_when_file_exists(tmp_path: Path):
    audit_path = tmp_path / "audit_report.json"

    audit_path.write_text(
        json.dumps(
            {
                "publishable": True,
                "clip_anchor_accuracy": {
                    "clips_within_tolerance": "100%",
                    "tolerance_seconds": 1.0,
                },
            }
        ),
        encoding="utf-8",
    )

    report = load_audit_report(audit_path)

    assert report is not None
    assert report["publishable"] is True
    assert report["clip_anchor_accuracy"]["tolerance_seconds"] == 1.0


def test_load_audit_report_returns_none_when_missing(tmp_path: Path):
    report = load_audit_report(tmp_path / "missing.json")

    assert report is None


def test_load_audit_report_returns_none_for_blank_or_directory_path(tmp_path: Path):
    assert load_audit_report("") is None
    assert load_audit_report("   ") is None
    assert load_audit_report(".") is None
    assert load_audit_report(tmp_path) is None


def test_paper_exists_detects_existing_html_file(tmp_path: Path):
    paper_path = tmp_path / "paper.html"
    paper_path.write_text("<html></html>", encoding="utf-8")

    assert paper_exists(paper_path) is True
    assert paper_exists(tmp_path / "missing.html") is False
    assert paper_exists(None) is False


def test_render_studio_css_includes_design_tokens_and_card_classes():
    css = render_studio_css()

    assert "--studio-primary" in css
    assert "--studio-accent" in css
    assert ".studio-hero" in css
    assert ".metric-card" in css
    assert ".state-chip" in css


def test_render_brand_header_html_includes_title_and_environment():
    html = render_brand_header_html(
        title="Studio <Test>",
        subtitle="Local operator shell",
        environment="Local",
    )

    assert "Studio &lt;Test&gt;" in html
    assert "Local operator shell" in html
    assert "Local" in html
    assert "Build " not in html


def test_render_hero_html_includes_micro_guide():
    html = render_hero_html()

    assert "Create inquiry in 60 seconds" in html
    assert "1. Source" in html
    assert "2. Queue" in html
    assert "3. Inspect" in html


def test_render_state_chip_uses_semantic_tones_and_escapes_label():
    completed = render_state_chip("completed")
    failed = render_state_chip("failed")
    unsafe = render_state_chip("unknown", "<script>")

    assert "state-chip--success" in completed
    assert "COMPLETED" in completed
    assert "state-chip--danger" in failed
    assert "&lt;SCRIPT&gt;" in unsafe
    assert "<script>" not in unsafe


def test_render_metric_cards_normalizes_tone_and_escapes_text():
    html = render_metric_cards(
        [
            {
                "label": "Warnings",
                "value": 2,
                "detail": "2 blocking <issues>",
                "tone": "warning",
            },
            {
                "label": "Unsafe",
                "value": "<bad>",
                "detail": "ignored class",
                "tone": "unexpected tone",
            },
        ]
    )

    assert "metric-card--warning" in html
    assert "metric-card--neutral" in html
    assert "2 blocking &lt;issues&gt;" in html
    assert "&lt;bad&gt;" in html
    assert "metric-card--unexpected tone" not in html


def test_render_empty_state_html_explains_next_action_and_escapes_text():
    html = render_empty_state_html(
        icon="?",
        title="Nothing <yet>",
        body="Create a request.",
        action="Use <Prepare Request>.",
    )

    assert "Nothing &lt;yet&gt;" in html
    assert "Create a request." in html
    assert "Next action:" in html
    assert "Use &lt;Prepare Request&gt;." in html


def test_render_last_action_panel_html_shows_status_and_artifact():
    html = render_last_action_panel_html(
        LastAction(
            title="Run launched <ok>",
            message="Progress log ready.",
            status="success",
            artifact_path="logs/runs/run_001/progress.json",
            created_at="2026-05-08T12:00:00Z",
        )
    )

    assert "Run launched &lt;ok&gt;" in html
    assert "Progress log ready." in html
    assert "state-chip--success" in html
    assert "logs/runs/run_001/progress.json" in html


def test_render_last_action_panel_html_returns_empty_string_without_action():
    assert render_last_action_panel_html(None) == ""
