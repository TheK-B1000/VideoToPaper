import json
import subprocess
import sys
from pathlib import Path


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


def test_main_audit_html_paper_stage_writes_passing_report(tmp_path: Path) -> None:
    html_path = tmp_path / "inquiry_paper.html"
    spec_path = tmp_path / "paper_spec.json"
    report_path = tmp_path / "html_audit_report.json"

    html_path.write_text(_valid_html(), encoding="utf-8")
    spec_path.write_text(json.dumps(_paper_spec()), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "main.py",
            "--stage",
            "audit_html_paper",
            "--html-output-path",
            str(html_path),
            "--paper-spec-path",
            str(spec_path),
            "--html-audit-report-path",
            str(report_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "HTML audit report written to:" in result.stdout
    assert "HTML audit passed: True" in result.stdout
    assert report_path.exists()

    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["passed"] is True
    assert report["checks_run"] == 5
    assert report["findings"] == []


def test_main_audit_html_paper_stage_exits_nonzero_when_audit_fails(
    tmp_path: Path,
) -> None:
    html_path = tmp_path / "inquiry_paper.html"
    spec_path = tmp_path / "paper_spec.json"
    report_path = tmp_path / "html_audit_report.json"

    broken_html = _valid_html().replace('<section id="evidence"></section>', "")

    html_path.write_text(broken_html, encoding="utf-8")
    spec_path.write_text(json.dumps(_paper_spec()), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "main.py",
            "--stage",
            "audit_html_paper",
            "--html-output-path",
            str(html_path),
            "--paper-spec-path",
            str(spec_path),
            "--html-audit-report-path",
            str(report_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "HTML audit passed: False" in result.stdout
    assert "missing_required_section" in result.stdout
    assert report_path.exists()

    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["passed"] is False
    assert any(
        finding["code"] == "missing_required_section"
        for finding in report["findings"]
    )
