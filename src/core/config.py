import json
from pathlib import Path
from typing import Any

REQUIRED_TOP_LEVEL_KEYS = [
    "stage",
    "input_path",
    "output_paths",
    "chunking",
    "anchors",
    "llm",
    "safety",
]

def load_config(config_path: str | Path) -> dict[str, Any]:
    """
    Load a JSON config file and validate that required top-level keys exist.

    Args:
        config_path: Path to the JSON config file.

    Returns:
        Parsed config dictionary.

    Raises:
        FileNotFoundError: If the config file does not exist.
        ValueError: If the config is missing required keys.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    path = Path(config_path)

    if not path.exists():
        raise FileNotFoundError(f"config file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        config = json.load(file)

    missing_keys = [
        key for key in REQUIRED_TOP_LEVEL_KEYS
        if key not in config
    ]

    if missing_keys:
        raise ValueError(
            f"config file is missing required keys: {missing_keys}"
        )

    return config