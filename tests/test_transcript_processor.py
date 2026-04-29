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
            "text": "reinforcement learning is useful",
            "start_time": 12.4,
            "end_time": 18.9
        },
        {
            "text": "The agent learns from rewards.",
            "start_time": 19.0,
            "end_time": 24.2
        }
    ]


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
test_process_transcript_rejects_non_list()
test_process_transcript_rejects_empty_list()
test_process_transcript_rejects_invalid_segment()

print("All transcript_processor tests passed.")