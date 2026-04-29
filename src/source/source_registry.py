from datetime import datetime, timezone

from src.data.json_store import load_json, save_json
from src.core.embed_builder import (
    build_embed_base_url,
    extract_youtube_video_id
)
from src.data.json_store import load_json, save_json

def register_video(
    url: str,
    title: str,
    duration_seconds: float,
    speaker: dict,
    transcript_origin: str = "mock",
) -> dict:
    """
    Register a video source with provenance and embed metadata.

    Args:
        url: YouTube URL or video ID.
        title: Video title.
        duration_seconds: Video duration in seconds.
        speaker: Speaker metadata dictionary.
        transcript_origin: Where the transcript came from.

    Returns:
        A video source record dictionary.

    Raises:
        TypeError: If input types are invalid.
        ValueError: If required values are missing or invalid.
    """
    if not isinstance(url, str):
        raise TypeError("url must be a string")
    
    if not isinstance(title, str):
        raise TypeError("title must be a string")
    
    if not isinstance(duration_seconds, (int, float)):
        raise TypeError("duration_seconds must be a number")
    
    if not isinstance(speaker, dict):
        raise TypeError("speaker must be a dictionary")
    
    if not isinstance(transcript_origin, str):
        raise TypeError("transcript_origin must be a string")

    if not url.strip():
        raise ValueError("url cannot be empty")

    if not title.strip():
        raise ValueError("title cannot be empty")
    
    if duration_seconds <= 0:
        raise ValueError("duration_seconds must be greater than 0")
    
    if not transcript_origin.strip():
        raise ValueError("transcript_origin cannot be empty")
    
    video_id = extract_youtube_video_id(url)
    embed_base_url = build_embed_base_url(video_id)

    return {
        "video_id": video_id,
        "title": title.strip(),
        "url": url.strip(),
        "embed_base_url": embed_base_url,
        "duration_seconds": float(duration_seconds),
        "speaker": speaker,
        "transcript_origin": transcript_origin.strip(),
        "ingested_at": datetime.now(timezone.utc).isoformat(),
    }


def save_registered_video(video_record: dict, file_path: str) -> None:
    """
    Save a registered video source record to disk.

    Args:
        video_record: Registered video metadata dictionary.
        file_path: Destination JSON path.

    Raises:
        TypeError: If inputs are invalid.
        ValueError: If the video record is missing required fields.
    """
    if not isinstance(video_record, dict):
        raise TypeError("video_record must be a dictionary")
    
    if not isinstance(file_path, str):
        raise TypeError("file_path must be a string")
    
    required_fields = [
        "video_id",
        "title",
        "url",
        "embed_base_url",
        "duration_seconds",
        "speaker",
        "transcript_origin",
        "ingested_at",
    ]

    for field in required_fields:
        if field not in video_record:
            raise ValueError(f"video_record missing required field: {field}")

    save_json(video_record, file_path)


def load_registered_video(file_path: str) -> dict:
    """
    Load a registered video source record from disk.

    Args:
        file_path: Source registry JSON path.

    Returns:
        Registered video metadata dictionary.

    Raises:
        TypeError: If file_path is not a string.
        ValueError: If loaded record is malformed.
    """
    video_record = load_json(file_path)

    if not isinstance(video_record, dict):
        raise ValueError("registered video file must contain a dictionary")

    required_fields = [
        "video_id",
        "title",
        "url",
        "embed_base_url",
        "duration_seconds",
        "speaker",
        "transcript_origin",
        "ingested_at",
    ]

    for field in required_fields:
        if field not in video_record:
            raise ValueError(f"video_record missing required field: {field}")

    return video_record
