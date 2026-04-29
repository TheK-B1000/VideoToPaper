from src.core.transcript_processor import process_transcript
from src.data.json_store import load_json, save_json
from src.source.speaker_context import capture_speaker_context
from src.source.source_registry import register_video, save_registered_video
from src.source.transcript_loader import load_transcript


def ingest_source(
    video_url: str,
    title: str,
    duration_seconds: float,
    transcript_path: str,
    registry_output_path: str,
    processed_transcript_output_path: str,
    speaker_name: str,
    speaker_credentials: str = "",
    speaker_stated_motivations: str = "",
    speaker_notes: str = "",
    transcript_origin: str = "mock",
    config=None,
) -> dict:
    """
    Ingest a video source and transcript into citation-safe project artifacts.

    Args:
        video_url: YouTube URL or video ID.
        title: Video title.
        duration_seconds: Video duration in seconds.
        transcript_path: Path to raw transcript JSON.
        registry_output_path: Path where source registry JSON should be saved.
        processed_transcript_output_path: Path where processed transcript JSON should be saved.
        speaker_name: Speaker name.
        speaker_credentials: Speaker background or credentials.
        speaker_stated_motivations: Speaker's stated motivations.
        speaker_notes: Optional extra notes.
        transcript_origin: Where the transcript came from.
        config: Optional project config dictionary.

    Returns:
        A dictionary containing the registered video and processed transcript artifact paths.
    """
    speaker = capture_speaker_context(
        name=speaker_name,
        credentials=speaker_credentials,
        stated_motivations=speaker_stated_motivations,
        notes=speaker_notes,
    )

    video_record = register_video(
        url=video_url,
        title=title,
        duration_seconds=duration_seconds,
        speaker=speaker,
        transcript_origin=transcript_origin,
    )

    loaded_transcript = load_transcript(transcript_path)
    source_text = loaded_transcript["source_text"]
    offset_segments = loaded_transcript["segments"]

    processed_segments = process_transcript(offset_segments, config=config)

    processed_transcript_record = {
        'video_id': video_record["video_id"],
        'source_text': source_text,
        'segments': processed_segments,
    }

    save_registered_video(video_record, registry_output_path)
    save_json(processed_transcript_record, processed_transcript_output_path)

    return {
        "video_record": video_record,
        "transcript_record": processed_transcript_record,
        "registry_output_path": registry_output_path,
        "processed_transcript_output_path": processed_transcript_output_path
    }