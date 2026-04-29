import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.data.json_store import save_json
from src.source.transcript_loader import (
    build_source_text,
    add_character_offsets,
    load_transcript,
)


def test_build_source_text_combines_segment_text():
    raw_segments = [
        {
            "text": "Hello world.",
            "start_time": 0.0,
            "end_time": 2.0
        },
        {
            "text": "AI is useful.",
            "start_time": 2.1,
            "end_time": 5.0
        }
    ]

    result = build_source_text(raw_segments)

    assert result == "Hello world. AI is useful."


def test_add_character_offsets_preserves_exact_segment_text():
    raw_segments = [
        {
            "text": "Hello world.",
            "start_time": 0.0,
            "end_time": 2.0
        },
        {
            "text": "AI is useful.",
            "start_time": 2.1,
            "end_time": 5.0
        }
    ]

    segments, source_text = add_character_offsets(raw_segments)

    first_segment = segments[0]
    second_segment = segments[1]

    assert source_text[first_segment["char_start"]:first_segment["char_end"]] == first_segment["text"]
    assert source_text[second_segment["char_start"]:second_segment["char_end"]] == second_segment["text"]


def test_add_character_offsets_adds_expected_offsets():
    raw_segments = [
        {
            "text": "Hello world.",
            "start_time": 0.0,
            "end_time": 2.0
        },
        {
            "text": "AI is useful.",
            "start_time": 2.1,
            "end_time": 5.0
        }
    ]

    segments, source_text = add_character_offsets(raw_segments)

    assert segments[0]["char_start"] == 0
    assert segments[0]["char_end"] == 12
    assert segments[1]["char_start"] == 13
    assert segments[1]["char_end"] == 26
    assert source_text == "Hello world. AI is useful."


def test_load_transcript_returns_source_text_and_segments():
    test_path = "data/raw/test_offset_transcript.json"

    raw_segments = [
        {
            "text": "Hello world.",
            "start_time": 0.0,
            "end_time": 2.0
        },
        {
            "text": "AI is useful.",
            "start_time": 2.1,
            "end_time": 5.0
        }
    ]

    save_json(raw_segments, test_path)

    result = load_transcript(test_path)

    assert "source_text" in result
    assert "segments" in result
    assert result["source_text"] == "Hello world. AI is useful."
    assert len(result["segments"]) == 2


def test_load_transcript_rejects_non_list_json():
    test_path = "data/raw/test_bad_transcript.json"

    save_json({"text": "not a list"}, test_path)

    try:
        load_transcript(test_path)
        assert False, "Expected ValueError, but no error was raised"
    except ValueError:
        pass


test_build_source_text_combines_segment_text()
test_add_character_offsets_preserves_exact_segment_text()
test_add_character_offsets_adds_expected_offsets()
test_load_transcript_returns_source_text_and_segments()
test_load_transcript_rejects_non_list_json()

print("All transcript_loader tests passed.")