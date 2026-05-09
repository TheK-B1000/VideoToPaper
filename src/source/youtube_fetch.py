"""
Fetch YouTube captions and basic metadata for Week 1 ingestion.

Requires ``youtube-transcript-api`` (captions) and ``yt-dlp`` (title, duration, channel).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.core.embed_builder import canonical_youtube_watch_url, extract_youtube_video_id
from src.data.json_store import save_json


def normalize_caption_word_spacing(text: str) -> str:
    """
    Repair missing spaces between concatenated words in auto-generated captions.

    YouTube often emits glued tokens (e.g. ``foreignthat``, ``stage ofcivilization``).
    Uses ``wordninja`` when installed; otherwise returns stripped text unchanged.
    """
    collapsed = " ".join(text.split())
    if not collapsed:
        return text.strip()
    try:
        import wordninja
    except ImportError:
        return collapsed
    return " ".join(wordninja.split(collapsed))


def fetched_snippets_to_raw_segments(snippets: Any) -> list[dict[str, float | str]]:
    """
    Convert transcript snippets (FetchedTranscript iterable) to raw segment dicts.

    Each segment has ``text``, ``start_time``, and ``end_time`` as required by
    :func:`src.source.transcript_loader.load_transcript`.
    """
    out: list[dict[str, float | str]] = []

    for sn in snippets:
        text = getattr(sn, "text", None)
        if not isinstance(text, str) or not text.strip():
            continue
        text = normalize_caption_word_spacing(text)
        start = float(getattr(sn, "start", 0.0))
        duration = float(getattr(sn, "duration", 0.0) or 0.0)
        end = start + duration if duration > 0 else start + 0.05
        if end <= start:
            end = start + 0.05
        out.append({"text": text, "start_time": start, "end_time": end})

    if not out:
        raise ValueError("YouTube transcript contained no non-empty caption lines.")

    return out


def fetch_youtube_transcript_snippets(video_id: str) -> Any:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        from youtube_transcript_api._errors import (
            NoTranscriptFound,
            TranscriptsDisabled,
        )
    except ImportError as exc:
        raise RuntimeError(
            "youtube-transcript-api is not installed. "
            "Install dependencies: pip install youtube-transcript-api"
        ) from exc

    api = YouTubeTranscriptApi()
    langs = ("en", "en-US", "en-GB")

    try:
        return api.fetch(video_id, languages=langs)
    except TranscriptsDisabled:
        raise
    except NoTranscriptFound:
        pass
    except Exception:
        pass

    try:
        tls = api.list(video_id)
        try:
            return tls.find_transcript(["en"]).fetch()
        except Exception:
            return tls.find_generated_transcript(["en"]).fetch()
    except TranscriptsDisabled as exc:
        raise RuntimeError(
            f"YouTube captions are disabled for this video ({video_id})."
        ) from exc
    except NoTranscriptFound as exc:
        raise RuntimeError(
            f"No captions were found for video {video_id}. "
            "Try another upload or enable captions on the video."
        ) from exc
    except Exception as exc:
        raise RuntimeError(
            f"Could not load a transcript for video {video_id}: {exc}"
        ) from exc


def fetch_youtube_video_metadata(url: str) -> dict[str, Any]:
    try:
        import yt_dlp
    except ImportError as exc:
        raise RuntimeError(
            "yt-dlp is not installed. Install dependencies: pip install yt-dlp"
        ) from exc

    opts: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 30,
        "noplaylist": True,
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if not isinstance(info, dict):
        raise RuntimeError("yt-dlp returned unexpected metadata.")

    title = info.get("title")
    duration = info.get("duration")
    uploader = info.get("uploader") or info.get("channel")

    if not isinstance(title, str) or not title.strip():
        raise RuntimeError("Could not read video title from YouTube metadata.")

    if duration is None or not isinstance(duration, (int, float)) or duration <= 0:
        raise RuntimeError("Could not read a positive duration from YouTube metadata.")

    return {
        "title": title.strip(),
        "duration_seconds": float(duration),
        "uploader": uploader.strip()
        if isinstance(uploader, str) and uploader.strip()
        else None,
    }


def save_raw_youtube_transcript(segments: list[dict[str, float | str]], path: str) -> Path:
    resolved = Path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    save_json(segments, str(resolved))
    return resolved


def ingest_kwargs_from_youtube(
    youtube_url: str,
    *,
    raw_transcript_path: str,
    speaker_name: str | None,
    speaker_credentials: str,
    speaker_stated_motivations: str,
    speaker_notes: str,
) -> dict[str, Any]:
    """
    Build keyword arguments for :func:`src.source.ingestion.ingest_source` from YouTube.
    """
    video_id = extract_youtube_video_id(youtube_url)
    canonical_url = canonical_youtube_watch_url(video_id)

    snippets = fetch_youtube_transcript_snippets(video_id)
    segments = fetched_snippets_to_raw_segments(snippets)
    save_raw_youtube_transcript(segments, raw_transcript_path)

    meta = fetch_youtube_video_metadata(canonical_url)
    display_speaker = speaker_name or meta.get("uploader") or "Unknown speaker"

    return {
        "video_url": canonical_url,
        "title": meta["title"],
        "duration_seconds": meta["duration_seconds"],
        "speaker_name": display_speaker,
        "speaker_credentials": speaker_credentials,
        "speaker_stated_motivations": speaker_stated_motivations,
        "speaker_notes": speaker_notes,
        "transcript_origin": "youtube_auto",
    }
