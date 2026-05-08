import json
import subprocess
import sys
from pathlib import Path


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
                    "Multi-agent environments can violate stationarity assumptions, "
                    "but specialized MARL methods address this problem."
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
                "supports": [],
                "complicates": [],
                "contradicts": [],
                "qualifies": ["ev_001"],
            }
        ],
        "limitations": [
            "This pass relies on retrieved metadata and does not yet verify full-text source claims."
        ],
        "further_reading": [],
    }


def test_main_html_paper_stage_writes_output_file(tmp_path: Path) -> None:
    paper_spec_path = tmp_path / "paper_spec.json"
    output_path = tmp_path / "inquiry_paper.html"

    paper_spec_path.write_text(json.dumps(_paper_spec()), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "main.py",
            "--stage",
            "html_paper",
            "--paper-spec-path",
            str(paper_spec_path),
            "--html-output-path",
            str(output_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert output_path.exists()
    assert "HTML paper written to:" in result.stdout

    html = output_path.read_text(encoding="utf-8")

    assert '<article class="inquiry-paper">' in html
    assert "The Speaker's Perspective" in html
    assert "Claims Under Examination" in html
    assert "Evidence Review" in html
    assert "Open Questions &amp; Limitations" in html or "Open Questions & Limitations" in html
    assert "References" in html
    assert "https://www.youtube-nocookie.com/embed/ABC123?start=252&end=263&rel=0" in html
