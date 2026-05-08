import json
from pathlib import Path

from src.paper.html_audit import audit_html_paper


def _paper_spec() -> dict:
    return {
        "title": "Custom Inquiry Paper",
        "abstract": "Custom paper abstract.",
        "video": {
            "video_id": "ABC123",
            "title": "What Most People Get Wrong About Reinforcement Learning",
            "url": "https://www.youtube.com/watch?v=ABC123",
            "embed_base_url": "https://www.youtube-nocookie.com/embed/ABC123",
            "speaker_name": "Dr. Jane Smith",
            "speaker_credentials": "Professor of Computer Science",
        },
        "speaker_perspective": "The speaker argues from a charitable technical frame.",
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
            }
        ],
        "adjudications": [],
        "limitations": ["Metadata-only retrieval is a limitation."],
        "further_reading": [],
    }


def _valid_html() -> str:
    return """
    <!doctype html>
    <html>
      <body>
        <article class="inquiry-paper">
          <section id="perspective">
            <h2>The Speaker's Perspective</h2>
          </section>

          <section id="claims">
            <article id="claim_0042">
              <iframe
                src="https://www.youtube-nocookie.com/embed/ABC123?start=252&end=263&rel=0"
                loading="lazy"
                allowfullscreen>
              </iframe>
            </article>
          </section>

          <section id="evidence"></section>
          <section id="agreement"></section>
          <section id="complexity"></section>

          <section id="limitations">
            <h2>Open Questions &amp; Limitations</h2>
          </section>

          <section id="reading"></section>

          <section id="references">
            <ol>
              <li id="ev_001">
                <a href="https://example.org/marl-overview">
                  Multi-Agent Reinforcement Learning: A Selective Overview
                </a>
              </li>
            </ol>
          </section>
        </article>
      </body>
    </html>
    """


def test_audit_html_paper_passes_for_valid_html(tmp_path: Path) -> None:
    html_path = tmp_path / "paper.html"
    spec_path = tmp_path / "paper_spec.json"

    html_path.write_text(_valid_html(), encoding="utf-8")
    spec_path.write_text(json.dumps(_paper_spec()), encoding="utf-8")

    report = audit_html_paper(
        html_path=html_path,
        paper_spec_path=spec_path,
    )

    assert report.passed is True
    assert report.checks_run == 5
    assert report.findings == []


def test_audit_html_paper_writes_report_file(tmp_path: Path) -> None:
    html_path = tmp_path / "paper.html"
    spec_path = tmp_path / "paper_spec.json"
    report_path = tmp_path / "html_audit.json"

    html_path.write_text(_valid_html(), encoding="utf-8")
    spec_path.write_text(json.dumps(_paper_spec()), encoding="utf-8")

    report = audit_html_paper(
        html_path=html_path,
        paper_spec_path=spec_path,
        report_output_path=report_path,
    )

    assert report.passed is True
    assert report_path.exists()

    saved_report = json.loads(report_path.read_text(encoding="utf-8"))

    assert saved_report["passed"] is True
    assert saved_report["checks_run"] == 5
    assert saved_report["findings"] == []


def test_audit_html_paper_fails_when_required_section_is_missing(tmp_path: Path) -> None:
    html_path = tmp_path / "paper.html"
    spec_path = tmp_path / "paper_spec.json"

    broken_html = _valid_html().replace('<section id="evidence"></section>', "")

    html_path.write_text(broken_html, encoding="utf-8")
    spec_path.write_text(json.dumps(_paper_spec()), encoding="utf-8")

    report = audit_html_paper(
        html_path=html_path,
        paper_spec_path=spec_path,
    )

    assert report.passed is False
    assert any(
        finding.code == "missing_required_section"
        and 'id="evidence"' in finding.message
        for finding in report.findings
    )


def test_audit_html_paper_fails_when_claim_iframe_timing_is_wrong(tmp_path: Path) -> None:
    html_path = tmp_path / "paper.html"
    spec_path = tmp_path / "paper_spec.json"

    broken_html = _valid_html().replace("start=252&end=263", "start=200&end=210")

    html_path.write_text(broken_html, encoding="utf-8")
    spec_path.write_text(json.dumps(_paper_spec()), encoding="utf-8")

    report = audit_html_paper(
        html_path=html_path,
        paper_spec_path=spec_path,
    )

    assert report.passed is False
    assert any(finding.code == "missing_claim_iframe" for finding in report.findings)


def test_audit_html_paper_fails_for_non_privacy_embed_domain(tmp_path: Path) -> None:
    html_path = tmp_path / "paper.html"
    spec_path = tmp_path / "paper_spec.json"

    broken_html = _valid_html().replace(
        "https://www.youtube-nocookie.com/embed/ABC123",
        "https://www.youtube.com/embed/ABC123",
    )

    html_path.write_text(broken_html, encoding="utf-8")
    spec_path.write_text(json.dumps(_paper_spec()), encoding="utf-8")

    report = audit_html_paper(
        html_path=html_path,
        paper_spec_path=spec_path,
    )

    assert report.passed is False
    assert any(
        finding.code == "non_privacy_respecting_embed"
        for finding in report.findings
    )


def test_audit_html_paper_fails_when_reference_is_missing(tmp_path: Path) -> None:
    html_path = tmp_path / "paper.html"
    spec_path = tmp_path / "paper_spec.json"

    broken_html = _valid_html().replace('id="ev_001"', 'id="ev_missing"')

    html_path.write_text(broken_html, encoding="utf-8")
    spec_path.write_text(json.dumps(_paper_spec()), encoding="utf-8")

    report = audit_html_paper(
        html_path=html_path,
        paper_spec_path=spec_path,
    )

    assert report.passed is False
    assert any(finding.code == "missing_reference_id" for finding in report.findings)