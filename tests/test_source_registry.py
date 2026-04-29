import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.source.source_registry import register_video


def test_register_video_accepts_valid_video_source():
    speaker = {
        "name": "Dr. Jane Smith",
        "credentials": "Professor of Computer Science",
        "stated_motivations": "Concerned about misconceptions in popular AI discourse"
    }

    result = register_video(
        url="https://www.youtube.com/watch?v=ABC123XYZ89",
        title="What Most People Get Wrong About Reinforcement Learning",
        duration_seconds=2840,
        speaker=speaker,
        transcript_origin="youtube_auto"
    )

    assert result["video_id"] == "ABC123XYZ89"
    assert result["title"] == "What Most People Get Wrong About Reinforcement Learning"
    assert result["url"] == "https://www.youtube.com/watch?v=ABC123XYZ89"
    assert result["embed_base_url"] == "https://www.youtube-nocookie.com/embed/ABC123XYZ89"
    assert result["duration_seconds"] == 2840.0
    assert result["speaker"] == speaker
    assert result["transcript_origin"] == "youtube_auto"
    assert "ingested_at" in result


def test_register_video_rejects_empty_title():
    speaker = {"name": "Dr. Jane Smith"}

    try:
        register_video(
            url="ABC123XYZ89",
            title="   ",
            duration_seconds=100,
            speaker=speaker
        )
        assert False, "Expected ValueError, but no error was raised"
    except ValueError:
        pass


def test_register_video_rejects_bad_duration():
    speaker = {"name": "Dr. Jane Smith"}

    try:
        register_video(
            url="ABC123XYZ89",
            title="Test Video",
            duration_seconds=0,
            speaker=speaker
        )
        assert False, "Expected ValueError, but no error was raised"
    except ValueError:
        pass


def test_register_video_rejects_non_dict_speaker():
    try:
        register_video(
            url="ABC123XYZ89",
            title="Test Video",
            duration_seconds=100,
            speaker="Dr. Jane Smith"
        )
        assert False, "Expected TypeError, but no error was raised"
    except TypeError:
        pass


def test_register_video_rejects_invalid_url_or_id():
    speaker = {"name": "Dr. Jane Smith"}

    try:
        register_video(
            url="not-a-valid-youtube-id",
            title="Test Video",
            duration_seconds=100,
            speaker=speaker
        )
        assert False, "Expected ValueError, but no error was raised"
    except ValueError:
        pass


test_register_video_accepts_valid_video_source()
test_register_video_rejects_empty_title()
test_register_video_rejects_bad_duration()
test_register_video_rejects_non_dict_speaker()
test_register_video_rejects_invalid_url_or_id()

print("All source_registry tests passed.")