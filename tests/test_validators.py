import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.data.validators import validate_segment


def test_validate_segment_accepts_valid_segment():
    segment = {
        "text": "  Um, reinforcement    learning is useful uh! ",
        "start_time": 12.4,
        "end_time": 18.9
    }

    result = validate_segment(segment)

    assert result == {
        "text": "reinforcement learning is useful",
        "start_time": 12.4,
        "end_time": 18.9
    }


def test_validate_segment_rejects_non_dict():
    try:
        validate_segment("not a dictionary")
        assert False, "Expected TypeError, but no error was raised"
    except TypeError:
        pass


def test_validate_segment_rejects_missing_text():
    segment = {
        "start_time": 12.4,
        "end_time": 18.9
    }

    try:
        validate_segment(segment)
        assert False, "Expected ValueError, but no error was raised"
    except ValueError:
        pass


def test_validate_segment_rejects_missing_start_time():
    segment = {
        "text": "hello",
        "end_time": 18.9
    }

    try:
        validate_segment(segment)
        assert False, "Expected ValueError, but no error was raised"
    except ValueError:
        pass


def test_validate_segment_rejects_missing_end_time():
    segment = {
        "text": "hello",
        "start_time": 12.4
    }

    try:
        validate_segment(segment)
        assert False, "Expected ValueError, but no error was raised"
    except ValueError:
        pass


def test_validate_segment_rejects_non_string_text():
    segment = {
        "text": 123,
        "start_time": 12.4,
        "end_time": 18.9
    }

    try:
        validate_segment(segment)
        assert False, "Expected TypeError, but no error was raised"
    except TypeError:
        pass


def test_validate_segment_rejects_non_numeric_start_time():
    segment = {
        "text": "hello",
        "start_time": "12.4",
        "end_time": 18.9
    }

    try:
        validate_segment(segment)
        assert False, "Expected TypeError, but no error was raised"
    except TypeError:
        pass


def test_validate_segment_rejects_non_numeric_end_time():
    segment = {
        "text": "hello",
        "start_time": 12.4,
        "end_time": "18.9"
    }

    try:
        validate_segment(segment)
        assert False, "Expected TypeError, but no error was raised"
    except TypeError:
        pass


def test_validate_segment_rejects_negative_start_time():
    segment = {
        "text": "hello",
        "start_time": -1.0,
        "end_time": 3.0
    }

    try:
        validate_segment(segment)
        assert False, "Expected ValueError, but no error was raised"
    except ValueError:
        pass


def test_validate_segment_rejects_end_time_before_start_time():
    segment = {
        "text": "bad timing",
        "start_time": 18.9,
        "end_time": 12.4
    }

    try:
        validate_segment(segment)
        assert False, "Expected ValueError, but no error was raised"
    except ValueError:
        pass


def test_validate_segment_rejects_equal_start_and_end_time():
    segment = {
        "text": "zero duration",
        "start_time": 12.4,
        "end_time": 12.4
    }

    try:
        validate_segment(segment)
        assert False, "Expected ValueError, but no error was raised"
    except ValueError:
        pass


test_validate_segment_accepts_valid_segment()
test_validate_segment_rejects_non_dict()
test_validate_segment_rejects_missing_text()
test_validate_segment_rejects_missing_start_time()
test_validate_segment_rejects_missing_end_time()
test_validate_segment_rejects_non_string_text()
test_validate_segment_rejects_non_numeric_start_time()
test_validate_segment_rejects_non_numeric_end_time()
test_validate_segment_rejects_negative_start_time()
test_validate_segment_rejects_end_time_before_start_time()
test_validate_segment_rejects_equal_start_and_end_time()

print("All validators tests passed.")