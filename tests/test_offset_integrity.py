import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.source.transcript_loader import add_character_offsets
from src.core.transcript_processor import process_transcript


def test_cleaning_does_not_break_raw_offsets():
    raw_segments = [
        {
            "text": "  Um, [Music] reinforcement    learning is useful uh!  ",
            "start_time": 12.4,
            "end_time": 18.9
        },
        {
            "text": "The agent learns by interacting with an environment.",
            "start_time": 19.0,
            "end_time": 24.2
        }
    ]

    offset_segments, source_text = add_character_offsets(raw_segments)

    processed_segments = process_transcript(offset_segments)

    for segment in processed_segments:
        char_start = segment["char_start"]
        char_end = segment["char_end"]

        raw_slice = source_text[char_start:char_end]

        assert raw_slice == segment["text"]
        assert "cleaned_text" in segment
        assert segment["cleaned_text"] != ""


def test_cleaned_text_is_separate_from_raw_text_when_cleaning_changes_content():
    raw_segments = [
        {
            "text": "  Um, [Music] reinforcement    learning is useful uh!  ",
            "start_time": 12.4,
            "end_time": 18.9
        }
    ]

    offset_segments, source_text = add_character_offsets(raw_segments)
    processed_segments = process_transcript(offset_segments)

    segment = processed_segments[0]

    raw_slice = source_text[segment["char_start"]:segment["char_end"]]

    assert raw_slice == segment["text"]
    assert segment["text"] == "  Um, [Music] reinforcement    learning is useful uh!  "
    assert segment["cleaned_text"] == "reinforcement learning is useful"
    assert segment["text"] != segment["cleaned_text"]


test_cleaning_does_not_break_raw_offsets()
test_cleaned_text_is_separate_from_raw_text_when_cleaning_changes_content()

print("All offset_integrity tests passed.")