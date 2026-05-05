from pathlib import Path

from src.pipelines.claim_inventory_pipeline import (
    DEFAULT_ARGUMENT_MAP_PATH,
    DEFAULT_CHUNKS_PATH,
    _resolve_week2_input_path,
)


def test_resolve_week2_input_path_prefers_output_paths_chunks():
    config = {"output_paths": {"chunks": "data/outputs/chunks.json"}}
    resolved = _resolve_week2_input_path(
        config,
        output_paths_key="chunks",
        explicit=None,
        fallback=DEFAULT_CHUNKS_PATH,
    )
    assert resolved == Path("data/outputs/chunks.json")


def test_resolve_week2_input_path_prefers_explicit_over_config():
    config = {"output_paths": {"chunks": "data/outputs/chunks.json"}}
    resolved = _resolve_week2_input_path(
        config,
        output_paths_key="chunks",
        explicit="data/custom/chunks.json",
        fallback=DEFAULT_CHUNKS_PATH,
    )
    assert resolved == Path("data/custom/chunks.json")


def test_resolve_week2_input_path_falls_back_when_missing_output_paths():
    resolved = _resolve_week2_input_path(
        {},
        output_paths_key="chunks",
        explicit=None,
        fallback=DEFAULT_CHUNKS_PATH,
    )
    assert resolved == DEFAULT_CHUNKS_PATH


def test_resolve_week2_argument_map_from_output_paths():
    config = {"output_paths": {"argument_map": "data/outputs/argument_map.json"}}
    resolved = _resolve_week2_input_path(
        config,
        output_paths_key="argument_map",
        explicit=None,
        fallback=DEFAULT_ARGUMENT_MAP_PATH,
    )
    assert resolved == Path("data/outputs/argument_map.json")
