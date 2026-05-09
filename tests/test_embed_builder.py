import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.core.embed_builder import (
    canonical_youtube_watch_url,
    extract_youtube_video_id,
    build_embed_base_url,
    build_embed_url,
)


def test_extract_youtube_video_id_from_raw_id():
    assert extract_youtube_video_id("ABC123XYZ89") == "ABC123XYZ89"


def test_extract_youtube_video_id_from_watch_url():
    url = "https://www.youtube.com/watch?v=ABC123XYZ89"
    assert extract_youtube_video_id(url) == "ABC123XYZ89"


def test_extract_youtube_video_id_from_short_url():
    url = "https://youtu.be/ABC123XYZ89"
    assert extract_youtube_video_id(url) == "ABC123XYZ89"


def test_canonical_youtube_watch_url():
    assert (
        canonical_youtube_watch_url("https://youtu.be/ABC123XYZ89")
        == "https://www.youtube.com/watch?v=ABC123XYZ89"
    )


def test_extract_youtube_video_id_rejects_empty_string():
    try:
        extract_youtube_video_id("")
        assert False, "Expected ValueError, but no error was raised"
    except ValueError:
        pass


def test_extract_youtube_video_id_rejects_non_string():
    try:
        extract_youtube_video_id(123)
        assert False, "Expected TypeError, but no error was raised"
    except TypeError:
        pass


def test_build_embed_base_url():
    result = build_embed_base_url("ABC123XYZ89")
    assert result == "https://www.youtube-nocookie.com/embed/ABC123XYZ89"


def test_build_embed_url():
    result = build_embed_url("ABC123XYZ89", 252.4, 263.0)
    assert result == "https://www.youtube-nocookie.com/embed/ABC123XYZ89?start=252&end=263&rel=0"


def test_build_embed_url_rejects_negative_start_time():
    try:
        build_embed_url("ABC123XYZ89", -1.0, 10.0)
        assert False, "Expected ValueError, but no error was raised"
    except ValueError:
        pass


def test_build_embed_url_rejects_bad_time_order():
    try:
        build_embed_url("ABC123XYZ89", 10.0, 5.0)
        assert False, "Expected ValueError, but no error was raised"
    except ValueError:
        pass


test_extract_youtube_video_id_from_raw_id()
test_extract_youtube_video_id_from_watch_url()
test_extract_youtube_video_id_from_short_url()
test_canonical_youtube_watch_url()
test_extract_youtube_video_id_rejects_empty_string()
test_extract_youtube_video_id_rejects_non_string()
test_build_embed_base_url()
test_build_embed_url()
test_build_embed_url_rejects_negative_start_time()
test_build_embed_url_rejects_bad_time_order()

print("All embed_builder tests passed.")