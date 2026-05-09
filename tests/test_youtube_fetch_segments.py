import sys
from dataclasses import dataclass
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.pipelines.evidence_retrieval_flatten import flatten_evidence_records
from src.source.youtube_fetch import (
    fetched_snippets_to_raw_segments,
    normalize_caption_word_spacing,
)


@dataclass
class _FakeSnippet:
    text: str
    start: float
    duration: float


def test_fetched_snippets_to_raw_segments_skips_blank_and_fixes_zero_duration():
    snippets = [
        _FakeSnippet("  ", 1.0, 1.0),
        _FakeSnippet("Hello", 2.0, 0.0),
        _FakeSnippet("World", 5.0, 1.5),
    ]
    rows = fetched_snippets_to_raw_segments(snippets)
    assert rows == [
        {"text": "Hello", "start_time": 2.0, "end_time": 2.05},
        {"text": "World", "start_time": 5.0, "end_time": 6.5},
    ]


def test_normalize_caption_word_spacing_repairs_glued_youtube_tokens():
    raw = "foreignthat even at the present stage ofcivilization in this world there aresouls"
    fixed = normalize_caption_word_spacing(raw)
    assert "foreign that" in fixed
    assert "of civilization" in fixed
    assert "are souls" in fixed


def test_fetched_snippets_to_raw_segments_normalizes_glued_caption_text():
    snippets = [
        _FakeSnippet("foreignthat even", 0.0, 1.0),
    ]
    rows = fetched_snippets_to_raw_segments(snippets)
    assert rows[0]["text"] == "foreign that even"


def test_flatten_evidence_records_nested_retrieval_results():
    doc = {
        "retrieval_results": [
            {"evidence_records": [{"claim_id": "a", "evidence_id": "e1"}]},
            {"evidence_records": [{"claim_id": "a", "evidence_id": "e2"}]},
        ]
    }
    flat = flatten_evidence_records(doc)
    assert len(flat) == 2
    assert flat[0]["evidence_id"] == "e1"


test_fetched_snippets_to_raw_segments_skips_blank_and_fixes_zero_duration()
test_normalize_caption_word_spacing_repairs_glued_youtube_tokens()
test_fetched_snippets_to_raw_segments_normalizes_glued_caption_text()
test_flatten_evidence_records_nested_retrieval_results()

print("All youtube_fetch / flatten tests passed.")
