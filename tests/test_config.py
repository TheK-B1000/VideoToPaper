import json

import pytest

from src.core.config import load_config


def test_load_config_success(tmp_path):
    config_data = {
        "stage": "argument_structure",
        "input_path": "data/outputs/processed_transcript.json",
        "output_paths": {},
        "chunking": {},
        "anchors": {},
        "llm": {},
        "safety": {},
    }

    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config_data), encoding="utf-8")

    config = load_config(config_path)

    assert config["stage"] == "argument_structure"


def test_load_config_missing_required_key(tmp_path):
    config_data = {
        "stage": "argument_structure"
    }

    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config_data), encoding="utf-8")

    with pytest.raises(ValueError):
        load_config(config_path)


def test_load_config_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_config("does/not/exist.json")