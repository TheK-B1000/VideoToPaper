import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.core.transcript_processor import process_transcript

def test_process_transcript_accepts_valid_transcript():
    raw_transcript = [
        {
            "text": "  Um, reinforcement    learning is useful uh! ",
            "start_time": 12.4,
            "end_time": 18.9
        },
        {
            "text": "The agent learns from rewards.",
            "start_time": 19.0,
            "end_time": 24.2
        }
    ]

    result = process_transcript(raw_transcript)

    assert result == [
        {
            "text": "  Um, reinforcement    learning is useful uh! ",
            "cleaned_text": "reinforcement learning is useful",
            "start_time": 12.4,
            "end_time": 18.9
        },
        {
            "text": "The agent learns from rewards.",
            "cleaned_text": "The agent learns from rewards.",
            "start_time": 19.0,
            "end_time": 24.2
        }
    ]


def test_process_transcript_preserves_offsets():
    raw_transcript = [
        {
            "text": "  Um, reinforcement learning is useful uh! ",
            "start_time": 12.4,
            "end_time": 18.9,
            "char_start": 0,
            "char_end": 42
        }
    ]

    result = process_transcript(raw_transcript)

    assert result[0]["text"] == "  Um, reinforcement learning is useful uh! "
    assert result[0]["cleaned_text"] == "reinforcement learning is useful"
    assert result[0]["char_start"] == 0
    assert result[0]["char_end"] == 42


def test_process_transcript_offsets_still_match_source_text():
    source_text = (
        "Intro.   Um, reinforcement learning is useful uh! "
        "The agent learns from rewards."
    )
    segment_text = "  Um, reinforcement learning is useful uh! "
    char_start = source_text.index(segment_text)
    char_end = char_start + len(segment_text)
    raw_transcript = [
        {
            "text": segment_text,
            "start_time": 12.4,
            "end_time": 18.9,
            "char_start": char_start,
            "char_end": char_end
        }
    ]

    result = process_transcript(raw_transcript)

    assert source_text[result[0]["char_start"]:result[0]["char_end"]] == result[0]["text"]
    assert result[0]["cleaned_text"] == "reinforcement learning is useful"


def test_process_transcript_rejects_non_list():
    try:
        process_transcript("not a list")
        assert False, "Expected TypeError, but no error was raised"
    except TypeError:
        pass


def test_process_transcript_rejects_empty_list():
    try:
        process_transcript([])
        assert False, "Expected ValueError, but no error was raised"
    except ValueError:
        pass


def test_process_transcript_rejects_invalid_segment():
    raw_transcript = [
        {
            "text": "valid segment",
            "start_time": 1.0,
            "end_time": 2.0
        },
        {
            "text": "bad segment",
            "start_time": 5.0,
            "end_time": 3.0
        }
    ]

    try:
        process_transcript(raw_transcript)
        assert False, "Expected ValueError, but no error was raised"
    except ValueError:
        pass


test_process_transcript_accepts_valid_transcript()
test_process_transcript_preserves_offsets()
test_process_transcript_offsets_still_match_source_text()
test_process_transcript_rejects_non_list()
test_process_transcript_rejects_empty_list()
test_process_transcript_rejects_invalid_segment()

print("All transcript_processor tests passed.")
