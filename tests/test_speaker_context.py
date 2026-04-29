import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.source.speaker_context import capture_speaker_context


def test_capture_speaker_context_accepts_valid_context():
    result = capture_speaker_context(
        name=" Dr. Jane Smith ",
        credentials=" Professor of Computer Science ",
        stated_motivations=" Concerned about misconceptions in popular AI discourse ",
        notes=" Long-form interview "
    )

    assert result == {
        "name": "Dr. Jane Smith",
        "credentials": "Professor of Computer Science",
        "stated_motivations": "Concerned about misconceptions in popular AI discourse",
        "notes": "Long-form interview"
    }


def test_capture_speaker_context_allows_optional_fields():
    result = capture_speaker_context(name="Dr. Jane Smith")

    assert result == {
        "name": "Dr. Jane Smith",
        "credentials": "",
        "stated_motivations": "",
        "notes": ""
    }


def test_capture_speaker_context_rejects_empty_name():
    try:
        capture_speaker_context(name="   ")
        assert False, "Expected ValueError, but no error was raised"
    except ValueError:
        pass


def test_capture_speaker_context_rejects_non_string_name():
    try:
        capture_speaker_context(name=123)
        assert False, "Expected TypeError, but no error was raised"
    except TypeError:
        pass


def test_capture_speaker_context_rejects_non_string_credentials():
    try:
        capture_speaker_context(
            name="Dr. Jane Smith",
            credentials=123
        )
        assert False, "Expected TypeError, but no error was raised"
    except TypeError:
        pass


test_capture_speaker_context_accepts_valid_context()
test_capture_speaker_context_allows_optional_fields()
test_capture_speaker_context_rejects_empty_name()
test_capture_speaker_context_rejects_non_string_name()
test_capture_speaker_context_rejects_non_string_credentials()

print("All speaker_context tests passed.")