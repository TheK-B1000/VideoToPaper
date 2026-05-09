import json
import sys
import tempfile
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.pipelines.paper_evidence_integration_finalize import (
    enrich_evidence_records_for_paper,
    finalize_evidence_integration_json_for_paper,
)


def test_enrich_evidence_records_for_paper_fills_missing_evidence_id():
    rows = [{"claim_id": "c", "identifier": "pub:1", "title": "t", "source": "s", "url": "u", "tier": 1, "stance": "supports"}]
    out = enrich_evidence_records_for_paper(rows)
    assert out[0]["evidence_id"] == "pub:1"


def test_finalize_evidence_integration_json_for_paper_merges_steelman_and_evidence():
    tmp_path = Path(tempfile.mkdtemp())
    integration = tmp_path / "evidence_integration.json"
    integration.write_text(
        json.dumps({"schema_version": "week7.v1", "adjudications": []}),
        encoding="utf-8",
    )
    sp = tmp_path / "speaker_perspective.json"
    sp.write_text(
        json.dumps(
            {
                "narrative_blocks": [
                    {"text": "Hello perspective.", "verbatim_anchors": []},
                ]
            }
        ),
        encoding="utf-8",
    )
    ev_path = tmp_path / "evidence_records.json"
    ev_path.write_text(
        json.dumps(
            [
                {
                    "claim_id": "c1",
                    "title": "Dry",
                    "source": "DryRun",
                    "tier": 1,
                    "stance": "supports",
                    "identifier": "id:x",
                    "url": "https://example.com",
                }
            ]
        ),
        encoding="utf-8",
    )

    finalize_evidence_integration_json_for_paper(
        integration_path=integration,
        speaker_perspective_path=sp,
        evidence_records_path=ev_path,
    )

    merged = json.loads(integration.read_text(encoding="utf-8"))
    assert merged["steelman"]["narrative_blocks"][0]["text"] == "Hello perspective."
    assert merged["evidence_records"][0]["evidence_id"] == "id:x"


test_enrich_evidence_records_for_paper_fills_missing_evidence_id()
test_finalize_evidence_integration_json_for_paper_merges_steelman_and_evidence()

print("All paper_evidence_integration_finalize tests passed.")
