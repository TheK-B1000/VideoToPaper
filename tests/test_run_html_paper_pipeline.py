import json
from pathlib import Path

import pytest

from src.pipelines.run_html_paper_pipeline import (
    HtmlPaperPipelineError,
    run_html_paper_pipeline,
)


def _paper_spec() -> dict:
    return {
        "title": "Inquiry Paper: Reinforcement Learning Misconceptions",
        "abstract": "A charitable review of a technical claim about reinforcement learning.",
        "video": {
            "video_id": "ABC123",
            "title": "What Most People Get Wrong About Reinforcement Learning",
            "url": "https://www.youtube.com/watch?v=ABC123",
            "embed_base_url": "https://www.youtube-nocookie.com/embed/ABC123",
            "speaker_name": "Dr. Jane Smith",
            "speaker_credentials": "Professor of Computer Science",
        },
        "speaker_perspective": (
            "The speaker argues that naive single-agent assumptions become fragile "
            "when moved into adaptive multi-agent settings."
        ),
        "claims": [
            {
                "claim_id": "claim_0042",
                "verbatim_quote": "non-stationarity makes single-agent algorithms fundamentally unsuited",
                "claim_type": "empirical_technical",
                "anchor_clip_start": 252.4,
                "anchor_clip_end": 263.0,
            }
        ],
        "evidence_records": [
            {
                "evidence_id": "ev_001",
                "claim_id": "claim_0042",
                "title": "Multi-Agent Reinforcement Learning: A Selective Overview",
                "source": "Journal of Artificial Intelligence Research",
                "url": "https://example.org/marl-overview",
                "tier": 1,
                "stance": "qualifies",
                "identifier": "doi:10.0000/example",
                "key_finding": (
                    "Multi-agent settings can violate stationarity assumptions, "
                    "but specialized approaches address this problem."
                ),
            }
        ],
        "adjudications": [
            {
                "claim_id": "claim_0042",
                "verdict": "well_supported_with_qualifications",
                "confidence": "high",
                "narrative": (
                    "The speaker's claim is directionally supported, but the literature "
                    "shows that specialized multi-agent methods complicate the strongest version."
                ),
                "qualifies": ["ev_001"],
            }
        ],
        "limitations": [
            "This pass relies on retrieved metadata and does not yet verify full-text source claims."
        ],
        "further_reading": [
            {
                "evidence_id": "ev_001",
                "claim_id": "claim_0042",
                "title": "Multi-Agent Reinforcement Learning: A Selective Overview",
                "source": "Journal of Artificial Intelligence Research",
                "url": "https://example.org/marl-overview",
                "tier": 1,
                "stance": "qualifies",
                "identifier": "doi:10.0000/example",
                "key_finding": (
                    "Multi-agent settings can violate stationarity assumptions, "
                    "but specialized approaches address this problem."
                ),
            }
        ],
    }


def test_run_html_paper_pipeline_writes_html_file(tmp_path: Path) -> None:
    paper_spec_path = tmp_path / "paper_spec.json"
    output_path = tmp_path / "paper.html"

    paper_spec_path.write_text(json.dumps(_paper_spec()), encoding="utf-8")

    result = run_html_paper_pipeline(
        paper_spec_path=paper_spec_path,
        output_path=output_path,
    )

    assert result == output_path
    assert output_path.exists()

    html = output_path.read_text(encoding="utf-8")

    assert '<article class="inquiry-paper">' in html
    assert "Inquiry Paper: Reinforcement Learning Misconceptions" in html
    assert (
        "https://www.youtube-nocookie.com/embed/ABC123?start=252&end=263&rel=0" in html
        or "https://www.youtube-nocookie.com/embed/ABC123?start=252&amp;end=263&amp;rel=0"
        in html
    )
    assert "Source Attribution" in html
    assert "Open Questions &amp; Limitations" in html or "Open Questions & Limitations" in html


def test_run_html_paper_pipeline_rejects_missing_spec_file(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.json"
    output_path = tmp_path / "paper.html"

    with pytest.raises(HtmlPaperPipelineError, match="does not exist"):
        run_html_paper_pipeline(
            paper_spec_path=missing_path,
            output_path=output_path,
        )


def test_run_html_paper_pipeline_rejects_invalid_json(tmp_path: Path) -> None:
    paper_spec_path = tmp_path / "bad.json"
    output_path = tmp_path / "paper.html"

    paper_spec_path.write_text("{bad json", encoding="utf-8")

    with pytest.raises(HtmlPaperPipelineError, match="Invalid JSON"):
        run_html_paper_pipeline(
            paper_spec_path=paper_spec_path,
            output_path=output_path,
        )


def test_run_html_paper_pipeline_rejects_missing_required_field(tmp_path: Path) -> None:
    spec = _paper_spec()
    spec.pop("claims")

    paper_spec_path = tmp_path / "paper_spec.json"
    output_path = tmp_path / "paper.html"

    paper_spec_path.write_text(json.dumps(spec), encoding="utf-8")

    with pytest.raises(HtmlPaperPipelineError, match="missing required field: claims"):
        run_html_paper_pipeline(
            paper_spec_path=paper_spec_path,
            output_path=output_path,
        )


def test_run_html_paper_pipeline_rejects_bad_claim_timing(tmp_path: Path) -> None:
    spec = _paper_spec()
    spec["claims"][0]["anchor_clip_start"] = 300
    spec["claims"][0]["anchor_clip_end"] = 200

    paper_spec_path = tmp_path / "paper_spec.json"
    output_path = tmp_path / "paper.html"

    paper_spec_path.write_text(json.dumps(spec), encoding="utf-8")

    with pytest.raises(Exception, match="invalid anchor clip range|Clip end must be greater"):
        run_html_paper_pipeline(
            paper_spec_path=paper_spec_path,
            output_path=output_path,
        )