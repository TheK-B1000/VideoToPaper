# The Inquiry Engine

The Inquiry Engine is an applied AI engineering capstone for turning a YouTube video into an educational research paper that takes the speaker seriously, checks empirical claims against authoritative literature, and points the reader toward further inquiry.

This repository still uses the `videotopaper` package path for continuity, but the scaffold now reflects the newer Inquiry Engine plan. The current setup is aimed at week 1 and week 2 of that plan: source provenance, speaker context, transcript offsets, chunking, and argument-structure handoff.

## Current Setup

- `data/mock_video.json` models a source registry entry with speaker context.
- `data/mock_transcript.json` models a transcript document with `source_text` plus offset-preserving segments.
- `src/videotopaper/sources.py` stubs the source-ingestion work for week 1.
- `src/videotopaper/transcripts.py` stubs offset-aware transcript loading and validation for week 1.
- `src/videotopaper/chunking.py` and `src/videotopaper/arguments.py` stub the week 2 chunking and argument-mapping handoff.
- `docs/capstone_plan.md` summarizes the new 10-week roadmap inside the repo.
- `docs/development_log.md` mirrors the new weekly operating rhythm and proof-of-competency standard.

## Project Layout

```text
VideoToPaper/
  data/
    mock_transcript.json
    mock_video.json
  docs/
    capstone_plan.md
    development_log.md
  scripts/
    setup.ps1
    test.ps1
  src/
    videotopaper/
      __init__.py
      arguments.py
      chunking.py
      sources.py
      transcripts.py
  tests/
    test_scaffold.py
  pyproject.toml
```

## Local Setup

Install Python 3.11 or newer, then run:

```powershell
.\scripts\setup.ps1
```

The setup script creates `.venv`, installs the local package plus dev tooling when `pip` is available, and still runs the scaffold tests if that install step has to be skipped.

If Python is not on your PATH, pass the interpreter explicitly:

```powershell
.\scripts\setup.ps1 -Python "C:\Path\To\python.exe"
```

If you need an offline bootstrap without package installs:

```powershell
.\scripts\setup.ps1 -WithoutPip
```

Activate the virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Run tests again at any point:

```powershell
.\scripts\test.ps1
```

If PowerShell blocks local scripts because they are unsigned, use a one-time bypass:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\test.ps1
```

Optional extras are grouped by the later roadmap phases:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[ingestion,ai,retrieval,storage,api,ui]"
```

## Week 1 Starting Point

Implement these functions manually:

- `register_video` in `src/videotopaper/sources.py`
- `capture_speaker_context` in `src/videotopaper/sources.py`
- `load_transcript` in `src/videotopaper/transcripts.py`
- `clean_text` in `src/videotopaper/transcripts.py`
- `validate_segment` in `src/videotopaper/transcripts.py`

The starter data now assumes a richer ingestion contract than the old scaffold:

```json
{
  "video_id": "vid_001",
  "title": "What Most People Get Wrong About Reinforcement Learning",
  "url": "https://www.youtube.com/watch?v=example123",
  "duration_seconds": 2840,
  "speaker": {
    "name": "Dr. Jane Smith",
    "credentials": "Professor of Computer Science, Stanford",
    "stated_expertise": ["reinforcement learning", "multi-agent systems"],
    "stated_motivations": "Concerned about misconceptions in popular AI discourse"
  },
  "transcript_origin": "youtube_auto",
  "ingested_at": "2026-04-27T10:00:00Z"
}
```

Transcript segments are now expected to preserve character offsets against the original transcript text.

## Week 2 Handoff

Implement these functions manually:

- `chunk_transcript` in `src/videotopaper/chunking.py`
- `extract_argument_map` in `src/videotopaper/arguments.py`

Week 2 is no longer just about grouping sentences by word count. The chunker now needs to preserve timestamps and character offsets so the argument map can anchor the speaker's thesis, supporting points, qualifications, and examples back to the source.

## Manual-First Rule

For each component:

1. Specify the behavior in plain language.
2. Define the input and output contract.
3. Spend at least 30 minutes on a manual first draft.
4. Use AI for review, debugging, edge cases, and refactoring after that draft exists.
5. Add tests.
6. Write a short development log entry explaining the design and what you learned.
