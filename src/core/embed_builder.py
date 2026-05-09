import re
from urllib.parse import parse_qs, urlparse

_YOUTUBE_VIDEO_ID = re.compile(r"^[a-zA-Z0-9_-]{11}$")


def _is_youtube_video_id(value: str) -> bool:
    return bool(_YOUTUBE_VIDEO_ID.fullmatch(value))


def extract_youtube_video_id(video_url_or_id: str) -> str:
    """
    Extract a YouTube video ID from a YouTube URL or return the ID directly.

    Args:
        video_url_or_id: A YouTube URL or 11-character YouTube video ID.

    Returns:
        The YouTube video ID.

    Raises:
        TypeError: If video_url_or_id is not a string.
        ValueError: If a valid video ID cannot be extracted.
    """
    if not isinstance(video_url_or_id, str):
        raise TypeError("video_url_or_id must be a string")
    
    value = video_url_or_id.strip()

    if not value:
        raise ValueError("video_url_or_id cannot be empty")
    
    if _is_youtube_video_id(value):
        return value

    parsed_url = urlparse(value)

    if parsed_url.netloc in ["youtu.be"]:
        video_id = parsed_url.path.lstrip("/")
        if _is_youtube_video_id(video_id):
            return video_id

    if "youtube.com" in parsed_url.netloc:
        query_params = parse_qs(parsed_url.query)
        video_id_list = query_params.get("v", [])

        if video_id_list:
            candidate = video_id_list[0]
            if _is_youtube_video_id(candidate):
                return candidate
    
    raise ValueError(f"could not extract YouTube video ID from: {video_url_or_id}")

def canonical_youtube_watch_url(video_url_or_id: str) -> str:
    """
    Normalize any supported YouTube URL or bare ID to a standard watch URL.

    Args:
        video_url_or_id: YouTube URL or 11-character video ID.

    Returns:
        ``https://www.youtube.com/watch?v=<id>``
    """
    video_id = extract_youtube_video_id(video_url_or_id)
    return f"https://www.youtube.com/watch?v={video_id}"


def build_embed_base_url(video_url_or_id: str) -> str:
    """
    Build a privacy-respecting YouTube embed base URL.

    Args:
        video_url_or_id: A YouTube URL or 11-character YouTube video ID.

    Returns:
        A youtube-nocookie embed base URL.
    """
    video_id = extract_youtube_video_id(video_url_or_id)

    return f"https://www.youtube-nocookie.com/embed/{video_id}"

def build_embed_url(video_url_or_id: str, start_time: float, end_time: float) -> str:
    """
    Build a privacy-respecting YouTube embed URL for a specific time range.

    Args:
        video_url_or_id: A YouTube URL or 11-character YouTube video ID.
        start_time: Clip start time in seconds.
        end_time: Clip end time in seconds.

    Returns:
        A YouTube embed URL with start and end parameters.

    Raises:
        TypeError: If start_time or end_time are not numbers.
        ValueError: If times are invalid.
    """
    if not isinstance(start_time, (int, float)):
        raise TypeError("start_time must be a number")
    
    if not isinstance(end_time, (int, float)):
        raise TypeError("end_time must be a number")
    
    if start_time < 0:
        raise ValueError("start_time cannot be negative")
    
    if end_time <= start_time:
        raise ValueError("end_time must be greater than start_time")
    
    embed_base_url = build_embed_base_url(video_url_or_id)

    start_seconds = int(start_time)
    end_seconds = int(end_time)

    return f"{embed_base_url}?start={start_seconds}&end={end_seconds}&rel=0"