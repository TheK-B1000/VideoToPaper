import json
from pathlib import Path


def load_json(file_path: str):
    """
    Load JSON data from a file.

    Args:
        file_path: Path to the JSON file.

    Returns:
        Parsed JSON data.

    Raises:
        TypeError: If file_path is not a string.
        FileNotFoundError: If the file does not exist.
        ValueError: If the file is not valid JSON.
    """
    if not isinstance(file_path, str):
        raise TypeError("file_path must be a string")

    p = Path(file_path)

    if not p.exists():
        raise FileNotFoundError(f"file not found: {file_path}")

    try:
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid JSON in file: {file_path}") from error


def save_json(data: dict, file_path: str) -> None:
    """
    Save data to a JSON file.

    Args:
        data: JSON-serializable data.
        file_path: Path where the JSON file should be saved.

    Raises:
        TypeError: If file_path is not a string.
        ValueError: If data cannot be serialized as JSON.
    """
    if not isinstance(file_path, str):
        raise TypeError("file_path must be a string")

    p = Path(file_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    try:
        with p.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except (IOError, OSError) as error:
        raise ValueError("data must be JSON serializable") from error


if __name__ == "__main__":
    sample_data = {"message": "json store works"}

    save_json(sample_data, "data/outputs/json_store_test.json")
    loaded_data = load_json("data/outputs/json_store_test.json")

    print(loaded_data)
