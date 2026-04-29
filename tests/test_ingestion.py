import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.data.json_store import load_json, save_json
from src.source.ingestion import ingest_source


def test_ingest_source_creates_registry_and_processed_transcript():
    raw_transcript_path = "data/raw/test_ingestion_transcript.json"
    registry_output_path = "data/outputs/test_source_registry.json"
    processed_output_path = "data/outputs/test_processed_transcript.json"

    raw_segments = [
        {
            "text": "  Um, [Music] reinforcement    learning is useful uh!  ",
            "start_time": 12.4,
            "end_time": 18.9,
        },
        {
            "text": "The agent learns by interacting with an environment.",
            "start_time": 19.0,
            "end_time": 24.2,
        },
    ]

    save_json(raw_segments, raw_transcript_path)

    result = ingest_source(
        video_url="https://www.youtube.com/watch?v=ABC123XYZ89",
        title="What Most People Get Wrong About Reinforcement Learning",
        duration_seconds=2840,
        transcript_path=raw_transcript_path,
        registry_output_path=registry_output_path,
        processed_transcript_output_path=processed_output_path,
        speaker_name="Dr. Jane Smith",
        speaker_credentials="Professor of Computer Science",
        speaker_stated_motivations="Concerned about misconceptions in popular AI discourse",
        speaker_notes="Long-form educational interview",
        transcript_origin="youtube_auto",
    )

    assert Path(registry_output_path).exists()
    assert Path(processed_output_path).exists()

    registry = load_json(registry_output_path)
    processed = load_json(processed_output_path)

    assert registry["video_id"] == "ABC123XYZ89"
    assert registry["speaker"]["name"] == "Dr. Jane Smith"
    assert registry["embed_base_url"] == "https://www.youtube-nocookie.com/embed/ABC123XYZ89"

    assert processed["video_id"] == "ABC123XYZ89"
    assert "source_text" in processed
    assert "segments" in processed
    assert len(processed["segments"]) == 2

    first_segment = processed["segments"][0]

    raw_slice = processed["source_text"][
        first_segment["char_start"]:first_segment["char_end"]
    ]

    assert raw_slice == first_segment["text"]
    assert first_segment["cleaned_text"] == "reinforcement learning is useful"

    assert result["registry_output_path"] == registry_output_path
    assert result["processed_transcript_output_path"] == processed_output_path


test_ingest_source_creates_registry_and_processed_transcript()

print("All ingestion tests passed.")