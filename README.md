# VideoToPaper

VideoToPaper is a small transcript research pipeline. Week 1 builds the citation-safe foundation: source registration, speaker provenance, raw transcript loading, character offsets, text cleaning, validation, processed transcript output, and run logs.

The AI layer comes later. The current goal is to preserve source truth while creating cleaned text that later processing can use safely.

## Week 1 Flow

1. Load configuration from `configs/default_config.json`.
2. Load raw transcript segments from `data/raw/raw_transcript.json`.
3. Build one `source_text` string from the raw segment text.
4. Add `char_start` and `char_end` offsets to each segment.
5. Validate each segment.
6. Preserve raw `text` and add separate `cleaned_text`.
7. Register the source video with speaker and transcript provenance.
8. Save processed artifacts and a run log.

## Outputs

Running `main.py` writes:

```text
data/outputs/video_registry.json
data/processed/processed_transcript.json
logs/runs/<run_id>.json
```

The processed transcript has this shape:

```json
{
  "video_id": "ABC123XYZ89",
  "source_text": "raw transcript text...",
  "segments": [
    {
      "text": "  Um, reinforcement learning is useful uh! ",
      "cleaned_text": "reinforcement learning is useful",
      "start_time": 12.4,
      "end_time": 18.9,
      "char_start": 0,
      "char_end": 42
    }
  ]
}
```

The key invariant is:

```python
source_text[segment["char_start"]:segment["char_end"]] == segment["text"]
```

`cleaned_text` may change, but raw `text` and offsets must remain citation-safe.

## Source Registry

Registered videos include:

```json
{
  "video_id": "ABC123XYZ89",
  "title": "What Most People Get Wrong About Reinforcement Learning",
  "url": "https://www.youtube.com/watch?v=ABC123XYZ89",
  "embed_base_url": "https://www.youtube-nocookie.com/embed/ABC123XYZ89",
  "duration_seconds": 2840.0,
  "speaker": {
    "name": "Dr. Jane Smith",
    "credentials": "Professor of Computer Science",
    "stated_motivations": "Concerned about misconceptions in popular AI discourse",
    "notes": "Long-form educational interview"
  },
  "transcript_origin": "youtube_auto",
  "ingested_at": "..."
}
```

## Project Layout

```text
VideoToPaper/
  configs/
    default_config.json
  data/
    raw/
    processed/
    outputs/
  logs/
    runs/
  src/
    core/
    data/
    ops/
    source/
  tests/
  main.py
```

## Run

Use the project virtual environment on Windows:

```powershell
.\.venv\Scripts\python.exe main.py
```

Run all current script-style tests:

```powershell
$tests = Get-ChildItem -LiteralPath 'tests' -Filter 'test_*.py' | Sort-Object Name
foreach ($test in $tests) {
    .\.venv\Scripts\python.exe $test.FullName
}
```

`pytest.ini` is present, but `pytest` is not currently listed as an installed dependency in this environment.
