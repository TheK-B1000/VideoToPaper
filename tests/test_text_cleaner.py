import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.core.text_cleaner import clean_text


def test_clean_text_removes_outer_spaces():
    result = clean_text("   hello world   ")
    assert result == "hello world"


def test_clean_text_collapses_extra_spaces():
    result = clean_text("hello      world")
    assert result == "hello world"


def test_clean_text_handles_newlines_and_tabs():
    result = clean_text("AI\nengineering\tis fun")
    assert result == "AI engineering is fun"


def test_clean_text_removes_bracket_tags():
    result = clean_text("[Music] hello world [Applause]")
    assert result == "hello world"


def test_clean_text_removes_filler_words():
    result = clean_text("um hello uh world")
    assert result == "hello world"


def test_clean_text_rejects_non_string():
    try:
        clean_text(123)
        assert False, "Expected TypeError, but no error was raised"
    except TypeError:
        pass


def test_clean_text_rejects_empty_text():
    try:
        clean_text("   ")
        assert False, "Expected ValueError, but no error was raised"
    except ValueError:
        pass


def test_clean_text_uses_config_to_keep_fillers():
    config = {
        "transcript": {
            "remove_bracket_tags": True,
            "remove_fillers": False,
            "fillers": ["um", "uh"],
            "allow_empty_text": False
        }
    }

    result = clean_text("um hello uh world", config)

    assert result == "um hello uh world"


def test_clean_text_uses_config_to_keep_bracket_tags():
    config = {
        "transcript": {
            "remove_bracket_tags": False,
            "remove_fillers": True,
            "fillers": ["um", "uh"],
            "allow_empty_text": False
        }
    }

    result = clean_text("[Music] hello world", config)

    assert result == "[Music] hello world"


test_clean_text_removes_outer_spaces()
test_clean_text_collapses_extra_spaces()
test_clean_text_handles_newlines_and_tabs()
test_clean_text_removes_bracket_tags()
test_clean_text_removes_filler_words()
test_clean_text_rejects_non_string()
test_clean_text_rejects_empty_text()
test_clean_text_uses_config_to_keep_fillers()
test_clean_text_uses_config_to_keep_bracket_tags()

print("All text_cleaner tests passed.")