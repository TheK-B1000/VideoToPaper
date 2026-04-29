import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.data.json_store import load_json, save_json

def test_save_and_load_json():
    file_path = "data/outputs/test_json_store.json"
    data = {
        "message": "hello",
        "count": 3
    }

    save_json(data, file_path)
    result = load_json(file_path)

    assert result == data


def test_load_json_rejects_missing_file():
    try:
        load_json("data/outputs/does_not_exist.json")
        assert False, "Expected FileNotFoundError, but no error was raised"
    except FileNotFoundError:
        pass


def test_load_json_rejects_non_string_path():
    try:
        load_json(123)
        assert False, "Expected TypeError, but no error was raised"
    except TypeError:
        pass


def test_save_json_rejects_non_string_path():
    try:
        save_json({"message": "hello"}, 123)
        assert False, "Expected TypeError, but no error was raised"
    except TypeError:
        pass


def test_save_json_creates_parent_directories():
    file_path = "data/outputs/nested/test_file.json"
    data = {
        "status": "created nested folder"
    }

    save_json(data, file_path)

    assert Path(file_path).exists()
    assert load_json(file_path) == data


test_save_and_load_json()
test_load_json_rejects_missing_file()
test_load_json_rejects_non_string_path()
test_save_json_rejects_non_string_path()
test_save_json_creates_parent_directories()

print("All json_store tests passed.")